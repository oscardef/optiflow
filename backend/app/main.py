"""
OptiFlow Backend API
Main application entry point with FastAPI
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db, SessionLocal_simulation, SessionLocal_real
from .models import Zone, Configuration, InventoryItem, Product
from .config import config_state, ConfigMode
from .core import logger
import random


def generate_aisle_positions(num_items: int):
    """Generate positions along store aisles"""
    positions = []
    aisles = [
        {'x': 200, 'y_start': 150, 'y_end': 700},
        {'x': 400, 'y_start': 120, 'y_end': 700},
        {'x': 600, 'y_start': 120, 'y_end': 700},
        {'x': 800, 'y_start': 120, 'y_end': 700},
    ]
    
    for aisle in aisles:
        for side_offset in [-25, 25]:
            for shelf_level in range(4):
                x_pos = aisle['x'] + side_offset
                for slot in range(30):
                    aisle_length = aisle['y_end'] - aisle['y_start']
                    y_pos = aisle['y_start'] + (aisle_length * (slot + 0.5) / 30)
                    positions.append((round(x_pos, 2), round(y_pos, 2)))
    
    # Cross-aisle positions
    for x_pos in range(200, 900, 30):
        for side_offset in [-30, 30]:
            positions.append((x_pos, 400 + side_offset))
    
    random.shuffle(positions)
    
    if len(positions) < num_items:
        while len(positions) < num_items:
            base = random.choice(positions)
            positions.append((base[0] + random.uniform(-2, 2), base[1] + random.uniform(-2, 2)))
    
    return positions[:num_items]


def populate_inventory_if_empty(db):
    """Populate inventory items if table is empty"""
    item_count = db.query(InventoryItem).count()
    if item_count > 0:
        logger.info(f"Inventory already has {item_count} items")
        return
    
    product_count = db.query(Product).count()
    if product_count == 0:
        logger.info("No products found, skipping inventory population")
        return
    
    logger.info("Populating inventory items...")
    products = db.query(Product).order_by(Product.id).all()
    
    # Create ~2 items per product on average
    num_items = min(len(products) * 2, 3000)
    positions = generate_aisle_positions(num_items)
    
    items_per_product = max(1, num_items // len(products))
    item_num = 0
    
    for i, product in enumerate(products):
        # Give each product 1-3 items
        count = items_per_product if i < len(products) - 1 else num_items - item_num
        count = min(count, num_items - item_num)
        
        for _ in range(count):
            if item_num >= len(positions):
                break
            
            x, y = positions[item_num]
            item = InventoryItem(
                rfid_tag=f"RFID{str(item_num + 1).zfill(8)}",
                product_id=product.id,
                status="present",
                x_position=x,
                y_position=y
            )
            db.add(item)
            item_num += 1
    
    db.commit()
    logger.info(f"Created {item_num} inventory items")
from .routers import (
    anchors_router,
    positions_router,
    data_router,
    products_router,
    analytics_router,
    zones_router,
    config_router,
    simulation_router,
    items_router
)

app = FastAPI(
    title="OptiFlow API",
    version="1.0.0",
    description="""
# OptiFlow Real-Time Inventory Tracking System

A comprehensive UWB-based inventory tracking system with real-time analytics.

## Features

- **Real-time Position Tracking**: UWB triangulation for precise 2D positioning
- **RFID Item Detection**: Track item presence/absence in real-time
- **Analytics Dashboard**: Product velocity, trends, and AI-powered insights
- **Historical Data**: Time-series analytics with purchase events and stock snapshots

## Quick Start

1. Configure anchors via `/anchors` endpoint
2. Start simulation or connect hardware
3. View live data at `/positions` and `/items`
4. Access analytics at `/analytics/*` endpoints

## Analytics Endpoints

