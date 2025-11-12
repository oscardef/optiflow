from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Detection(Base):
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    product_id = Column(String, index=True)
    product_name = Column(String)
    
    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "product_id": self.product_id,
            "product_name": self.product_name
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
