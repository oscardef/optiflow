"""Setup and initialization endpoints for complete system setup"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict
import subprocess
import sys
from pathlib import Path

from ..database import get_db
from ..models import Product, StockLevel
from ..core import logger

router = APIRouter(prefix="/setup", tags=["setup"])

@router.post("/initialize-stock-levels")
def initialize_stock_levels(db: Session = Depends(get_db)):
    """
    Initialize stock_levels table from current inventory_items state.
    This should be run after products are created and before backfill.
    """
    try:
        # Check if products exist
        product_count = db.query(Product).count()
        if product_count == 0:
            raise HTTPException(
                status_code=400,
                detail="No products found. Please generate products first."
            )
        
        # Initialize stock levels from current inventory_items
        query = text("""
            INSERT INTO stock_levels (product_id, current_count, updated_at)
            SELECT 
                product_id,
                COUNT(*) FILTER (WHERE status = 'present') as current_count,
                NOW() as updated_at
            FROM inventory_items
            GROUP BY product_id
            ON CONFLICT (product_id) 
            DO UPDATE SET 
                current_count = EXCLUDED.current_count,
                updated_at = EXCLUDED.updated_at
        """)
        
        result = db.execute(query)
        db.commit()
        
        # Get count of initialized products
        stock_count = db.query(StockLevel).count()
        
        logger.info(f"Initialized stock levels for {stock_count} products")
        
        return {
            "status": "success",
            "message": f"Initialized stock levels for {stock_count} products",
            "products_total": product_count,
            "stock_levels_initialized": stock_count
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error initializing stock levels: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify-and-fix")
def verify_and_fix(db: Session = Depends(get_db)):
    """
    Verify system setup and fix common issues:
    1. Check if products exist (if not, suggest running generation)
    2. Check if stock_levels are initialized
    3. Initialize stock_levels if needed
    """
    try:
        # Check products
        product_count = db.query(Product).count()
        stock_level_count = db.query(StockLevel).count()
        
        issues = []
        fixes_applied = []
        
        # Issue 1: No products
        if product_count == 0:
            issues.append({
                "issue": "no_products",
                "message": "No products found in database",
                "fix": "Run 'docker compose exec backend bash -c \"cd /simulation && python generate_inventory.py --items 100\"' to generate products"
            })
        
        # Issue 2: Products exist but stock_levels not initialized
        if product_count > 0 and stock_level_count == 0:
            issues.append({
                "issue": "stock_levels_missing",
                "message": "Products exist but stock_levels table is empty",
                "fix": "Initializing stock_levels now..."
            })
            
            # Auto-fix: Initialize stock levels
            query = text("""
                INSERT INTO stock_levels (product_id, current_count, missing_count, updated_at)
                SELECT 
                    product_id,
                    COUNT(*) FILTER (WHERE status = 'present') as current_count,
                    COUNT(*) FILTER (WHERE status = 'missing') as missing_count,
                    NOW() as updated_at
                FROM inventory_items
                GROUP BY product_id
                ON CONFLICT (product_id) 
                DO UPDATE SET 
                    current_count = EXCLUDED.current_count,
                    missing_count = EXCLUDED.missing_count,
                    updated_at = EXCLUDED.updated_at
            """)
            
            db.execute(query)
            db.commit()
            stock_level_count = db.query(StockLevel).count()
            
            fixes_applied.append({
                "fix": "stock_levels_initialized",
                "message": f"Initialized stock_levels for {stock_level_count} products"
            })
        
        # Issue 3: Stock levels exist but are stale (last_updated > 1 day ago)
        # This is just informational, not auto-fixed
        
        return {
            "status": "checked",
            "products_count": product_count,
            "stock_levels_count": stock_level_count,
            "issues": issues,
            "fixes_applied": fixes_applied,
            "ready": product_count > 0 and stock_level_count > 0
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error verifying setup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
def get_setup_status(db: Session = Depends(get_db)):
    """
    Get current setup status without making any changes
    """
    try:
        from ..models import InventoryItem, PurchaseEvent, StockSnapshot
        
        product_count = db.query(Product).count()
        stock_level_count = db.query(StockLevel).count()
        inventory_item_count = db.query(InventoryItem).count()
        purchase_event_count = db.query(PurchaseEvent).count()
        stock_snapshot_count = db.query(StockSnapshot).count()
        
        return {
            "products": product_count,
            "stock_levels": stock_level_count,
            "inventory_items": inventory_item_count,
            "purchase_events": purchase_event_count,
            "stock_snapshots": stock_snapshot_count,
            "setup_complete": product_count > 0 and stock_level_count > 0,
            "has_analytics_data": purchase_event_count > 0 and stock_snapshot_count > 0
        }
        
    except Exception as e:
        logger.error(f"Error getting setup status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
