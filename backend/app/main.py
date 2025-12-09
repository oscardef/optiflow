"""
OptiFlow Backend API
Main application entry point with FastAPI
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db, SessionLocal_simulation, SessionLocal_production
from .models import Configuration, InventoryItem, Product
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
    config_router,
    simulation_router,
    items_router,
    setup_router
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
app.include_router(config_router)
app.include_router(simulation_router)
app.include_router(items_router)
app.include_router(setup_router)

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
    
    # Initialize simulation database
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
        
        # Populate inventory items if empty
        populate_inventory_if_empty(db_sim)
    finally:
        db_sim.close()
    
    # Initialize production database with configuration
    db_production = SessionLocal_production()
    try:
        config = db_production.query(Configuration).first()
        if not config:
            config = Configuration(
                store_width=config_state.store_width,
                store_height=config_state.store_height
            )
            db_production.add(config)
            db_production.commit()
            logger.info("Created default configuration in production database")
    finally:
        db_production.close()
    
    logger.info("Both databases initialized successfully")
