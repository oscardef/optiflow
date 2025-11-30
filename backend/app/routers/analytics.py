"""Analytics and heatmap router"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from collections import defaultdict
from statistics import mean

from ..database import get_db
from ..models import (
    Zone, InventoryItem, ProductLocationHistory, Product,
    PurchaseEvent
)
from ..core import logger

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/stock-heatmap")
def get_stock_heatmap(db: Session = Depends(get_db)):
    """
    Get stock depletion heatmap based on location clusters
    Returns per-product location data with depletion percentage based on historical maximum
    0% depletion = all items present (green), 100% = all items missing (red)
    """
    zones = db.query(Zone).all()
    
    def get_zone_from_position(x, y):
        for zone in zones:
            if (zone.x_min <= x <= zone.x_max and 
                zone.y_min <= y <= zone.y_max):
                return zone.id
        return None
    
    items = db.query(InventoryItem).all()
    
    product_stats = defaultdict(lambda: {
        'x_positions': [],
        'y_positions': [],
        'present_count': 0,
        'total_count': 0,
        'zone_id': None
    })
    
    for item in items:
        zone_id = item.zone_id if item.zone_id else get_zone_from_position(item.x_position, item.y_position)
        
        if zone_id:
            key = (item.product_id, zone_id)
            product_stats[key]['x_positions'].append(item.x_position)
            product_stats[key]['y_positions'].append(item.y_position)
            product_stats[key]['total_count'] += 1
            if item.status == "present":
                product_stats[key]['present_count'] += 1
            product_stats[key]['zone_id'] = zone_id
    
    current_stats = []
    for (product_id, zone_id), stats in product_stats.items():
        if stats['total_count'] > 0:
            current_stats.append({
                'product_id': product_id,
                'zone_id': zone_id,
                'x_center': mean(stats['x_positions']),
                'y_center': mean(stats['y_positions']),
                'present_count': stats['present_count'],
                'total_count': stats['total_count']
            })
    
    for stat in current_stats:
        location_history = db.query(ProductLocationHistory).filter(
            ProductLocationHistory.product_id == stat['product_id'],
            ProductLocationHistory.zone_id == stat['zone_id']
        ).first()
        
        if location_history:
            location_history.current_count = stat['present_count']
            location_history.x_center = stat['x_center']
            location_history.y_center = stat['y_center']
            if stat['total_count'] > location_history.max_items_seen:
                location_history.max_items_seen = stat['total_count']
            location_history.last_updated = datetime.utcnow()
        else:
            location_history = ProductLocationHistory(
                product_id=stat['product_id'],
                zone_id=stat['zone_id'],
                x_center=stat['x_center'],
                y_center=stat['y_center'],
                current_count=stat['present_count'],
                max_items_seen=stat['total_count'],
                last_updated=datetime.utcnow()
            )
            db.add(location_history)
    
    db.commit()
    
    heatmap_data = db.query(
        ProductLocationHistory,
        Product,
        Zone
    ).join(
        Product, ProductLocationHistory.product_id == Product.id
    ).join(
        Zone, ProductLocationHistory.zone_id == Zone.id
    ).filter(
        ProductLocationHistory.max_items_seen > 0
    ).all()
    
    logger.info(f"Generated heatmap with {len(heatmap_data)} location clusters")
    
    return [
        {
            "product_id": location.product_id,
            "product_name": product.name,
            "product_category": product.category,
            "zone_id": location.zone_id,
            "zone_name": zone.name,
            "x": location.x_center,
            "y": location.y_center,
            "current_count": location.current_count,
            "max_items_seen": location.max_items_seen,
            "items_missing": location.max_items_seen - location.current_count,
            "depletion_percentage": round(
                ((location.max_items_seen - location.current_count) / location.max_items_seen * 100), 
                1
            ) if location.max_items_seen > 0 else 0
        }
        for location, product, zone in heatmap_data
    ]

@router.get("/purchase-heatmap")
def get_purchase_heatmap(hours: int = 24, db: Session = Depends(get_db)):
    """
    Get purchase density heatmap by zone
    Returns purchase count per zone for the last N hours
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    results = db.query(
        Zone,
        func.count(PurchaseEvent.id).label("purchase_count")
    ).outerjoin(
        PurchaseEvent,
        (PurchaseEvent.zone_id == Zone.id) & (PurchaseEvent.purchased_at >= cutoff_time)
    ).group_by(Zone.id).all()
    
    return [
        {
            "zone": zone.to_dict(),
            "purchase_count": count
        }
        for zone, count in results
    ]

@router.get("/overview")
def get_analytics_overview(db: Session = Depends(get_db)):
    """
    Get high-level analytics overview with key metrics
    """
    from ..models import StockLevel, InventoryItem
    
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
    
    # Sales statistics
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
    
    return {
        'total_products': total_products,
        'total_stock_value': round(total_stock_value, 2),
        'items_needing_restock': items_needing_restock,
        'sales_today': sales_today,
        'sales_last_7_days': sales_7_days,
        'sales_last_30_days': sales_30_days,
        'low_stock_products': low_stock_products,
        'timestamp': datetime.utcnow().isoformat()
    }

@router.get("/product-velocity")
def get_product_velocity(days: int = 7, db: Session = Depends(get_db)):
    """
    Calculate product velocity (turnover rate) for all products
    """
    from ..models import StockLevel
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
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
        velocity_daily = sales / days if days > 0 else 0
        
        # Calculate turnover rate and days until stockout
        turnover_rate = (sales / max(1, current_stock)) if current_stock > 0 else 0
        days_until_stockout = (current_stock / velocity_daily) if velocity_daily > 0 else None
        
        velocity_data.append({
            'product_id': product.id,
            'sku': product.sku,
            'name': product.name,
            'category': product.category,
            'current_stock': current_stock,
            'sales_7_days': sales if days == 7 else None,
            'sales_30_days': sales if days == 30 else None,
            'velocity_daily': round(velocity_daily, 2),
            'turnover_rate': round(turnover_rate, 2),
            'days_until_stockout': round(days_until_stockout, 1) if days_until_stockout else None
        })
    
    return sorted(velocity_data, key=lambda x: x['velocity_daily'], reverse=True)

