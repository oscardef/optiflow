from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Numeric, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Detection(Base):
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    product_id = Column(String, index=True)
    product_name = Column(String)
    x_position = Column(Float, nullable=True)  # Item location
    y_position = Column(Float, nullable=True)
    status = Column(String, default="present")  # present, not present
    
    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "product_id": self.product_id,
            "product_name": self.product_name,
            "x_position": self.x_position,
            "y_position": self.y_position,
            "status": self.status
        }

class UWBMeasurement(Base):
    __tablename__ = "uwb_measurements"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    mac_address = Column(String, index=True)
    distance_cm = Column(Float)
    status = Column(String, nullable=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "mac_address": self.mac_address,
            "distance_cm": self.distance_cm,
            "status": self.status
        }

class Anchor(Base):
    """UWB anchor configuration - stores physical anchor positions on store map"""
    __tablename__ = "anchors"

    id = Column(Integer, primary_key=True, index=True)
    mac_address = Column(String, unique=True, index=True)  # e.g., "0x0001"
    name = Column(String)  # e.g., "Front Left"
    x_position = Column(Float)  # X coordinate on map (in cm or pixels)
    y_position = Column(Float)  # Y coordinate on map (in cm or pixels)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "mac_address": self.mac_address,
            "name": self.name,
            "x_position": self.x_position,
            "y_position": self.y_position,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

class TagPosition(Base):
    """Calculated tag positions based on triangulation"""
    __tablename__ = "tag_positions"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    tag_id = Column(String, index=True)  # Identifier for the tag (could be MAC or employee ID)
    x_position = Column(Float)  # Calculated X position
    y_position = Column(Float)  # Calculated Y position
    confidence = Column(Float)  # Confidence score (0-1) based on measurement quality
    num_anchors = Column(Integer)  # Number of anchors used in calculation
    
    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "tag_id": self.tag_id,
            "x_position": self.x_position,
            "y_position": self.y_position,
            "confidence": self.confidence,
            "num_anchors": self.num_anchors
        }

