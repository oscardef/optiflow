"""Anchor management service"""
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional

from ..models import Anchor
from ..core import logger
from ..core.exceptions import ResourceNotFoundError, ResourceAlreadyExistsError


class AnchorService:
    """Service for managing UWB anchors"""
    
    @staticmethod
    def get_all(db: Session) -> List[Anchor]:
        """Get all configured anchors"""
        logger.info("Fetching all anchors")
        return db.query(Anchor).all()
    
    @staticmethod
    def get_active(db: Session) -> List[Anchor]:
        """Get all active anchors"""
        return db.query(Anchor).filter(Anchor.is_active == True).all()
    
    @staticmethod
    def get_by_id(db: Session, anchor_id: int) -> Anchor:
        """Get anchor by ID"""
        anchor = db.query(Anchor).filter(Anchor.id == anchor_id).first()
        if not anchor:
            raise ResourceNotFoundError("Anchor", anchor_id)
        return anchor
    
    @staticmethod
    def get_by_mac(db: Session, mac_address: str) -> Optional[Anchor]:
        """Get anchor by MAC address"""
        return db.query(Anchor).filter(Anchor.mac_address == mac_address).first()
    
    @staticmethod
    def create(
        db: Session,
        mac_address: str,
        name: str,
        x_position: float,
        y_position: float,
        is_active: bool = True
    ) -> Anchor:
        """Create a new anchor"""
        # Check if anchor with this MAC already exists
        existing = AnchorService.get_by_mac(db, mac_address)
        if existing:
            raise ResourceAlreadyExistsError("Anchor", mac_address)
        
        anchor = Anchor(
            mac_address=mac_address,
            name=name,
            x_position=x_position,
            y_position=y_position,
            is_active=is_active
        )
        db.add(anchor)
        db.commit()
        db.refresh(anchor)
        
        logger.info(f"Created anchor {anchor.id}: {name} at ({x_position}, {y_position})")
        return anchor
    
    @staticmethod
    def update(
        db: Session,
        anchor_id: int,
        name: Optional[str] = None,
        x_position: Optional[float] = None,
        y_position: Optional[float] = None,
        is_active: Optional[bool] = None
    ) -> Anchor:
        """Update an existing anchor"""
        anchor = AnchorService.get_by_id(db, anchor_id)
        
        if name is not None:
            anchor.name = name
        if x_position is not None:
            anchor.x_position = x_position
        if y_position is not None:
            anchor.y_position = y_position
        if is_active is not None:
            anchor.is_active = is_active
        
        anchor.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(anchor)
        
        logger.info(f"Updated anchor {anchor.id}: {anchor.name}")
        return anchor
    
    @staticmethod
    def delete(db: Session, anchor_id: int) -> None:
        """Delete an anchor"""
        anchor = AnchorService.get_by_id(db, anchor_id)
        logger.info(f"Deleting anchor {anchor.id}: {anchor.name}")
        db.delete(anchor)
        db.commit()
