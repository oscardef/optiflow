"""Anchor management router"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from ..database import get_db
from ..models import Anchor
from ..schemas import AnchorCreate, AnchorUpdate, AnchorResponse
from ..core import logger

router = APIRouter(prefix="/anchors", tags=["anchors"])

@router.get("", response_model=List[AnchorResponse])
def get_anchors(db: Session = Depends(get_db)):
    """Get all configured anchors"""
    logger.info("Fetching all anchors")
    anchors = db.query(Anchor).all()
    return [AnchorResponse(
        id=a.id,
        mac_address=a.mac_address,
        name=a.name,
        x_position=a.x_position,
        y_position=a.y_position,
        is_active=a.is_active,
        created_at=a.created_at.isoformat(),
        updated_at=a.updated_at.isoformat()
    ) for a in anchors]

@router.post("", response_model=AnchorResponse, status_code=201)
def create_anchor(anchor: AnchorCreate, db: Session = Depends(get_db)):
    """Create a new anchor configuration"""
    existing = db.query(Anchor).filter(Anchor.mac_address == anchor.mac_address).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Anchor with MAC {anchor.mac_address} already exists")
    
    new_anchor = Anchor(
        mac_address=anchor.mac_address,
        name=anchor.name,
        x_position=anchor.x_position,
        y_position=anchor.y_position,
        is_active=anchor.is_active
    )
    db.add(new_anchor)
    db.commit()
    db.refresh(new_anchor)
    
    logger.info(f"Created anchor {new_anchor.id}: {new_anchor.name} at ({new_anchor.x_position}, {new_anchor.y_position})")
    
    return AnchorResponse(
        id=new_anchor.id,
        mac_address=new_anchor.mac_address,
        name=new_anchor.name,
        x_position=new_anchor.x_position,
        y_position=new_anchor.y_position,
        is_active=new_anchor.is_active,
        created_at=new_anchor.created_at.isoformat(),
        updated_at=new_anchor.updated_at.isoformat()
    )

@router.put("/{anchor_id}", response_model=AnchorResponse)
def update_anchor(anchor_id: int, anchor_update: AnchorUpdate, db: Session = Depends(get_db)):
    """Update an existing anchor configuration"""
    anchor = db.query(Anchor).filter(Anchor.id == anchor_id).first()
    if not anchor:
        raise HTTPException(status_code=404, detail=f"Anchor {anchor_id} not found")
    
    if anchor_update.name is not None:
        anchor.name = anchor_update.name
    if anchor_update.x_position is not None:
        anchor.x_position = anchor_update.x_position
    if anchor_update.y_position is not None:
        anchor.y_position = anchor_update.y_position
    if anchor_update.is_active is not None:
        anchor.is_active = anchor_update.is_active
    
    anchor.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(anchor)
    
    logger.info(f"Updated anchor {anchor.id}: {anchor.name}")
    
    return AnchorResponse(
        id=anchor.id,
        mac_address=anchor.mac_address,
        name=anchor.name,
        x_position=anchor.x_position,
        y_position=anchor.y_position,
        is_active=anchor.is_active,
        created_at=anchor.created_at.isoformat(),
        updated_at=anchor.updated_at.isoformat()
    )

@router.delete("/{anchor_id}", status_code=204)
def delete_anchor(anchor_id: int, db: Session = Depends(get_db)):
    """Delete an anchor configuration"""
    anchor = db.query(Anchor).filter(Anchor.id == anchor_id).first()
    if not anchor:
        raise HTTPException(status_code=404, detail=f"Anchor {anchor_id} not found")
    
    logger.info(f"Deleting anchor {anchor.id}: {anchor.name}")
    db.delete(anchor)
    db.commit()
    return None