class Product(Base):
    """Master catalog of all products in the store"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), index=True)
    unit_price = Column(Numeric(10, 2))
    reorder_threshold = Column(Integer, nullable=True, default=None)
    optimal_stock_level = Column(Integer, nullable=True, default=None)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    inventory_items = relationship("InventoryItem", back_populates="product")
    stock_level = relationship("StockLevel", back_populates="product", uselist=False)
    purchase_events = relationship("PurchaseEvent", back_populates="product")
    
    def to_dict(self):
        return {
            "id": self.id,
            "sku": self.sku,
            "name": self.name,
            "category": self.category,
            "unit_price": float(self.unit_price) if self.unit_price else None,
            "reorder_threshold": self.reorder_threshold,
            "optimal_stock_level": self.optimal_stock_level,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class Zone(Base):
    """Store map divided into zones for heat mapping"""
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    x_min = Column(Float, nullable=False)
    y_min = Column(Float, nullable=False)
    x_max = Column(Float, nullable=False)
    y_max = Column(Float, nullable=False)
    zone_type = Column(String(50), index=True)  # aisle, checkout, entrance, storage
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    inventory_items = relationship("InventoryItem", back_populates="zone")
    purchase_events = relationship("PurchaseEvent", back_populates="zone")
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.zone_type,  # Using zone_type as description
            "x_min": self.x_min,
            "y_min": self.y_min,
            "x_max": self.x_max,
            "y_max": self.y_max,
            "zone_type": self.zone_type,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class InventoryItem(Base):
    """Individual RFID-tagged items in the store"""
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    rfid_tag = Column(String(50), unique=True, nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), default="present", index=True)  # present, not present
    x_position = Column(Float)
    y_position = Column(Float)
    zone_id = Column(Integer, ForeignKey("zones.id", ondelete="SET NULL"), index=True)
    last_seen_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="inventory_items")
    zone = relationship("Zone", back_populates="inventory_items")
    purchase_event = relationship("PurchaseEvent", back_populates="inventory_item", uselist=False)
    
    def to_dict(self):
        return {
            "id": self.id,
            "rfid_tag": self.rfid_tag,
            "product_id": self.product_id,
            "status": self.status,
            "x_position": self.x_position,
            "y_position": self.y_position,
            "zone_id": self.zone_id,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class StockLevel(Base):
    """Aggregated current stock counts per product"""
    __tablename__ = "stock_levels"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    current_count = Column(Integer, default=0)
    missing_count = Column(Integer, default=0)
    sold_today = Column(Integer, default=0)
    max_items_seen = Column(Integer, default=0)  # Track historical maximum for depletion calculation
    last_restock_at = Column(DateTime)
    priority_score = Column(Float, default=0.0, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="stock_level")
    
    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "current_count": self.current_count,
            "missing_count": self.missing_count,
            "sold_today": self.sold_today,
            "max_items_seen": self.max_items_seen,
            "last_restock_at": self.last_restock_at.isoformat() if self.last_restock_at else None,
            "priority_score": self.priority_score,
            "updated_at": self.updated_at.isoformat()
        }

class ProductLocationHistory(Base):
    """Track maximum items seen per product per location cluster for heatmap depletion"""
    __tablename__ = "product_location_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    zone_id = Column(Integer, ForeignKey("zones.id", ondelete="CASCADE"), nullable=True, index=True)  # Nullable for items without zone
    x_center = Column(Float)  # Center of location cluster
    y_center = Column(Float)
    max_items_seen = Column(Integer, default=0)
    current_count = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "zone_id": self.zone_id,
            "x_center": self.x_center,
            "y_center": self.y_center,
            "max_items_seen": self.max_items_seen,
            "current_count": self.current_count,
            "depletion_percentage": round(((self.max_items_seen - self.current_count) / self.max_items_seen * 100), 1) if self.max_items_seen > 0 else 0,
            "last_updated": self.last_updated.isoformat()
        }

class PurchaseEvent(Base):
    """Track when items are sold (for analytics)"""
    __tablename__ = "purchase_events"

    id = Column(Integer, primary_key=True, index=True)
    inventory_item_id = Column(Integer, ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    x_position = Column(Float)
    y_position = Column(Float)
    zone_id = Column(Integer, ForeignKey("zones.id", ondelete="SET NULL"), index=True)
    purchased_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    inventory_item = relationship("InventoryItem", back_populates="purchase_event")
    product = relationship("Product", back_populates="purchase_events")
    zone = relationship("Zone", back_populates="purchase_events")
    
    def to_dict(self):
        return {
            "id": self.id,
            "inventory_item_id": self.inventory_item_id,
            "product_id": self.product_id,
            "x_position": self.x_position,
            "y_position": self.y_position,
            "zone_id": self.zone_id,
            "purchased_at": self.purchased_at.isoformat()
        }

class Configuration(Base):
    """System configuration (singleton table - should only have one row)"""
    __tablename__ = "configuration"

    id = Column(Integer, primary_key=True, index=True)
    store_width = Column(Integer, default=1000)  # cm
    store_height = Column(Integer, default=800)  # cm
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "store_width": self.store_width,
            "store_height": self.store_height,
            "updated_at": self.updated_at.isoformat()
        }

class StockSnapshot(Base):
    """Periodic snapshots of stock levels for time-series analytics"""
    __tablename__ = "stock_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    present_count = Column(Integer, default=0)
    missing_count = Column(Integer, default=0)
    zone_id = Column(Integer, ForeignKey("zones.id", ondelete="SET NULL"), index=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "timestamp": self.timestamp.isoformat(),
            "present_count": self.present_count,
            "missing_count": self.missing_count,
            "zone_id": self.zone_id
        }

class StockMovement(Base):
    """Track individual stock movements for detailed analytics"""
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    movement_type = Column(String(20), nullable=False, index=True)  # sale, restock, loss, adjustment
    quantity = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    notes = Column(Text, nullable=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "movement_type": self.movement_type,
            "quantity": self.quantity,
            "timestamp": self.timestamp.isoformat(),
            "notes": self.notes
        }
