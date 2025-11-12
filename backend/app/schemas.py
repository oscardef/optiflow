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

class DataPacket(BaseModel):
    timestamp: str
    detections: List[DetectionInput]
    uwb_measurements: List[UWBMeasurementInput]

class DetectionResponse(BaseModel):
    id: int
    timestamp: str
    product_id: str
    product_name: str

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
