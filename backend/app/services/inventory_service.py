"""Inventory management service"""
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import datetime
from typing import List, Optional, Dict, Any

from ..models import InventoryItem, Product, Zone
from ..core import logger
from ..core.exceptions import ResourceNotFoundError, ValidationError


class InventoryService:
    """Service for managing inventory items"""
    
    @staticmethod
    def get_all_items(db: Session) -> List[tuple]:
        """Get all inventory items with product info"""
        return db.query(InventoryItem, Product)\
            .join(Product, InventoryItem.product_id == Product.id)\
            .all()
    
    @staticmethod
    def get_missing_items(db: Session) -> List[tuple]:
        """Get all items marked as 'not present'"""
        return db.query(InventoryItem, Product)\
            .join(Product, InventoryItem.product_id == Product.id)\
            .filter(InventoryItem.status == 'not present')\
            .all()
    
    @staticmethod
    def get_item_by_rfid(db: Session, rfid_tag: str) -> InventoryItem:
        """Get an inventory item by RFID tag"""
        item = db.query(InventoryItem).filter(InventoryItem.rfid_tag == rfid_tag).first()
        if not item:
            raise ResourceNotFoundError("InventoryItem", rfid_tag)
        return item
    
    @staticmethod
    def get_item_detail(db: Session, rfid_tag: str) -> Dict[str, Any]:
        """Get detailed information about an item including inventory summary"""
        item = InventoryService.get_item_by_rfid(db, rfid_tag)
        
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise ResourceNotFoundError("Product", item.product_id)
        
        # Count items with same product
        same_name_count = db.query(InventoryItem)\
            .filter(
                InventoryItem.product_id == item.product_id,
                InventoryItem.status == "present"
            )\
            .count()
        
        missing_count = db.query(InventoryItem)\
            .filter(
                InventoryItem.product_id == item.product_id,
                InventoryItem.status == "not present"
            )\
            .count()
        
        total_count = db.query(InventoryItem)\
            .filter(InventoryItem.product_id == item.product_id)\
            .count()
        
        # Get zone info if available
        zone_info = None
        if item.zone_id:
            zone = db.query(Zone).filter(Zone.id == item.zone_id).first()
            if zone:
                zone_info = zone.to_dict()
        
        return {
            "rfid_tag": item.rfid_tag,
            "product_id": product.id,
            "name": product.name,
            "x_position": item.x_position,
            "y_position": item.y_position,
            "status": item.status,
            "last_seen": item.last_seen_at.isoformat() if item.last_seen_at else None,
            "zone": zone_info,
            "inventory_summary": {
                "in_stock": same_name_count,
                "missing": missing_count,
                "total": total_count,
                "max_detected": total_count
            }
        }
    
    @staticmethod
    def update_item_status(db: Session, rfid_tag: str, status: str) -> InventoryItem:
        """Update the status of an inventory item"""
        if status not in ['present', 'not present']:
            raise ValidationError("Status must be 'present' or 'not present'")
        
        item = InventoryService.get_item_by_rfid(db, rfid_tag)
        item.status = status
        db.commit()
        db.refresh(item)
        
        logger.info(f"Updated item {rfid_tag} status to {status}")
        return item
    
    @staticmethod
    def delete_item(db: Session, rfid_tag: str) -> None:
        """Delete an inventory item by RFID tag"""
        item = InventoryService.get_item_by_rfid(db, rfid_tag)
        
        product = db.query(Product).filter(Product.id == item.product_id).first()
        product_info = f"{product.name} (SKU: {product.sku})" if product else f"Product ID {item.product_id}"
        
        db.delete(item)
        db.commit()
        
        logger.info(f"Deleted inventory item {rfid_tag} from {product_info}")
    
    @staticmethod
    def search_items(db: Session, query: str, limit: int = 50) -> Dict[str, Any]:
        """Search for items by name, RFID tag, or SKU"""
        search_term = f"%{query}%"
        
        subquery = db.query(
            InventoryItem.product_id,
            func.min(InventoryItem.id).label('first_item_id'),
            func.count(InventoryItem.id).label('total_count'),
            func.sum(case((InventoryItem.status == 'present', 1), else_=0)).label('present_count'),
            func.sum(case((InventoryItem.status == 'not present', 1), else_=0)).label('missing_count')
        )\
        .group_by(InventoryItem.product_id)\
        .subquery()
        
        results_query = db.query(
            InventoryItem,
            Product,
            subquery.c.total_count,
            subquery.c.present_count,
            subquery.c.missing_count
        )\
        .join(Product, InventoryItem.product_id == Product.id)\
        .join(subquery, InventoryItem.id == subquery.c.first_item_id)\
        .filter(
            (Product.name.ilike(search_term)) |
            (InventoryItem.rfid_tag.ilike(search_term)) |
            (Product.sku.ilike(search_term))
        )\
        .limit(limit)\
        .all()
        
        results = []
        for item, product, total_count, present_count, missing_count in results_query:
            results.append({
                "rfid_tag": item.rfid_tag,
                "product_id": product.id,
                "name": product.name,
                "sku": product.sku,
                "category": product.category,
                "x": item.x_position,
                "y": item.y_position,
                "status": "present" if present_count > 0 else "not present",
                "last_seen": item.last_seen_at.isoformat() if item.last_seen_at else None,
                "zone_id": item.zone_id,
                "count": {
                    "total": total_count,
                    "present": present_count,
                    "missing": missing_count
                }
            })
        
        return {
            "query": query,
            "total_results": len(results),
            "items": results
        }
    
    @staticmethod
    def get_or_create_item(
        db: Session,
        rfid_tag: str,
        product_id: int,
        status: str,
        x_position: Optional[float] = None,
        y_position: Optional[float] = None,
        zone_id: Optional[int] = None,
        timestamp: Optional[datetime] = None
    ) -> InventoryItem:
        """Get existing item or create new one"""
        item = db.query(InventoryItem).filter(InventoryItem.rfid_tag == rfid_tag).first()
        
        if item:
            # Update existing
            item.status = status
            item.x_position = x_position
            item.y_position = y_position
            item.zone_id = zone_id
            item.last_seen_at = timestamp or datetime.utcnow()
        else:
            # Create new
            item = InventoryItem(
                rfid_tag=rfid_tag,
                product_id=product_id,
                status=status,
                x_position=x_position,
                y_position=y_position,
                zone_id=zone_id,
                last_seen_at=timestamp or datetime.utcnow()
            )
            db.add(item)
        
        return item
