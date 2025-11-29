"""Data ingestion and retrieval service"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from ..models import (
    Detection, UWBMeasurement, TagPosition, Anchor,
    InventoryItem, Product, Zone, PurchaseEvent, 
    ProductLocationHistory, StockLevel
)
from ..triangulation import TriangulationService
from ..core import logger
from ..core.exceptions import DatabaseError


class DataService:
    """Service for data ingestion and retrieval"""
    
    @staticmethod
    def store_detection(
        db: Session,
        timestamp: datetime,
        product_id: str,
        product_name: str,
        status: str,
        x_position: Optional[float] = None,
        y_position: Optional[float] = None
    ) -> Detection:
        """Store a single detection record"""
        # Normalize status values
        status_val = status if status else "present"
        if status_val == 'missing':
            status_val = 'not present'
        
        detection = Detection(
            timestamp=timestamp,
            product_id=product_id,
            product_name=product_name,
            x_position=x_position,
            y_position=y_position,
            status=status_val
        )
        db.add(detection)
        db.flush()
        return detection
    
    @staticmethod
    def store_uwb_measurement(
        db: Session,
        timestamp: datetime,
        mac_address: str,
        distance_cm: float,
        status: Optional[str] = None
    ) -> UWBMeasurement:
        """Store a single UWB measurement"""
        measurement = UWBMeasurement(
            timestamp=timestamp,
            mac_address=mac_address,
            distance_cm=distance_cm,
            status=status
        )
        db.add(measurement)
        db.flush()
        return measurement
    
    @staticmethod
    def sync_to_inventory(
        db: Session,
        product_id: str,
        product_name: str,
        status: str,
        timestamp: datetime,
        x_position: Optional[float] = None,
        y_position: Optional[float] = None
    ) -> InventoryItem:
        """Sync detection data to inventory_items table"""
        # Normalize status
        status_val = status if status else "present"
        if status_val == 'missing':
            status_val = 'not present'
        
        inventory_item = db.query(InventoryItem).filter(
            InventoryItem.rfid_tag == product_id
        ).first()
        
        if not inventory_item:
            # Create new inventory item (find or create product first)
            product = db.query(Product).filter(Product.name == product_name).first()
            if not product:
                product = Product(
                    sku=f"GEN-{product_id}",
                    name=product_name,
                    category="General",
                    unit_price=29.99,
                    reorder_threshold=10,
                    optimal_stock_level=50
                )
                db.add(product)
                db.flush()
            
            # Determine zone based on position
            zone = DataService._get_zone_from_position(db, x_position, y_position)
            
            inventory_item = InventoryItem(
                rfid_tag=product_id,
                product_id=product.id,
                status=status_val,
                x_position=x_position,
                y_position=y_position,
                zone_id=zone.id if zone else None,
                last_seen_at=timestamp
            )
            db.add(inventory_item)
        else:
            # Update existing
            inventory_item.status = status_val
            inventory_item.x_position = x_position
            inventory_item.y_position = y_position
            inventory_item.last_seen_at = timestamp
            
            # Update zone if position changed
            zone = DataService._get_zone_from_position(db, x_position, y_position)
            if zone:
                inventory_item.zone_id = zone.id
        
        return inventory_item
    
    @staticmethod
    def _get_zone_from_position(
        db: Session,
        x: Optional[float],
        y: Optional[float]
    ) -> Optional[Zone]:
        """Get zone based on x, y position"""
        if x is None or y is None:
            return None
        
        zones = db.query(Zone).all()
        for zone in zones:
            if (zone.x_min <= x <= zone.x_max and 
                zone.y_min <= y <= zone.y_max):
                return zone
        return None
    
    @staticmethod
    def calculate_position(
        db: Session,
        timestamp: datetime,
        uwb_measurements: List[Dict[str, Any]],
        tag_id: str = "tag_0x42"
    ) -> Optional[TagPosition]:
        """Calculate and store tag position from UWB measurements"""
        anchors = db.query(Anchor).filter(Anchor.is_active == True).all()
        
        if len(anchors) < 2 or len(uwb_measurements) < 2:
            return None
        
        measurements = []
        for uwb in uwb_measurements:
            anchor = next(
                (a for a in anchors if a.mac_address == uwb.get('mac_address')), 
                None
            )
            if anchor:
                measurements.append((
                    anchor.x_position,
                    anchor.y_position,
                    uwb.get('distance_cm')
                ))
        
        if len(measurements) < 2:
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
    
    @staticmethod
    def get_latest_detections(db: Session, limit: int = 50) -> List[Detection]:
        """Get the most recent detections"""
        return db.query(Detection)\
            .order_by(Detection.timestamp.desc())\
            .limit(limit)\
            .all()
    
    @staticmethod
    def get_latest_uwb_measurements(db: Session, limit: int = 50) -> List[UWBMeasurement]:
        """Get the most recent UWB measurements"""
        return db.query(UWBMeasurement)\
            .order_by(UWBMeasurement.timestamp.desc())\
            .limit(limit)\
            .all()
    
    @staticmethod
    def get_stats(db: Session) -> Dict[str, Any]:
        """Get basic statistics about stored data"""
        total_detections = db.query(Detection).count()
        total_uwb = db.query(UWBMeasurement).count()
        unique_items = db.query(Detection.product_id).distinct().count()
        missing_items = db.query(Detection.product_id)\
            .filter(Detection.status == 'not present')\
            .distinct().count()
        
        latest_detection = db.query(Detection).order_by(Detection.timestamp.desc()).first()
        latest_uwb = db.query(UWBMeasurement).order_by(UWBMeasurement.timestamp.desc()).first()
        
        return {
            "total_detections": total_detections,
            "unique_items": unique_items,
            "missing_items": missing_items,
            "total_uwb_measurements": total_uwb,
            "latest_detection_time": latest_detection.timestamp.isoformat() if latest_detection else None,
            "latest_uwb_time": latest_uwb.timestamp.isoformat() if latest_uwb else None
        }
    
    @staticmethod
    def clear_tracking_data(db: Session, keep_hours: int = 0) -> Dict[str, int]:
        """Clear old tracking data"""
        try:
            inventory_deleted = 0
            purchase_events_deleted = 0
            location_history_deleted = 0
            stock_levels_reset = 0
            
            if keep_hours > 0:
                cutoff_time = datetime.utcnow() - timedelta(hours=keep_hours)
                
                positions_deleted = db.query(TagPosition).filter(
                    TagPosition.timestamp < cutoff_time
                ).delete()
                
                detections_deleted = db.query(Detection).filter(
                    Detection.timestamp < cutoff_time
                ).delete()
                
                uwb_deleted = db.query(UWBMeasurement).filter(
                    UWBMeasurement.timestamp < cutoff_time
                ).delete()
                
                inventory_deleted = db.query(InventoryItem).filter(
                    InventoryItem.last_seen_at < cutoff_time
                ).delete()
                
                location_history_deleted = db.query(ProductLocationHistory).filter(
                    ProductLocationHistory.last_updated < cutoff_time
                ).delete()
            else:
                positions_deleted = db.query(TagPosition).delete()
                detections_deleted = db.query(Detection).delete()
                uwb_deleted = db.query(UWBMeasurement).delete()
                inventory_deleted = db.query(InventoryItem).delete()
                purchase_events_deleted = db.query(PurchaseEvent).delete()
                location_history_deleted = db.query(ProductLocationHistory).delete()
                
                stock_levels = db.query(StockLevel).all()
                for stock_level in stock_levels:
                    stock_level.max_items_seen = 0
                stock_levels_reset = len(stock_levels)
            
            db.commit()
            
            logger.info(f"Cleared data: {positions_deleted} positions, {detections_deleted} detections, {uwb_deleted} UWB")
            
            return {
                "positions_deleted": positions_deleted,
                "detections_deleted": detections_deleted,
                "uwb_measurements_deleted": uwb_deleted,
                "inventory_items_deleted": inventory_deleted,
                "purchase_events_deleted": purchase_events_deleted,
                "location_history_deleted": location_history_deleted,
                "stock_levels_reset": stock_levels_reset
            }
        except Exception as e:
            db.rollback()
            raise DatabaseError(f"Error clearing data: {str(e)}")
