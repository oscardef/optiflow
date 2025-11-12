from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
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
    status = Column(String, default="present")  # present, missing, unknown
    
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
