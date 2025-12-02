from pydantic import BaseModel
from typing import List, Optional, Dict, Any
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
    timestamp: Optional[str] = None
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

# Product schemas
class ProductCreate(BaseModel):
    sku: str
    name: str
    category: str
    unit_price: Optional[float] = None
    reorder_threshold: Optional[int] = None
    optimal_stock_level: Optional[int] = None

class ProductResponse(BaseModel):
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

# Analytics schemas
class AnalyticsOverviewResponse(BaseModel):
    total_products: int
    total_stock_value: float
    items_needing_restock: int
    sales_today: int
    sales_last_7_days: int
    sales_last_30_days: int
    low_stock_products: List[Dict]
    timestamp: str

class ProductVelocityResponse(BaseModel):
    product_id: int
    sku: str
    name: str
    category: str
    current_stock: int
    sales_7_days: int
    sales_30_days: int
    velocity_daily: float
    turnover_rate: float
    days_until_stockout: Optional[float]
    abc_class: Optional[str] = None

class CategoryPerformanceResponse(BaseModel):
    category: str
    product_count: int
    total_stock: int
    sales_30_days: int
    total_revenue: float
    avg_velocity: float

class StockTrendPoint(BaseModel):
    timestamp: str
    present_count: int
    missing_count: int

class ProductStockTrendResponse(BaseModel):
    product_id: int
    sku: str
    name: str
    data_points: List[StockTrendPoint]

class AIClusterResponse(BaseModel):
    cluster_id: int
    size: int
    avg_velocity: float
    avg_stock: float
    products: List[Dict]

class DemandForecastResponse(BaseModel):
    product_id: int
    forecast: List[float]
    average_daily_sales: float
    confidence: str
    historical_variance: float

class AnomalyResponse(BaseModel):
    product_id: int
    sku: str
    name: str
    anomaly_type: str
    severity: str
    z_score: float
    recent_sales: int
    expected_sales: float
    detected_at: str

class ProductAffinityResponse(BaseModel):
    product1_id: int
    product1_name: str
    product2_id: int
    product2_name: str
    frequency: int
    support: float
    confidence: float

class ABCAnalysisResponse(BaseModel):
    classification: str
    products: List[Dict]
