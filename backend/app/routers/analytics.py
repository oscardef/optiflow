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
