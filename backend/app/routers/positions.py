"""Position calculation and tracking router"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..schemas import TagPositionResponse
from ..services import PositionService

router = APIRouter(prefix="/positions", tags=["positions"])


@router.get("/latest", response_model=List[TagPositionResponse])
def get_latest_positions(limit: int = 50, db: Session = Depends(get_db)):
    """Get the most recent calculated tag positions"""
    positions = PositionService.get_latest_positions(db, limit)
    
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
    position = PositionService.calculate_position_from_measurements(db, tag_id)
    
    return TagPositionResponse(
        id=position.id,
        timestamp=position.timestamp.isoformat(),
        tag_id=position.tag_id,
        x_position=position.x_position,
        y_position=position.y_position,
        confidence=position.confidence,
        num_anchors=position.num_anchors
    )
