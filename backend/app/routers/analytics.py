"""Analytics and heatmap router"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..services import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/stock-heatmap")
def get_stock_heatmap(db: Session = Depends(get_db)):
    """
    Get stock depletion heatmap based on location clusters
    Returns per-product location data with depletion percentage based on historical maximum
    0% depletion = all items present (green), 100% = all items missing (red)
    """
    return AnalyticsService.get_stock_heatmap(db)


@router.get("/purchase-heatmap")
def get_purchase_heatmap(hours: int = 24, db: Session = Depends(get_db)):
    """
    Get purchase density heatmap by zone
    Returns purchase count per zone for the last N hours
    """
    return AnalyticsService.get_purchase_heatmap(db, hours)
