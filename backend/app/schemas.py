from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class UWBMeasurementInput(BaseModel):
    mac_address: str
    distance_cm: float
    status: Optional[str] = None

class DetectionInput(BaseModel):
    product_id: str
    product_name: str
    x_position: Optional[float] = None  # Item location in store
    y_position: Optional[float] = None
    status: Optional[str] = "present"  # "present", "missing", "unknown"

class DataPacket(BaseModel):
    timestamp: str
    detections: List[DetectionInput]
    uwb_measurements: List[UWBMeasurementInput]

class DetectionResponse(BaseModel):
    id: int
    timestamp: str
    product_id: str
    product_name: str
    x_position: Optional[float] = None
    y_position: Optional[float] = None
    status: Optional[str] = "present"

    class Config:
        from_attributes = True

class UWBMeasurementResponse(BaseModel):
    id: int
    timestamp: str
    mac_address: str
    distance_cm: float
    status: Optional[str] = None

    class Config:
        from_attributes = True

class LatestDataResponse(BaseModel):
    detections: List[DetectionResponse]
    uwb_measurements: List[UWBMeasurementResponse]

# Anchor schemas
class AnchorCreate(BaseModel):
    mac_address: str
    name: str
    x_position: float
    y_position: float
    is_active: Optional[bool] = True

class AnchorUpdate(BaseModel):
    name: Optional[str] = None
    x_position: Optional[float] = None
    y_position: Optional[float] = None
    is_active: Optional[bool] = None

class AnchorResponse(BaseModel):
    id: int
    mac_address: str
    name: str
    x_position: float
    y_position: float
    is_active: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

# Tag position schemas
class TagPositionResponse(BaseModel):
    id: int
    timestamp: str
    tag_id: str
    x_position: float
    y_position: float
    confidence: float
    num_anchors: int

    class Config:
        from_attributes = True
