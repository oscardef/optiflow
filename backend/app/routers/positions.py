"""Position calculation and tracking router"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List

from ..database import get_db
from ..models import TagPosition, Anchor, UWBMeasurement
from ..schemas import TagPositionResponse
from ..triangulation import TriangulationService
from ..core import logger

router = APIRouter(prefix="/positions", tags=["positions"])

@router.get("/latest", response_model=List[TagPositionResponse])
def get_latest_positions(limit: int = 50, db: Session = Depends(get_db)):
    """Get the most recent calculated tag positions"""
    logger.info(f"Fetching latest {limit} positions")
    positions = db.query(TagPosition)\
        .order_by(TagPosition.timestamp.desc())\
        .limit(limit)\
        .all()
    
    return [TagPositionResponse(
        id=p.id,
        timestamp=p.timestamp.isoformat(),
        tag_id=p.tag_id,
        x_position=p.x_position,
        y_position=p.y_position,
        confidence=p.confidence,
        num_anchors=p.num_anchors
    ) for p in positions]

@router.post("/calculate-position")
def calculate_position(tag_id: str, db: Session = Depends(get_db)):
    """
    Calculate current position of a tag based on recent UWB measurements
    
    This endpoint:
    1. Gets the latest UWB measurements for all active anchors
    2. Looks up anchor positions from the database
    3. Performs trilateration to calculate tag position
    4. Stores the result in tag_positions table
    """
    # Get active anchors
    anchors = db.query(Anchor).filter(Anchor.is_active == True).all()
    
    if len(anchors) < 2:
        raise HTTPException(
            status_code=400, 
            detail="At least 2 active anchors required for position calculation"
        )
    
    # Get latest UWB measurement for each anchor (within last 5 seconds)
    cutoff_time = datetime.utcnow() - timedelta(seconds=5)
    measurements = []
    
    for anchor in anchors:
        uwb = db.query(UWBMeasurement)\
            .filter(
                UWBMeasurement.mac_address == anchor.mac_address,
                UWBMeasurement.timestamp >= cutoff_time
            )\
            .order_by(UWBMeasurement.timestamp.desc())\
            .first()
        
        if uwb:
            # Convert cm to same units as anchor positions
            measurements.append((
                anchor.x_position,
                anchor.y_position,
                uwb.distance_cm
            ))
    
    if len(measurements) < 2:
        raise HTTPException(
            status_code=400,
            detail="Not enough recent measurements. Need at least 2 anchors with data from last 5 seconds"
        )
    
    # Calculate position using triangulation
    result = TriangulationService.calculate_position(measurements)
    
    if result is None:
        raise HTTPException(status_code=500, detail="Position calculation failed")
    
    x, y, confidence = result
    
    # Store the calculated position
    position = TagPosition(
        timestamp=datetime.utcnow(),
        tag_id=tag_id,
        x_position=x,
        y_position=y,
        confidence=confidence,
        num_anchors=len(measurements)
    )
    db.add(position)
    db.commit()
    db.refresh(position)
    
    logger.info(f"Calculated position for {tag_id}: ({x:.2f}, {y:.2f}) with {len(measurements)} anchors")
    
    return TagPositionResponse(
        id=position.id,
        timestamp=position.timestamp.isoformat(),
        tag_id=position.tag_id,
        x_position=position.x_position,
        y_position=position.y_position,
        confidence=position.confidence,
        num_anchors=position.num_anchors
    )
