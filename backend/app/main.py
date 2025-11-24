"""
OptiFlow Backend API
Main application entry point with FastAPI
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db, SessionLocal
from .models import Zone
from .core import logger
from .routers import (
    anchors_router,
    positions_router,
    data_router,
    products_router,
    analytics_router,
    zones_router
)

app = FastAPI(title="OptiFlow API", version="1.0.0")

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

@app.get("/")
def health_check():
    """API health check"""
    return {"status": "ok", "service": "OptiFlow API"}

@app.on_event("startup")
def startup_event():
    """Initialize database and create default zones on startup"""
    logger.info("Starting OptiFlow API server...")
    init_db()
    
    # Create default zones if they don't exist
    db = SessionLocal()
    try:
        zone_count = db.query(Zone).count()
        if zone_count == 0:
            logger.info("Creating default store zones...")
            # Create store zones based on typical retail layout
            # Store dimensions: 1000cm x 800cm
            zones = [
                Zone(name="Entrance", x_min=0, x_max=200, y_min=0, y_max=160),
                Zone(name="Aisle 1", x_min=200, x_max=400, y_min=0, y_max=400),
                Zone(name="Aisle 2", x_min=400, x_max=600, y_min=0, y_max=400),
                Zone(name="Aisle 3", x_min=600, x_max=800, y_min=0, y_max=400),
                Zone(name="Aisle 4", x_min=800, x_max=1000, y_min=0, y_max=400),
                Zone(name="Cross Aisle", x_min=0, x_max=1000, y_min=360, y_max=440),
                Zone(name="Aisle 5", x_min=200, x_max=400, y_min=440, y_max=800),
                Zone(name="Aisle 6", x_min=400, x_max=600, y_min=440, y_max=800),
                Zone(name="Aisle 7", x_min=600, x_max=800, y_min=440, y_max=800),
                Zone(name="Aisle 8", x_min=800, x_max=1000, y_min=440, y_max=800),
                Zone(name="Checkout", x_min=0, x_max=200, y_min=640, y_max=800),
            ]
            db.add_all(zones)
            db.commit()
            logger.info(f"Created {len(zones)} default zones")
        else:
            logger.info(f"Found {zone_count} existing zones")
    finally:
        db.close()
    
    logger.info("Database initialized successfully")
