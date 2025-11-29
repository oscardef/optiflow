"""
OptiFlow Backend API
Main application entry point with FastAPI
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db, SessionLocal_simulation, SessionLocal_real
from .models import Zone, Configuration
from .config import config_state, ConfigMode
from .core import logger, settings
from .core.exceptions import OptiFlowException
from .core.handlers import optiflow_exception_handler
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
    title=settings.app_name, 
    version=settings.app_version,
    description="Real-time store tracking system using UWB triangulation"
)

# Register exception handlers
app.add_exception_handler(OptiFlowException, optiflow_exception_handler)

# CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
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