@router.get("/top-products")
def get_top_products(metric: str = 'sales', days: int = 30, limit: int = 20, db: Session = Depends(get_db)):
    """
    Get top performing products by various metrics
    metric options: 'sales', 'revenue', 'velocity'
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
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
def get_category_performance(days: int = 30, db: Session = Depends(get_db)):
    """
    Aggregate performance metrics by product category
    """
    from ..models import StockLevel
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
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

@router.get("/stock-trends/{product_id}")
def get_stock_trends(product_id: int, days: int = 7, db: Session = Depends(get_db)):
    """
    Get historical stock level trends for a specific product
    """
    from ..models import StockSnapshot
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    snapshots = db.query(StockSnapshot).filter(
        StockSnapshot.product_id == product_id,
        StockSnapshot.timestamp >= cutoff_date
    ).order_by(StockSnapshot.timestamp).all()
    
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        return {'error': 'Product not found'}
    
    return {
        'product_id': product_id,
        'sku': product.sku,
        'name': product.name,
        'data_points': [
            {
                'timestamp': s.timestamp.isoformat(),
                'present_count': s.present_count,
                'missing_count': s.missing_count
            }
            for s in snapshots
        ]
    }

@router.get("/ai/clusters")
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

@router.get("/ai/forecast/{product_id}")
def get_demand_forecast(product_id: int, days_ahead: int = 7, db: Session = Depends(get_db)):
    """
    Get AI-powered demand forecast for a specific product
    Uses exponential smoothing for prediction
    """
    from ..services.ai_analytics import AIAnalyticsService
    
    ai_service = AIAnalyticsService(db)
    forecast = ai_service.forecast_demand(product_id, days_ahead)
    
    return forecast

@router.get("/ai/anomalies")
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

@router.get("/ai/abc-analysis")
def get_abc_analysis(db: Session = Depends(get_db)):
    """
    ABC classification of products based on revenue contribution
    A = top revenue generators, B = medium, C = low
    """
    from ..services.ai_analytics import AIAnalyticsService
    
    ai_service = AIAnalyticsService(db)
    classification = ai_service.abc_analysis()
    
    return {
        'A': {'classification': 'A', 'products': classification['A']},
        'B': {'classification': 'B', 'products': classification['B']},
        'C': {'classification': 'C', 'products': classification['C']},
        'timestamp': datetime.utcnow().isoformat()
    }

@router.get("/ai/product-affinity")
def get_product_affinity(min_support: float = 0.05, db: Session = Depends(get_db)):
    """
    Find products frequently purchased together
    Useful for cross-selling recommendations
    """
    from ..services.ai_analytics import AIAnalyticsService
    
    ai_service = AIAnalyticsService(db)
    affinities = ai_service.product_affinity(min_support)
    
    return {
        'affinities': affinities,
        'count': len(affinities),
        'timestamp': datetime.utcnow().isoformat()
    }

@router.get("/slow-movers")
def get_slow_movers(velocity_threshold: float = 0.1, days: int = 30, db: Session = Depends(get_db)):
    """
    Identify slow-moving inventory (low velocity products)
    """
    from ..models import StockLevel
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    products = db.query(Product).all()
    
    slow_movers = []
    for product in products:
        sales = db.query(PurchaseEvent).filter(
            PurchaseEvent.product_id == product.id,
            PurchaseEvent.purchased_at >= cutoff_date
        ).count()
        
        velocity = sales / days
        
        if velocity < velocity_threshold:
            stock = db.query(StockLevel).filter(
                StockLevel.product_id == product.id
            ).first()
            
            slow_movers.append({
                'product_id': product.id,
                'sku': product.sku,
                'name': product.name,
                'category': product.category,
                'current_stock': stock.current_count if stock else 0,
                'sales_last_30_days': sales,
                'velocity_daily': round(velocity, 3),
                'recommendation': 'Consider discount or promotion' if stock and stock.current_count > 10 else 'Monitor'
            })
    
    return sorted(slow_movers, key=lambda x: x['current_stock'], reverse=True)

@router.post("/bulk/purchases")
def bulk_insert_purchases(purchases: list[dict], db: Session = Depends(get_db)):
    """
    Bulk insert historical purchase events for analytics backfill
    Expected format: [{"product_id": int, "purchased_at": str, "zone_id": int (optional)}, ...]
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
                status='not_present',  # Historical purchases are gone
                zone_id=purchase_data.get('zone_id')
            )
            db.add(dummy_item)
            db.flush()  # Get the ID
            
            # Create purchase event
            purchase = PurchaseEvent(
                inventory_item_id=dummy_item.id,
                product_id=purchase_data['product_id'],
                x_position=purchase_data.get('x_position'),
                y_position=purchase_data.get('y_position'),
                zone_id=purchase_data.get('zone_id'),
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

@router.post("/bulk/snapshots")
def bulk_insert_snapshots(snapshots: list[dict], db: Session = Depends(get_db)):
    """
    Bulk insert historical stock snapshots for analytics backfill
    Expected format: [{"product_id": int, "timestamp": str, "present_count": int, "missing_count": int, "zone_id": int}, ...]
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
                    missing_count=snapshot_data.get('missing_count', 0),
                    zone_id=snapshot_data.get('zone_id')
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
