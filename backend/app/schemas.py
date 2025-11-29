"""
Pydantic schemas for API request/response validation
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# ==============================================================================
# Enums
# ==============================================================================

class ItemStatus(str, Enum):
    """Status values for inventory items"""
    PRESENT = "present"
    NOT_PRESENT = "not present"
    MISSING = "missing"
    UNKNOWN = "unknown"


class ZoneType(str, Enum):
    """Types of store zones"""
    AISLE = "aisle"
    CHECKOUT = "checkout"
    ENTRANCE = "entrance"
    STORAGE = "storage"


# ==============================================================================
# UWB Measurement Schemas
# ==============================================================================

class UWBMeasurementInput(BaseModel):
    """Input schema for UWB distance measurement"""
    mac_address: str = Field(..., description="MAC address of the anchor")
    distance_cm: float = Field(..., ge=0, description="Distance in centimeters")
    status: Optional[str] = Field(None, description="Status code from device")


class UWBMeasurementResponse(BaseModel):
    """Response schema for UWB measurement"""
    id: int
    timestamp: str
    mac_address: str
    distance_cm: float
    status: Optional[str] = None

    class Config:
        from_attributes = True


# ==============================================================================
# Detection Schemas
# ==============================================================================

class DetectionInput(BaseModel):
    """Input schema for item detection"""
    product_id: str = Field(..., description="Unique product/RFID identifier")
    product_name: str = Field(..., description="Human-readable product name")
    x_position: Optional[float] = Field(None, description="X coordinate in store (cm)")
    y_position: Optional[float] = Field(None, description="Y coordinate in store (cm)")
    status: Optional[str] = Field("present", description="Item status: present, missing, unknown")
    
    @field_validator('status')
    @classmethod
    def normalize_status(cls, v: Optional[str]) -> str:
        if v is None:
            return "present"
        v = v.lower()
        if v == "missing":
            return "not present"
        return v


class DetectionResponse(BaseModel):
    """Response schema for detection"""
    id: int
    timestamp: Optional[str] = None
    product_id: str
    product_name: str
    x_position: Optional[float] = None
    y_position: Optional[float] = None
    status: Optional[str] = "present"

    class Config:
        from_attributes = True


# ==============================================================================
# Data Packet Schemas
# ==============================================================================

class DataPacket(BaseModel):
    """Combined data packet from devices containing detections and UWB measurements"""
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    detections: List[DetectionInput] = Field(default_factory=list)
    uwb_measurements: List[UWBMeasurementInput] = Field(default_factory=list)


class LatestDataResponse(BaseModel):
    """Response schema for latest data endpoint"""
    detections: List[DetectionResponse]
    uwb_measurements: List[UWBMeasurementResponse]


class DataStoreResponse(BaseModel):
    """Response schema for data storage endpoint"""
    status: str = "success"
    detections_stored: int
    uwb_measurements_stored: int
    position_calculated: bool


# ==============================================================================
# Anchor Schemas
# ==============================================================================

class AnchorCreate(BaseModel):
    """Schema for creating a new anchor"""
    mac_address: str = Field(..., description="Unique MAC address identifier")
    name: str = Field(..., min_length=1, max_length=100, description="Display name")
    x_position: float = Field(..., ge=0, description="X coordinate on store map (cm)")
    y_position: float = Field(..., ge=0, description="Y coordinate on store map (cm)")
    is_active: Optional[bool] = Field(True, description="Whether anchor is active")


class AnchorUpdate(BaseModel):
    """Schema for updating an anchor"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    x_position: Optional[float] = Field(None, ge=0)
    y_position: Optional[float] = Field(None, ge=0)
    is_active: Optional[bool] = None


class AnchorResponse(BaseModel):
    """Response schema for anchor"""
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


# ==============================================================================
# Tag Position Schemas
# ==============================================================================

class TagPositionResponse(BaseModel):
    """Response schema for calculated tag position"""
    id: int
    timestamp: str
    tag_id: str
    x_position: float
    y_position: float
    confidence: float = Field(..., ge=0, le=1, description="Confidence score (0-1)")
    num_anchors: int = Field(..., ge=0, description="Number of anchors used")

    class Config:
        from_attributes = True


# ==============================================================================
# Product Schemas
# ==============================================================================

class ProductCreate(BaseModel):
    """Schema for creating a new product"""
    sku: str = Field(..., min_length=1, max_length=100, description="Stock keeping unit")
    name: str = Field(..., min_length=1, max_length=255, description="Product name")
    category: str = Field(..., min_length=1, max_length=100, description="Product category")
    unit_price: Optional[float] = Field(None, ge=0, description="Price per unit")
    reorder_threshold: Optional[int] = Field(None, ge=0, description="Minimum stock before reorder")
    optimal_stock_level: Optional[int] = Field(None, ge=0, description="Optimal stock quantity")


class ProductUpdate(BaseModel):
    """Schema for updating a product"""
    sku: Optional[str] = Field(None, min_length=1, max_length=100)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    unit_price: Optional[float] = Field(None, ge=0)
    reorder_threshold: Optional[int] = Field(None, ge=0)
    optimal_stock_level: Optional[int] = Field(None, ge=0)


class ProductResponse(BaseModel):
    """Response schema for product"""
    id: int
    sku: str
    name: str
    category: str
    unit_price: Optional[float] = None
    reorder_threshold: Optional[int] = None
    optimal_stock_level: Optional[int] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ProductWithStockResponse(ProductResponse):
    """Product response with current stock information"""
    current_stock: int = 0
    max_detected: int = 0


# ==============================================================================
# Inventory Item Schemas
# ==============================================================================

