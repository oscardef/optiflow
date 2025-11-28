"""Individual inventory item management router"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import InventoryItem, Product
from ..core import logger

router = APIRouter(prefix="/items", tags=["items"])

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
