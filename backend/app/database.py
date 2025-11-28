from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Dual database URLs for simulation and real modes
DATABASE_URL_SIMULATION = os.getenv(
    "DATABASE_URL_SIMULATION", 
    "postgresql://optiflow:optiflow_dev@localhost:5432/optiflow_simulation"
)
DATABASE_URL_REAL = os.getenv(
    "DATABASE_URL_REAL", 
    "postgresql://optiflow:optiflow_dev@localhost:5433/optiflow_real"
)

# Create engines for both databases
engine_simulation = create_engine(DATABASE_URL_SIMULATION)
engine_real = create_engine(DATABASE_URL_REAL)

# Create session makers for both databases
SessionLocal_simulation = sessionmaker(autocommit=False, autoflush=False, bind=engine_simulation)
SessionLocal_real = sessionmaker(autocommit=False, autoflush=False, bind=engine_real)

Base = declarative_base()

def get_db():
    """
    Dependency for FastAPI routes to get DB session based on current mode
    This is the main function routes should use
    """
    from .config import config_state, ConfigMode
    
    if config_state.mode == ConfigMode.SIMULATION:
        db = SessionLocal_simulation()
    else:
        db = SessionLocal_real()
    
    try:
        yield db
    finally:
        db.close()

def get_db_simulation():
    """Direct access to simulation database"""
    db = SessionLocal_simulation()
    try:
        yield db
    finally:
        db.close()

def get_db_real():
    """Direct access to real database"""
    db = SessionLocal_real()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables for both databases"""
    Base.metadata.create_all(bind=engine_simulation)
    Base.metadata.create_all(bind=engine_real)
