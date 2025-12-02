"""Individual inventory item management router"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from ..database import get_db
from ..models import InventoryItem, Product
from ..core import logger

router = APIRouter(prefix="/items", tags=["items"])

class InventoryItemCreate(BaseModel):
    rfid_tag: str
    product_id: int
    status: str = "present"
    x_position: Optional[float] = None
    y_position: Optional[float] = None
    zone_id: Optional[int] = None

@router.get("")
def get_all_items(db: Session = Depends(get_db)):
    """Get all inventory items"""
    items = db.query(InventoryItem).all()
    return [item.to_dict() for item in items]

@router.post("")
def create_inventory_item(item: InventoryItemCreate, db: Session = Depends(get_db)):
    """Create a new inventory item"""
    # Check if product exists
    product = db.query(Product).filter(Product.id == item.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
    
    # Check if RFID tag already exists
    existing = db.query(InventoryItem).filter(InventoryItem.rfid_tag == item.rfid_tag).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Item with RFID tag {item.rfid_tag} already exists")
    
    # Create item
    new_item = InventoryItem(
        rfid_tag=item.rfid_tag,
        product_id=item.product_id,
        status=item.status,
        x_position=item.x_position,
        y_position=item.y_position,
        zone_id=item.zone_id,
        last_seen_at=datetime.utcnow()
    )
    
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    
    logger.info(f"Created inventory item {item.rfid_tag} for product {product.sku}")
    
    return new_item.to_dict()

@router.delete("/{rfid_tag}")
def delete_inventory_item(rfid_tag: str, db: Session = Depends(get_db)):
    """Delete a specific inventory item by RFID tag (EPC)"""
    item = db.query(InventoryItem).filter(InventoryItem.rfid_tag == rfid_tag).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    product = db.query(Product).filter(Product.id == item.product_id).first()
    product_info = f"{product.name} (SKU: {product.sku})" if product else f"Product ID {item.product_id}"
    
    db.delete(item)
    db.commit()
    
    logger.info(f"Deleted inventory item {rfid_tag} from {product_info}")
    
    return {"success": True, "message": f"Item {rfid_tag} deleted successfully"}

@router.patch("/{rfid_tag}/status")
def update_item_status(rfid_tag: str, status_update: dict, db: Session = Depends(get_db)):
    """Update the status of a specific inventory item"""
    item = db.query(InventoryItem).filter(InventoryItem.rfid_tag == rfid_tag).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    new_status = status_update.get('status')
    if new_status not in ['present', 'not present']:
        raise HTTPException(status_code=400, detail="Status must be 'present' or 'not present'")
    
    item.status = new_status
    db.commit()
    db.refresh(item)
    
    logger.info(f"Updated item {rfid_tag} status to {new_status}")
    
    return {
        "id": item.id,
        "rfid_tag": item.rfid_tag,
        "status": item.status,
        "product_id": item.product_id
    }
