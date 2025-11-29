"""Individual inventory item management router"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import ItemStatusUpdate
from ..services import InventoryService

router = APIRouter(prefix="/items", tags=["items"])


@router.delete("/{rfid_tag}")
def delete_inventory_item(rfid_tag: str, db: Session = Depends(get_db)):
    """Delete a specific inventory item by RFID tag (EPC)"""
    InventoryService.delete_item(db, rfid_tag)
    return {"success": True, "message": f"Item {rfid_tag} deleted successfully"}


@router.patch("/{rfid_tag}/status")
def update_item_status(rfid_tag: str, status_update: ItemStatusUpdate, db: Session = Depends(get_db)):
    """Update the status of a specific inventory item"""
    item = InventoryService.update_item_status(db, rfid_tag, status_update.status)
    
    return {
        "id": item.id,
        "rfid_tag": item.rfid_tag,
        "status": item.status,
        "product_id": item.product_id
    }
