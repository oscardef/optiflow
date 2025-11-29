"""Anchor management router"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..schemas import AnchorCreate, AnchorUpdate, AnchorResponse
from ..services import AnchorService

router = APIRouter(prefix="/anchors", tags=["anchors"])


@router.get("", response_model=List[AnchorResponse])
def get_anchors(db: Session = Depends(get_db)):
    """Get all configured anchors"""
    anchors = AnchorService.get_all(db)
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
    new_anchor = AnchorService.create(
        db=db,
        mac_address=anchor.mac_address,
        name=anchor.name,
        x_position=anchor.x_position,
        y_position=anchor.y_position,
        is_active=anchor.is_active
    )
    
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
    anchor = AnchorService.update(
        db=db,
        anchor_id=anchor_id,
        name=anchor_update.name,
        x_position=anchor_update.x_position,
        y_position=anchor_update.y_position,
        is_active=anchor_update.is_active
    )
    
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
    AnchorService.delete(db, anchor_id)
    return None