class InventoryItemResponse(BaseModel):
    """Response schema for inventory item"""
    id: int
    rfid_tag: str
    product_id: int
    status: str
    x_position: Optional[float] = None
    y_position: Optional[float] = None
    zone_id: Optional[int] = None
    last_seen_at: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class InventorySummary(BaseModel):
    """Summary of inventory for a product"""
    in_stock: int = 0
    missing: int = 0
    total: int = 0
    max_detected: int = 0


class ItemDetailResponse(BaseModel):
    """Detailed response for a single inventory item"""
    rfid_tag: str
    product_id: int
    name: str
    x_position: Optional[float] = None
    y_position: Optional[float] = None
    status: str
    last_seen: Optional[str] = None
    zone: Optional[Dict[str, Any]] = None
    inventory_summary: InventorySummary


class ItemStatusUpdate(BaseModel):
    """Schema for updating item status"""
    status: str = Field(..., description="New status: 'present' or 'not present'")
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ['present', 'not present']:
            raise ValueError("Status must be 'present' or 'not present'")
        return v


# ==============================================================================
# Zone Schemas
# ==============================================================================

class ZoneCreate(BaseModel):
    """Schema for creating a zone"""
    name: str = Field(..., min_length=1, max_length=100)
    x_min: float = Field(..., ge=0)
    y_min: float = Field(..., ge=0)
    x_max: float = Field(..., ge=0)
    y_max: float = Field(..., ge=0)
    zone_type: Optional[str] = Field("aisle", description="Zone type: aisle, checkout, entrance, storage")


class ZoneResponse(BaseModel):
    """Response schema for zone"""
    id: int
    name: str
    description: Optional[str] = None
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    zone_type: str
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


# ==============================================================================
# Analytics Schemas
# ==============================================================================

class HeatmapDataPoint(BaseModel):
    """Single data point for stock heatmap"""
    product_id: int
    product_name: str
    product_category: str
    zone_id: int
    zone_name: str
    x: float
    y: float
    current_count: int
    max_items_seen: int
    items_missing: int
    depletion_percentage: float


class PurchaseHeatmapPoint(BaseModel):
    """Single data point for purchase heatmap"""
    zone: ZoneResponse
    purchase_count: int


# ==============================================================================
# Search Schemas
# ==============================================================================

class SearchResult(BaseModel):
    """Single search result item"""
    rfid_tag: str
    product_id: int
    name: str
    sku: str
    category: str
    x: Optional[float] = None
    y: Optional[float] = None
    status: str
    last_seen: Optional[str] = None
    zone_id: Optional[int] = None
    count: Dict[str, int]


class SearchResponse(BaseModel):
    """Response schema for search endpoint"""
    query: str
    total_results: int
    items: List[SearchResult]


# ==============================================================================
# Statistics Schemas
# ==============================================================================

class DataStats(BaseModel):
    """Response schema for data statistics"""
    total_detections: int
    unique_items: int
    missing_items: int
    total_uwb_measurements: int
    latest_detection_time: Optional[str] = None
    latest_uwb_time: Optional[str] = None


class ClearDataResponse(BaseModel):
    """Response schema for clear data endpoint"""
    message: str = "Tracking data cleared successfully"
    positions_deleted: int
    detections_deleted: int
    uwb_measurements_deleted: int
    inventory_items_deleted: int = 0
    purchase_events_deleted: int = 0
    location_history_deleted: int = 0
    stock_levels_reset: int = 0


# ==============================================================================
# Configuration Schemas
# ==============================================================================

class StoreConfigResponse(BaseModel):
    """Response schema for store configuration"""
    store_width: int
    store_height: int
    mode: str


class StoreConfigUpdate(BaseModel):
    """Schema for updating store configuration"""
    store_width: Optional[int] = Field(None, ge=100, le=10000)
    store_height: Optional[int] = Field(None, ge=100, le=10000)


class ModeResponse(BaseModel):
    """Response schema for mode endpoint"""
    mode: str
    simulation_running: bool


class ModeSwitch(BaseModel):
    """Schema for switching modes"""
    mode: str = Field(..., description="SIMULATION or REAL")
    confirm: bool = Field(False, description="Must be true to confirm mode switch")


class LayoutResponse(BaseModel):
    """Response schema for full store layout"""
    mode: str
    store_width: int
    store_height: int
    zones: List[ZoneResponse]
    anchors: List[AnchorResponse]


# ==============================================================================
# Simulation Schemas
# ==============================================================================

class SimulationStatus(BaseModel):
    """Response schema for simulation status"""
    running: bool
    pid: Optional[int] = None
    mode: str
    uptime_seconds: Optional[int] = None


class SimulationParams(BaseModel):
    """Parameters for starting simulation"""
    speed_multiplier: Optional[float] = Field(1.0, ge=0.1, le=10.0)
    mode: Optional[str] = Field("DEMO", description="DEMO, REALISTIC, or STRESS")
    api_url: Optional[str] = None
    disappearance_rate: Optional[float] = Field(0.015, ge=0, le=1.0)


class SimulationStartResponse(BaseModel):
    """Response schema for simulation start"""
    success: bool
    message: str
    pid: Optional[int] = None
    command: Optional[str] = None


class ConnectionStatus(BaseModel):
    """Response schema for connection status"""
    mqtt_connected: bool
    mqtt_broker: str
    mqtt_error: Optional[str] = None
    wifi_ssid: Optional[str] = None
    required_wifi_ssid: Optional[str] = None
    wifi_connected: bool
    wifi_warning: Optional[str] = None


# ==============================================================================
# Error Schemas
# ==============================================================================

class ErrorResponse(BaseModel):
    """Standard error response"""
    detail: str
    error_code: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
