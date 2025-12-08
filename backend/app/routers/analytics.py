"""Analytics router"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from pydantic import BaseModel
import subprocess
import sys
import re
from pathlib import Path
from typing import Optional

from ..database import get_db
from ..models import (
    InventoryItem, Product,
    PurchaseEvent
)
from ..core import logger

# Helper function to parse date range parameters
def get_date_range(
    days: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> tuple[datetime, datetime]:
    """
    Parse date range from either days or start_date/end_date parameters.
    Returns (start_datetime, end_datetime)
    """
    now = datetime.utcnow()
    
    if start_date and end_date:
        try:
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
            # Set end to end of day
            end = end.replace(hour=23, minute=59, second=59, microsecond=999999)
            return (start, end)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Default to days parameter
    if days is None:
        days = 30
    
    start = now - timedelta(days=days)
    return (start, now)

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
    responses={
        404: {"description": "Resource not found"},
        500: {"description": "Internal server error"}
    }
)

@router.get(
    "/overview",
    summary="Get Analytics Overview",
    description="""
    Retrieve high-level analytics metrics including:
    - Total products and stock value
    - Items needing restock
    - Sales statistics (today, 7 days, 30 days)
    - Low stock products prioritized by urgency
    
    **Use Case**: Dashboard summary, executive reporting
    
    **Update Frequency**: Real-time (query on-demand)
    """,
    response_description="Analytics overview with key performance metrics",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "total_products": 133,
                        "total_stock_value": 45280.50,
                        "items_needing_restock": 12,
                        "sales_today": 8,
                        "sales_last_7_days": 118,
                        "sales_last_30_days": 1153,
                        "low_stock_products": [
                            {
                                "product_id": 42,
                                "sku": "FOT-015",
                                "name": "Tennis Shoes - Size 10",
                                "current_stock": 2,
                                "reorder_threshold": 5,
                                "priority_score": 0.85
                            }
                        ],
                        "timestamp": "2025-11-30T10:30:00.000Z"
                    }
                }
            }
        }
    }
)
def get_analytics_overview(
    days: Optional[int] = Query(None, description="Number of days to look back"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    interval: str = Query("day", description="Time interval for aggregation"),
    db: Session = Depends(get_db)
):
    """
    Get high-level analytics overview with key metrics
    
    Args:
        days: Number of days to look back (7, 30, or 90) - ignored if start_date/end_date provided
        start_date: Custom start date (YYYY-MM-DD format)
        end_date: Custom end date (YYYY-MM-DD format)
        interval: Time interval for aggregation (hour, day, week, month)
    """
    from ..models import StockLevel, InventoryItem
    
    # Get date range
    date_start, date_end = get_date_range(days, start_date, end_date)
    
    # Total products
    total_products = db.query(Product).count()
    
    # Total stock value
    stock_value_query = db.query(
        func.sum(StockLevel.current_count * Product.unit_price)
    ).join(Product).first()
    total_stock_value = float(stock_value_query[0] or 0)
    
    # Items needing restock
    items_needing_restock = db.query(Product).join(StockLevel).filter(
        StockLevel.current_count < Product.reorder_threshold
    ).count()
    
    # Sales statistics based on selected date range
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)
    
    sales_today = db.query(PurchaseEvent).filter(
        PurchaseEvent.purchased_at >= today_start
    ).count()
    
    sales_7_days = db.query(PurchaseEvent).filter(
        PurchaseEvent.purchased_at >= seven_days_ago
    ).count()
    
    sales_30_days = db.query(PurchaseEvent).filter(
        PurchaseEvent.purchased_at >= thirty_days_ago
    ).count()
    
    # Low stock products (top 10)
    low_stock = db.query(Product, StockLevel).join(StockLevel).filter(
        StockLevel.current_count < Product.reorder_threshold
    ).order_by(StockLevel.priority_score.desc()).limit(10).all()
    
    low_stock_products = [
        {
            'product_id': p.id,
            'sku': p.sku,
            'name': p.name,
            'current_stock': sl.current_count,
            'reorder_threshold': p.reorder_threshold,
            'priority_score': sl.priority_score
        }
        for p, sl in low_stock
    ]
    
    # Additional KPIs for enhanced dashboard
    
    # Low stock items (approaching threshold but not critical)
    low_stock_items = db.query(Product).join(StockLevel).filter(
        StockLevel.current_count < Product.reorder_threshold * 1.5,
        StockLevel.current_count >= Product.reorder_threshold
    ).count()
    
    # Average stock level across all products
    avg_stock_query = db.query(func.avg(StockLevel.current_count)).first()
    avg_stock_level = float(avg_stock_query[0] or 0)
    
    # Calculate velocity and coverage for products
    seven_days_ago = now - timedelta(days=7)
    
    # Get products with stock and calculate their velocity
    products_with_stock = db.query(
        Product.id,
        StockLevel.current_count,
        func.count(PurchaseEvent.id).label('sales_7d')
    ).join(StockLevel).outerjoin(
        PurchaseEvent,
        (PurchaseEvent.product_id == Product.id) & 
        (PurchaseEvent.purchased_at >= seven_days_ago)
    ).filter(
        StockLevel.current_count > 0
    ).group_by(Product.id, StockLevel.current_count).all()
    
    # Calculate coverage days and stockout risk
    coverage_days_list = []
    stockout_risk_items = 0
    
    for product_id, current_count, sales_7d in products_with_stock:
        if sales_7d > 0:
            daily_velocity = sales_7d / 7.0
            days_coverage = current_count / daily_velocity
            coverage_days_list.append(days_coverage)
            
            if days_coverage < 7:
                stockout_risk_items += 1
    
    avg_coverage_days = sum(coverage_days_list) / len(coverage_days_list) if coverage_days_list else 0
    
    # Dead stock (no sales in last 30 days with stock > 0)
    products_with_no_sales = db.query(Product.id).join(StockLevel).outerjoin(
        PurchaseEvent,
        (PurchaseEvent.product_id == Product.id) & 
        (PurchaseEvent.purchased_at >= thirty_days_ago)
    ).filter(
        StockLevel.current_count > 0
    ).group_by(Product.id).having(
        func.count(PurchaseEvent.id) == 0
    ).all()
    
    dead_stock_count = len(products_with_no_sales)
    
    # Calculate average turnover rate (sales / avg stock)
    products_with_turnover = db.query(
        func.count(PurchaseEvent.id).label('sales'),
        func.avg(StockLevel.current_count).label('avg_stock')
    ).select_from(Product).join(StockLevel).outerjoin(
        PurchaseEvent,
        (PurchaseEvent.product_id == Product.id) & 
        (PurchaseEvent.purchased_at >= seven_days_ago)
    ).group_by(Product.id).all()
    
    turnover_rates = []
    for sales, avg_stock in products_with_turnover:
        if avg_stock and avg_stock > 0 and sales:
            turnover_rates.append(sales / float(avg_stock))
    
    avg_turnover_rate = sum(turnover_rates) / len(turnover_rates) if turnover_rates else 0
    
    # Total items tracked
    total_items_tracked = db.query(InventoryItem).count()
    present_items = db.query(InventoryItem).filter(InventoryItem.status == 'present').count()
    
    return {
        'total_products': total_products,
        'total_stock_value': round(total_stock_value, 2),
        'items_needing_restock': items_needing_restock,
        'low_stock_items': low_stock_items,
        'avg_stock_level': round(avg_stock_level, 2),
        'avg_coverage_days': round(avg_coverage_days, 1),
        'stockout_risk_items': stockout_risk_items,
        'dead_stock_count': dead_stock_count,
        'avg_turnover_rate': round(avg_turnover_rate, 3),
        'total_items_tracked': total_items_tracked,
        'present_items': present_items,
        'sales_today': sales_today,
        'sales_last_7_days': sales_7_days,
        'sales_last_30_days': sales_30_days,
        'low_stock_products': low_stock_products,
        'timestamp': datetime.utcnow().isoformat()
    }

@router.get(
    "/product-velocity",
    summary="Get Product Velocity",
    description="""
    Calculate product movement velocity and turnover rates.
    
    **Metrics Calculated**:
    - `velocity_daily`: Average items sold per day
    - `total_sold`: Total items sold in period
    - `days_active`: Number of days with sales data
    
    **Use Case**: Identify fast/slow-moving products, inventory planning
    
    **Parameters**:
    - `days`: Analysis period (default: 7 days)
    """,
    response_description="List of products with velocity metrics",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "product_id": 15,
                            "sku": "SPT-003",
                            "name": "Tennis Ball",
                            "category": "Sports",
                            "velocity_daily": 2.5,
                            "total_sold": 18,
                            "days_active": 7
                        }
                    ]
                }
            }
        }
    }
)
def get_product_velocity(
    days: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    interval: str = Query("day"),
    db: Session = Depends(get_db)
):
    """
    Calculate product velocity (turnover rate) for all products
    
    Args:
        days: Number of days to look back (7, 30, or 90)
        start_date: Custom start date (YYYY-MM-DD)
        end_date: Custom end date (YYYY-MM-DD)
        interval: Time interval for aggregation (hour, day, week, month) - for future use
    """
    from ..models import StockLevel
    
    cutoff_date, end_date_dt = get_date_range(days, start_date, end_date)
    calc_days = (end_date_dt - cutoff_date).days
    products = db.query(Product).all()
    
    velocity_data = []
    for product in products:
        # Get sales count
        sales = db.query(PurchaseEvent).filter(
            PurchaseEvent.product_id == product.id,
            PurchaseEvent.purchased_at >= cutoff_date
        ).count()
        
        # Get current stock
        stock = db.query(StockLevel).filter(
            StockLevel.product_id == product.id
        ).first()
        
        current_stock = stock.current_count if stock else 0
        velocity_daily = sales / calc_days if calc_days > 0 else 0
        
        # Calculate turnover rate and days until stockout
        turnover_rate = (sales / max(1, current_stock)) if current_stock > 0 else 0
        days_until_stockout = (current_stock / velocity_daily) if velocity_daily > 0 else None
        
        velocity_data.append({
            'product_id': product.id,
            'sku': product.sku,
            'name': product.name,
            'category': product.category,
            'current_stock': current_stock,
            'sales_7_days': sales if calc_days == 7 else None,
            'sales_30_days': sales if calc_days == 30 else None,
            'velocity_daily': round(velocity_daily, 2),
            'turnover_rate': round(turnover_rate, 2),
            'days_until_stockout': round(days_until_stockout, 1) if days_until_stockout else None
        })
    
    return sorted(velocity_data, key=lambda x: x['velocity_daily'], reverse=True)

@router.get("/top-products")
def get_top_products(
    metric: str = Query('sales'),
    days: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    interval: str = Query("day"),
    limit: int = Query(20),
    db: Session = Depends(get_db)
):
    """
    Get top performing products by various metrics
    
    Args:
        metric: Metric to rank by ('sales', 'revenue', 'velocity')
        days: Number of days to look back (7, 30, or 90)
        start_date: Custom start date (YYYY-MM-DD)
        end_date: Custom end date (YYYY-MM-DD)
        interval: Time interval for aggregation (hour, day, week, month) - for future use
        limit: Maximum number of results to return
    """
    cutoff_date, _ = get_date_range(days, start_date, end_date)
    
    if metric == 'sales':
        # Top by sales count
        results = db.query(
            Product,
            func.count(PurchaseEvent.id).label('sales_count')
        ).join(PurchaseEvent).filter(
            PurchaseEvent.purchased_at >= cutoff_date
        ).group_by(Product.id).order_by(func.count(PurchaseEvent.id).desc()).limit(limit).all()
        
        return [
            {
                'product_id': p.id,
                'sku': p.sku,
                'name': p.name,
                'category': p.category,
                'sales_count': count,
                'metric_value': count
            }
            for p, count in results
        ]
    
    elif metric == 'revenue':
        # Top by revenue
        results = db.query(
            Product,
            func.count(PurchaseEvent.id).label('sales_count')
        ).join(PurchaseEvent).filter(
            PurchaseEvent.purchased_at >= cutoff_date
        ).group_by(Product.id).all()
        
        revenue_data = [
            {
                'product_id': p.id,
                'sku': p.sku,
                'name': p.name,
                'category': p.category,
                'sales_count': count,
                'revenue': count * float(p.unit_price or 0),
                'metric_value': count * float(p.unit_price or 0)
            }
            for p, count in results
        ]
        
        return sorted(revenue_data, key=lambda x: x['revenue'], reverse=True)[:limit]
    
    elif metric == 'velocity':
        # Top by velocity (sales per day)
        results = db.query(
            Product,
            func.count(PurchaseEvent.id).label('sales_count')
        ).join(PurchaseEvent).filter(
            PurchaseEvent.purchased_at >= cutoff_date
        ).group_by(Product.id).all()
        
        velocity_data = [
            {
                'product_id': p.id,
                'sku': p.sku,
                'name': p.name,
                'category': p.category,
                'sales_count': count,
                'velocity': count / days,
                'metric_value': count / days
            }
            for p, count in results
        ]
        
        return sorted(velocity_data, key=lambda x: x['velocity'], reverse=True)[:limit]
    
    return []

@router.get("/category-performance")
def get_category_performance(
    days: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    interval: str = Query("day"),
    db: Session = Depends(get_db)
):
    """
    Aggregate performance metrics by product category
    
    Args:
        days: Number of days to look back (7, 30, or 90)
        start_date: Custom start date (YYYY-MM-DD)
        end_date: Custom end date (YYYY-MM-DD)
        interval: Time interval for aggregation (hour, day, week, month) - for future use
    """
    from ..models import StockLevel
    
    cutoff_date, _ = get_date_range(days, start_date, end_date)
    categories = db.query(Product.category).distinct().all()
    
    category_data = []
    for (category,) in categories:
        products = db.query(Product).filter(Product.category == category).all()
        product_ids = [p.id for p in products]
        
        # Sales count
        sales = db.query(PurchaseEvent).filter(
            PurchaseEvent.product_id.in_(product_ids),
            PurchaseEvent.purchased_at >= cutoff_date
        ).count()
        
        # Revenue
        revenue_query = db.query(
            func.sum(Product.unit_price)
        ).join(PurchaseEvent).filter(
            Product.category == category,
            PurchaseEvent.purchased_at >= cutoff_date
        ).first()
        revenue = float(revenue_query[0] or 0)
        
        # Current stock
        total_stock = db.query(func.sum(StockLevel.current_count)).join(Product).filter(
            Product.category == category
        ).first()[0] or 0
        
        # Average velocity
        avg_velocity = sales / (days * len(products)) if len(products) > 0 else 0
        
        category_data.append({
            'category': category,
            'product_count': len(products),
            'total_stock': total_stock,
            'sales_30_days': sales,
            'total_revenue': round(revenue, 2),
            'avg_velocity': round(avg_velocity, 2)
        })
    
    return sorted(category_data, key=lambda x: x['sales_30_days'], reverse=True)

@router.get(
    "/ai/clusters",
    summary="AI Product Clustering",
    description="""
    K-means clustering analysis to group products by similarity.
    
    **Algorithm**: K-means clustering with scikit-learn
    
    **Features Used**:
    - Sales velocity (normalized)
    - Current stock level (normalized)
    - Category encoding
    
    **Output**: Products grouped into N clusters with centroids
    
    **Use Case**: Inventory segmentation, merchandising strategy
    
    **Parameters**:
    - `n_clusters`: Number of clusters (default: 4)
    """,
    response_description="Product clusters with centroids and member products"
)
def get_ai_clusters(n_clusters: int = 4, db: Session = Depends(get_db)):
    """
    Get AI-powered product clustering analysis
    Groups products by similar characteristics (velocity, stock level, category)
    """
    from ..services.ai_analytics import AIAnalyticsService
    
    ai_service = AIAnalyticsService(db)
    clusters = ai_service.cluster_products(n_clusters=n_clusters)
    
    return {
        'clusters': clusters,
        'n_clusters': len(clusters),
        'timestamp': datetime.utcnow().isoformat()
    }

@router.get(
    "/ai/forecast/{product_id}",
    summary="AI Demand Forecasting",
    description="""
    Predict future demand using exponential smoothing.
    
    **Algorithm**: Exponential smoothing time-series forecasting
    **Input**: Historical stock snapshots (30+ days recommended)
    **Output**: Predicted stock levels for next N days
    **Use Case**: Inventory planning, reorder optimization
    """,
    response_description="Demand forecast with predicted values"
)
def get_demand_forecast(product_id: int, days_ahead: int = 7, db: Session = Depends(get_db)):
    """
    Get AI-powered demand forecast for a specific product
    Uses exponential smoothing for prediction
    """
    from ..services.ai_analytics import AIAnalyticsService
    
    ai_service = AIAnalyticsService(db)
    forecast = ai_service.forecast_demand(product_id, days_ahead)
    
    return forecast

@router.get(
    "/ai/anomalies",
    summary="AI Anomaly Detection",
    description="""
    Detect unusual stock patterns using Z-score analysis.
    
    **Algorithm**: Statistical Z-score anomaly detection
    **Threshold**: |Z-score| > 2.0 (>95% confidence)
    **Detects**: Unexpectedly high/low stock, outliers
    **Use Case**: Identify inventory issues, theft detection, data quality
    """,
    response_description="List of products with anomalous stock levels"
)
def get_anomaly_detection(lookback_days: int = 7, db: Session = Depends(get_db)):
    """
    Detect unusual stock movements and sales patterns using Z-score analysis
    """
    from ..services.ai_analytics import AIAnalyticsService
    
    ai_service = AIAnalyticsService(db)
    anomalies = ai_service.detect_anomalies(lookback_days)
    
    return {
        'anomalies': anomalies,
        'count': len(anomalies),
        'timestamp': datetime.utcnow().isoformat()
    }

@router.post(
    "/bulk/purchases",
    summary="Bulk Insert Purchase Events",
    description="""
    Insert multiple purchase events for historical data backfill or batch processing.
    
    **Expected Format**:
    ```json
    [
        {
            "product_id": 42,
            "purchased_at": "2025-11-29T15:30:00Z"
        }
    ]
    ```
    
    **Notes**:
    - Creates dummy InventoryItem records automatically
    - Position fields (x_position, y_position) are optional
    - Processes in batches for efficiency
    
    **Use Case**: Historical data generation, testing, migration
    """,
    response_description="Status of bulk insert operation",
    responses={
        200: {
            "description": "Successful bulk insert",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "inserted": 500
                    }
                }
            }
        }
    }
)
def bulk_insert_purchases(purchases: list[dict], db: Session = Depends(get_db)):
    """
    Bulk insert historical purchase events for analytics backfill
    Expected format: [{"product_id": int, "purchased_at": str, "x_position": float (optional), "y_position": float (optional)}, ...]
    Note: Creates dummy inventory_item records for historical data
    """
    from ..models import InventoryItem
    
    try:
        inserted = 0
        for purchase_data in purchases:
            # Create a dummy inventory item for historical purchase
            dummy_item = InventoryItem(
                product_id=purchase_data['product_id'],
                rfid_tag=f"HIST_{purchase_data['product_id']}_{inserted}",
                x_position=purchase_data.get('x_position'),
                y_position=purchase_data.get('y_position'),
                status='not_present'  # Historical purchases are gone
            )
            db.add(dummy_item)
            db.flush()  # Get the ID
            
            # Create purchase event
            purchase = PurchaseEvent(
                inventory_item_id=dummy_item.id,
                product_id=purchase_data['product_id'],
                x_position=purchase_data.get('x_position'),
                y_position=purchase_data.get('y_position'),
                purchased_at=datetime.fromisoformat(purchase_data['purchased_at'])
            )
            db.add(purchase)
            inserted += 1
        
        db.commit()
        logger.info(f"Bulk inserted {inserted} purchase events")
        return {"status": "success", "inserted": inserted}
    except Exception as e:
        db.rollback()
        logger.error(f"Error bulk inserting purchases: {e}")
        return {"status": "error", "message": str(e)}

@router.post(
    "/bulk/snapshots",
    summary="Bulk Insert Stock Snapshots",
    description="""
    Insert multiple stock snapshots for time-series analytics.
    
    **Expected Format**:
    ```json
    [
        {
            "product_id": 42,
            "timestamp": "2025-11-29T12:00:00Z",
            "present_count": 15,
            "missing_count": 2
        }
    ]
    ```
    
    **Notes**:
    - Processes in batches of 1000 for efficiency
    - Timestamps should be in ISO 8601 format
    - Snapshots are per-product (not location-specific)
    
    **Use Case**: Historical data generation, periodic backups
    """,
    response_description="Status of bulk insert operation",
    responses={
        200: {
            "description": "Successful bulk insert",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "inserted": 7448
                    }
                }
            }
        }
    }
)
def bulk_insert_snapshots(snapshots: list[dict], db: Session = Depends(get_db)):
    """
    Bulk insert historical stock snapshots for analytics backfill
    Expected format: [{"product_id": int, "timestamp": str, "present_count": int, "missing_count": int}, ...]
    """
    from ..models import StockSnapshot
    
    try:
        inserted = 0
        batch_size = 1000
        
        for i in range(0, len(snapshots), batch_size):
            batch = snapshots[i:i + batch_size]
            for snapshot_data in batch:
                snapshot = StockSnapshot(
                    product_id=snapshot_data['product_id'],
                    timestamp=datetime.fromisoformat(snapshot_data['timestamp']),
                    present_count=snapshot_data.get('present_count', 0),
                    missing_count=snapshot_data.get('missing_count', 0)
                )
                db.add(snapshot)
                inserted += 1
            
            db.commit()
            logger.info(f"Bulk inserted batch: {inserted}/{len(snapshots)} snapshots")
        
        logger.info(f"Bulk inserted {inserted} stock snapshots")
        return {"status": "success", "inserted": inserted}
    except Exception as e:
        db.rollback()
        logger.error(f"Error bulk inserting snapshots: {e}")
        return {"status": "error", "message": str(e)}


class BackfillParams(BaseModel):
    density: Optional[str] = "normal"  # sparse, normal, dense, extreme
    days: Optional[int] = 30

_backfill_process: Optional[subprocess.Popen] = None
_backfill_status = {"running": False, "message": "", "records": 0}

@router.post(
    "/backfill",
    summary="Generate historical analytics data",
    description="Triggers the backfill script to generate historical purchase events and stock snapshots. Uses fast-forward mode for instant data generation.",
    response_description="Status of backfill operation"
)
def trigger_backfill(params: BackfillParams, background_tasks: BackgroundTasks):
    """
    Trigger historical data generation (backfill) for analytics
    
    This endpoint runs the backfill_history.py script to generate historical
    purchase events and stock snapshots. The data is generated instantly using
    the fast-forward mode with configurable density presets.
    
    Parameters:
    - density: Data density (sparse/normal/dense/extreme) - affects frequency of events
    - days: Number of historical days to generate (default 30)
    
    Returns status information about the backfill operation.
    """
    global _backfill_process, _backfill_status
    
    # Check if already running
    if _backfill_status["running"]:
        return {
            "status": "running",
            "message": _backfill_status["message"],
            "records": _backfill_status["records"]
        }
    
    # Validate density
    valid_densities = ["sparse", "normal", "dense", "extreme"]
    if params.density not in valid_densities:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid density. Must be one of: {', '.join(valid_densities)}"
        )
    
    # Find simulation directory
    backend_dir = Path(__file__).parent.parent.parent.parent
    simulation_dir = backend_dir / "simulation"
    
    if not simulation_dir.exists():
        # Try container path
        simulation_dir = Path("/simulation")
        if not simulation_dir.exists():
            raise HTTPException(
                status_code=500,
                detail=f"Simulation directory not found. Checked: {backend_dir / 'simulation'} and /simulation"
            )
    
    backfill_script = simulation_dir / "backfill_history.py"
    if not backfill_script.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Backfill script not found at {backfill_script}"
        )
    
    # Build command with API URL (use localhost since script runs on host or in same container)
    # The backend is accessible at localhost:8000 from within the container
    api_url = "http://localhost:8000"
    cmd = [
        sys.executable,
        str(backfill_script),
        "--days", str(params.days),
        "--density", params.density,
        "--api", api_url
    ]
    
    try:
        # Reset status
        _backfill_status = {
            "running": True,
            "message": f"Generating {params.days} days of {params.density} density data...",
            "records": 0
        }
        
        # Run backfill script synchronously (it's fast with fast-forward mode)
        result = subprocess.run(
            cmd,
            cwd=str(simulation_dir.parent),
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )
        
        if result.returncode == 0:
            # Parse output for record counts
            output = result.stdout
            purchases = 0
            snapshots = 0
            
            # Look for "Purchases uploaded: X" and "Snapshots uploaded: X" lines
            import re
            for line in output.split('\n'):
                if 'purchases uploaded' in line.lower():
                    match = re.search(r'uploaded:\s*(\d+)', line.lower())
                    if match:
                        purchases = int(match.group(1))
                elif 'snapshots uploaded' in line.lower():
                    match = re.search(r'uploaded:\s*(\d+)', line.lower())
                    if match:
                        snapshots = int(match.group(1))
            
            records = purchases + snapshots
            
            _backfill_status = {
                "running": False,
                "message": f"Successfully generated {params.days} days of data ({purchases:,} purchases, {snapshots:,} snapshots)",
                "records": records
            }
            
            logger.info(f"Backfill completed: {params.days} days, {params.density} density - {purchases} purchases, {snapshots} snapshots")
            return {
                "status": "success",
                "message": _backfill_status["message"],
                "records": records,
                "purchases": purchases,
                "snapshots": snapshots,
                "density": params.density,
                "days": params.days
            }
        else:
            _backfill_status = {
                "running": False,
                "message": f"Backfill failed: {result.stderr}",
                "records": 0
            }
            logger.error(f"Backfill failed: {result.stderr}")
            raise HTTPException(
                status_code=500,
                detail=f"Backfill script failed: {result.stderr}"
            )
    
    except subprocess.TimeoutExpired:
        _backfill_status = {
            "running": False,
            "message": "Backfill timed out after 2 minutes",
            "records": 0
        }
        raise HTTPException(
            status_code=500,
            detail="Backfill operation timed out"
        )
    except Exception as e:
        _backfill_status = {
            "running": False,
            "message": f"Error: {str(e)}",
            "records": 0
        }
        logger.error(f"Backfill error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run backfill: {str(e)}"
        )

@router.get("/sales-time-series")
def get_sales_time_series(
    days: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    interval: str = Query("day"),
    db: Session = Depends(get_db)
):
    """
    Get sales time series data aggregated by interval
    
    Args:
        days: Number of days to look back (7, 30, or 90)
        start_date: Custom start date (YYYY-MM-DD)
        end_date: Custom end date (YYYY-MM-DD)
        interval: Time interval for aggregation (hour, day, week, month)
    
    Returns:
        List of data points with date, sales count, and revenue
    """
    cutoff_date, _ = get_date_range(days, start_date, end_date)
    
    # Map interval to SQL date truncation
    if interval == "hour":
        date_trunc = func.date_trunc('hour', PurchaseEvent.purchased_at)
    elif interval == "day":
        date_trunc = func.date_trunc('day', PurchaseEvent.purchased_at)
    elif interval == "week":
        date_trunc = func.date_trunc('week', PurchaseEvent.purchased_at)
    elif interval == "month":
        date_trunc = func.date_trunc('month', PurchaseEvent.purchased_at)
    else:
        date_trunc = func.date_trunc('day', PurchaseEvent.purchased_at)
    
    # Query aggregated sales data
    results = db.query(
        date_trunc.label('date'),
        func.count(PurchaseEvent.id).label('sales'),
        func.coalesce(func.sum(Product.unit_price), 0).label('revenue')
    ).join(
        Product, PurchaseEvent.product_id == Product.id
    ).filter(
        PurchaseEvent.purchased_at >= cutoff_date
    ).group_by(
        date_trunc
    ).order_by(
        date_trunc
    ).all()
    
    # Format results
    time_series = [
        {
            'date': row.date.isoformat() if row.date else None,
            'sales': row.sales,
            'revenue': float(row.revenue)
        }
        for row in results
    ]
    
    return time_series

@router.get(
    "/backfill/status",
    summary="Get backfill operation status",
    description="Check the current status of any running backfill operation",
    response_description="Current backfill status including progress"
)
def get_backfill_status():
    """
    Get the current status of backfill operation
    
    Returns information about whether a backfill is currently running,
    and the results of the last backfill operation.
    """
    return {
        "running": _backfill_status["running"],
        "message": _backfill_status["message"],
        "records": _backfill_status["records"]
    }

@router.post(
    "/clear",
    summary="Clear analytics data",
    description="Deletes all purchase events and stock snapshots (but keeps products and items)",
    response_description="Status of clear operation"
)
def clear_analytics_data(db: Session = Depends(get_db)):
    """
    Clear all analytics data (purchase events and stock snapshots)
    
    This removes all historical data generated by backfill operations,
    allowing you to start fresh with new data generation.
    
    NOTE: This keeps Products and InventoryItems intact, as they are needed
    for the simulation to function. Only historical analytics data is removed.
    
    WARNING: This is a destructive operation and cannot be undone.
    """
    try:
        from ..models import PurchaseEvent, StockSnapshot
        
        # Count records before deletion
        purchase_count = db.query(PurchaseEvent).count()
        snapshot_count = db.query(StockSnapshot).count()
        
        # Delete all records
        db.query(StockSnapshot).delete()
        db.query(PurchaseEvent).delete()
        db.commit()
        
        logger.info(f"Cleared {purchase_count} purchase events and {snapshot_count} stock snapshots")
        
        # Count remaining products and items
        from ..models import Product, InventoryItem
        products_remaining = db.query(Product).count()
        items_remaining = db.query(InventoryItem).count()
        
        return {
            "status": "success",
            "message": f"Cleared {purchase_count} purchase events and {snapshot_count} stock snapshots. {products_remaining} products and {items_remaining} items remain.",
            "purchases_deleted": purchase_count,
            "snapshots_deleted": snapshot_count,
            "products_remaining": products_remaining,
            "items_remaining": items_remaining
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error clearing analytics data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
