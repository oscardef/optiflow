"""Configuration and mode management router"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ..database import get_db, get_db_simulation, get_db_real
from ..models import Configuration, Anchor
from ..config import config_state, ConfigMode
from ..core import logger

router = APIRouter(prefix="/config", tags=["config"])

class ModeResponse(BaseModel):
    mode: str
    simulation_running: bool

class ModeSwitch(BaseModel):
    mode: str
    confirm: bool = False

class StoreConfigResponse(BaseModel):
    store_width: int
    store_height: int
    max_display_items: int
    mode: str

class StoreConfigUpdate(BaseModel):
    store_width: Optional[int] = None
    store_height: Optional[int] = None
    max_display_items: Optional[int] = None

@router.get("/mode", response_model=ModeResponse)
def get_current_mode():
    """Get current operating mode"""
    return {
        "mode": config_state.mode.value,
        "simulation_running": config_state.simulation_running
    }

@router.post("/mode/switch")
def switch_mode(switch: ModeSwitch):
    """
    Switch between SIMULATION and REAL modes
    Requires confirmation as it changes which database is active
    All data for each mode is preserved and can be resumed
    """
    if not switch.confirm:
        raise HTTPException(
            status_code=400, 
            detail="Mode switch requires confirmation. Set 'confirm: true' to proceed."
        )
    
    try:
        new_mode = ConfigMode(switch.mode)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode. Must be '{ConfigMode.SIMULATION.value}' or '{ConfigMode.REAL.value}'"
        )
    
    old_mode = config_state.mode
    
    if new_mode == old_mode:
        return {
            "success": True,
            "message": f"Already in {new_mode.value} mode",
            "mode": new_mode.value
        }
    
    # Stop simulation if running when switching to REAL mode
    if new_mode == ConfigMode.REAL and config_state.simulation_running:
        # Import here to avoid circular dependency
        from .simulation import stop_simulation_process
        stop_simulation_process()
        logger.info("Stopped simulation before switching to REAL mode")
    
    # Switch mode
    config_state.mode = new_mode
    
    logger.info(f"Switched from {old_mode.value} to {new_mode.value} mode")
    
    return {
        "success": True,
        "message": f"Switched from {old_mode.value} to {new_mode.value} mode. All data for {old_mode.value} mode has been preserved and can be resumed by switching back.",
        "previous_mode": old_mode.value,
        "current_mode": new_mode.value,
        "simulation_running": config_state.simulation_running
    }

@router.get("/store", response_model=StoreConfigResponse)
def get_store_config(db: Session = Depends(get_db)):
    """Get store configuration (dimensions and current mode)"""
    # Try to get from database first
    db_config = db.query(Configuration).first()
    
    if db_config:
        return {
            "store_width": db_config.store_width,
            "store_height": db_config.store_height,
            "max_display_items": config_state.max_display_items,
            "mode": config_state.mode.value
        }
    
    # Fall back to config state
    return {
        "store_width": config_state.store_width,
        "store_height": config_state.store_height,
        "max_display_items": config_state.max_display_items,
        "mode": config_state.mode.value
    }

@router.put("/store")
def update_store_config(
    update: StoreConfigUpdate,
    db: Session = Depends(get_db)
):
    """Update store configuration"""
    # Get or create configuration
    db_config = db.query(Configuration).first()
    
    if not db_config:
        db_config = Configuration(
            store_width=config_state.store_width,
            store_height=config_state.store_height
        )
        db.add(db_config)
    
    # Update fields
    if update.store_width is not None:
        db_config.store_width = update.store_width
        config_state.store_width = update.store_width
    
    if update.store_height is not None:
        db_config.store_height = update.store_height
        config_state.store_height = update.store_height
    
    if update.max_display_items is not None:
        config_state.max_display_items = update.max_display_items
    
    db.commit()
    db.refresh(db_config)
    
    logger.info(f"Updated store config: {db_config.store_width}x{db_config.store_height}cm, max_display_items={config_state.max_display_items}")
    
    return {
        "success": True,
        "store_width": db_config.store_width,
        "store_height": db_config.store_height,
        "max_display_items": config_state.max_display_items
    }

@router.get("/layout")
def get_full_layout(db: Session = Depends(get_db)):
    """Get complete store layout including dimensions, zones, and anchors"""
    config = db.query(Configuration).first()
    zones = db.query(Zone).all()
    anchors = db.query(Anchor).filter(Anchor.is_active == True).all()
    
    return {
        "mode": config_state.mode.value,
        "store_width": config.store_width if config else config_state.store_width,
        "store_height": config.store_height if config else config_state.store_height,
        "zones": [z.to_dict() for z in zones],
        "anchors": [a.to_dict() for a in anchors]
    }

@router.get("/validate-anchors")
def validate_anchors(db: Session = Depends(get_db)):
    """
    Validate that configured anchors match received UWB messages
    Checks last 60 seconds of measurements
    """
    from datetime import datetime, timedelta
    from ..models import UWBMeasurement
    
    # Get configured anchors
    configured_anchors = db.query(Anchor).filter(Anchor.is_active == True).all()
    configured_macs = {a.mac_address for a in configured_anchors}
    
    # Get recent measurements (last 60 seconds)
    cutoff = datetime.utcnow() - timedelta(seconds=60)
    recent_measurements = db.query(UWBMeasurement).filter(
        UWBMeasurement.timestamp >= cutoff
    ).all()
    
    received_macs = {m.mac_address for m in recent_measurements}
    
    # Find mismatches
    missing_from_config = received_macs - configured_macs
    missing_from_data = configured_macs - received_macs
    
    is_valid = len(missing_from_config) == 0 and len(missing_from_data) == 0
    
    warnings = []
    if missing_from_config:
        warnings.append(f"Received data from unconfigured anchors: {', '.join(missing_from_config)}")
    if missing_from_data:
        warnings.append(f"No data received from configured anchors: {', '.join(missing_from_data)}")
    
    return {
        "valid": is_valid,
        "configured_anchors": list(configured_macs),
        "received_anchors": list(received_macs),
        "warnings": warnings,
        "message": "All anchors validated successfully" if is_valid else "Anchor configuration mismatch detected"
    }
