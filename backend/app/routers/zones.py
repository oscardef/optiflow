"""Zone management router"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Zone

router = APIRouter(prefix="/zones", tags=["zones"])

@router.get("")
def get_zones(db: Session = Depends(get_db)):
    """Get all store zones"""
    zones = db.query(Zone).all()
    return [z.to_dict() for z in zones]