The analytics API provides:
- **Overview metrics** (sales, stock value, low stock alerts)
- **Product performance** (velocity, turnover, top products)
- **AI insights** (clustering, forecasting, anomaly detection)
- **Historical data** (bulk upload for testing/backfill)
    """,
    contact={
        "name": "OptiFlow Team",
        "url": "https://github.com/oscardef/optiflow"
    },
    license_info={
        "name": "MIT"
    }
)

# CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(anchors_router)
app.include_router(positions_router)
app.include_router(data_router)
app.include_router(products_router)
app.include_router(analytics_router)
app.include_router(zones_router)
app.include_router(config_router)
app.include_router(simulation_router)
app.include_router(items_router)

@app.get("/")
def health_check():
    """API health check"""
    return {"status": "ok", "service": "OptiFlow API"}

@app.on_event("startup")
def startup_event():
    """Initialize databases and create default configuration"""
    logger.info("Starting OptiFlow API server...")
    logger.info(f"Current mode: {config_state.mode.value}")
    
    # Initialize both databases
    init_db()
    
    # Initialize simulation database with default zones
    db_sim = SessionLocal_simulation()
    try:
        # Create configuration if doesn't exist
        config = db_sim.query(Configuration).first()
        if not config:
            config = Configuration(
                store_width=config_state.store_width,
                store_height=config_state.store_height
            )
            db_sim.add(config)
            db_sim.commit()
            logger.info("Created default configuration in simulation database")
        
        # Create default zones for simulation mode only
        zone_count = db_sim.query(Zone).count()
        if zone_count == 0:
            logger.info("Creating default store zones for simulation...")
            # Create store zones based on typical retail layout
            # Store dimensions: 1000cm x 800cm
            zones = [
                Zone(name="Entrance", x_min=0, x_max=200, y_min=0, y_max=160, zone_type="entrance"),
                Zone(name="Aisle 1", x_min=200, x_max=400, y_min=0, y_max=400, zone_type="aisle"),
                Zone(name="Aisle 2", x_min=400, x_max=600, y_min=0, y_max=400, zone_type="aisle"),
                Zone(name="Aisle 3", x_min=600, x_max=800, y_min=0, y_max=400, zone_type="aisle"),
                Zone(name="Aisle 4", x_min=800, x_max=1000, y_min=0, y_max=400, zone_type="aisle"),
                Zone(name="Cross Aisle", x_min=0, x_max=1000, y_min=360, y_max=440, zone_type="aisle"),
                Zone(name="Aisle 5", x_min=200, x_max=400, y_min=440, y_max=800, zone_type="aisle"),
                Zone(name="Aisle 6", x_min=400, x_max=600, y_min=440, y_max=800, zone_type="aisle"),
                Zone(name="Aisle 7", x_min=600, x_max=800, y_min=440, y_max=800, zone_type="aisle"),
                Zone(name="Aisle 8", x_min=800, x_max=1000, y_min=440, y_max=800, zone_type="aisle"),
                Zone(name="Checkout", x_min=0, x_max=200, y_min=640, y_max=800, zone_type="checkout"),
            ]
            db_sim.add_all(zones)
            db_sim.commit()
            logger.info(f"Created {len(zones)} default zones in simulation database")
        else:
            logger.info(f"Found {zone_count} existing zones in simulation database")
        
        # Populate inventory items if empty
        populate_inventory_if_empty(db_sim)
    finally:
        db_sim.close()
    
    # Initialize real database with configuration
    db_real = SessionLocal_real()
    try:
        config = db_real.query(Configuration).first()
        if not config:
            config = Configuration(
                store_width=config_state.store_width,
                store_height=config_state.store_height
            )
            db_real.add(config)
            db_real.commit()
            logger.info("Created default configuration in real database")
        
        # Real mode starts with empty zones - admin can create them
        zone_count = db_real.query(Zone).count()
        logger.info(f"Real database has {zone_count} zones")
    finally:
        db_real.close()
    
    logger.info("Both databases initialized successfully")
