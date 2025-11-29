"""Position calculation service"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional

from ..models import TagPosition, Anchor, UWBMeasurement
from ..triangulation import TriangulationService
from ..core import logger
from ..core.exceptions import InsufficientDataError
from ..core.settings import settings


class PositionService:
    """Service for position calculation and tracking"""
    
    @staticmethod
    def get_latest_positions(db: Session, limit: int = 50) -> List[TagPosition]:
        """Get the most recent calculated tag positions"""
        logger.info(f"Fetching latest {limit} positions")
        return db.query(TagPosition)\
            .order_by(TagPosition.timestamp.desc())\
            .limit(limit)\
            .all()
    
    @staticmethod
    def calculate_position_from_measurements(
        db: Session,
        tag_id: str,
        timeout_seconds: int = None
    ) -> TagPosition:
        """
        Calculate current position of a tag based on recent UWB measurements
        
        This method:
        1. Gets the latest UWB measurements for all active anchors
        2. Looks up anchor positions from the database
        3. Performs trilateration to calculate tag position
        4. Stores the result in tag_positions table
        """
        timeout = timeout_seconds or settings.position_measurement_timeout_seconds
        
        # Get active anchors
        anchors = db.query(Anchor).filter(Anchor.is_active == True).all()
        
        if len(anchors) < settings.min_anchors_for_position:
            raise InsufficientDataError(
                f"At least {settings.min_anchors_for_position} active anchors required for position calculation",
                details={"current_anchors": len(anchors)}
            )
        
        # Get latest UWB measurement for each anchor (within timeout)
        cutoff_time = datetime.utcnow() - timedelta(seconds=timeout)
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
                measurements.append((
                    anchor.x_position,
                    anchor.y_position,
                    uwb.distance_cm
                ))
        
        if len(measurements) < settings.min_anchors_for_position:
            raise InsufficientDataError(
                f"Not enough recent measurements. Need at least {settings.min_anchors_for_position} anchors with data from last {timeout} seconds",
                details={"measurements_found": len(measurements), "timeout_seconds": timeout}
            )
        
        # Calculate position using triangulation
        result = TriangulationService.calculate_position(measurements)
        
        if result is None:
            raise InsufficientDataError(
                "Position calculation failed - triangulation returned no result"
            )
        
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
        
        return position
    
    @staticmethod
    def calculate_position_from_data(
        measurements: List[tuple],
        db: Session,
        tag_id: str,
        timestamp: datetime
    ) -> Optional[TagPosition]:
        """
        Calculate and store position from already-fetched measurement data
        Used during data ingestion
        """
        if len(measurements) < settings.min_anchors_for_position:
            return None
        
        result = TriangulationService.calculate_position(measurements)
        if not result:
            return None
        
        x, y, confidence = result
        
        position = TagPosition(
            timestamp=timestamp,
            tag_id=tag_id,
            x_position=x,
            y_position=y,
            confidence=confidence,
            num_anchors=len(measurements)
        )
        db.add(position)
        
        return position
