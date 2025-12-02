"""Product management router"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import random
import uuid

from ..database import get_db
from ..models import Product, StockLevel
from ..schemas import ProductCreate
from ..core import logger

router = APIRouter(prefix="/products", tags=["products"])

@router.get("")
def get_products(db: Session = Depends(get_db)):
    """Get all products in catalog"""
    products = db.query(Product).all()
    return [p.to_dict() for p in products]

@router.get("/with-stock")
def get_products_with_stock(db: Session = Depends(get_db)):
    """Get all products with their current stock counts from InventoryItem"""
    from ..models import InventoryItem
    from sqlalchemy import func
    
    # Count items by product, grouped by status
    stock_counts = db.query(
        Product.id,
        Product.name,
        func.count(InventoryItem.id).filter(InventoryItem.status == 'present').label('current_stock'),
        func.count(InventoryItem.id).label('max_detected')
    ).outerjoin(
        InventoryItem, Product.id == InventoryItem.product_id
    ).group_by(Product.id, Product.name).all()
    
    # Create a dict for quick lookup
    stock_dict = {row.id: {'current_stock': row.current_stock, 'max_detected': row.max_detected} for row in stock_counts}
    
    # Get all products and add stock info
    products = db.query(Product).all()
    return [
        {
            **p.to_dict(),
            'current_stock': stock_dict.get(p.id, {}).get('current_stock', 0),
            'max_detected': stock_dict.get(p.id, {}).get('max_detected', 0)
        }
        for p in products
    ]

@router.post("/populate-stock")
def populate_stock_for_all_products(db: Session = Depends(get_db)):
    """
    Add inventory items to all products to match their optimal_stock_level.
    Creates new items with unique RFID tags and random shelf positions.
    """
    from ..models import InventoryItem
    from sqlalchemy import func
    
    # Get current stock counts per product
    stock_counts = db.query(
        Product.id,
        func.count(InventoryItem.id).label('current_count')
    ).outerjoin(
        InventoryItem, Product.id == InventoryItem.product_id
    ).group_by(Product.id).all()
    
    stock_dict = {row.id: row.current_count for row in stock_counts}
    
    # Get all products
    products = db.query(Product).all()
    
    # Store aisle positions for realistic placement
    aisles = [
        {'x': 200, 'y_min': 150, 'y_max': 700},
        {'x': 400, 'y_min': 120, 'y_max': 700},
        {'x': 600, 'y_min': 120, 'y_max': 700},
        {'x': 800, 'y_min': 120, 'y_max': 700},
    ]
    
    items_created = 0
    products_updated = 0
    
    for product in products:
        current_count = stock_dict.get(product.id, 0)
        target_count = product.optimal_stock_level or 5
        
        if current_count < target_count:
            items_needed = target_count - current_count
            products_updated += 1
            
            for i in range(items_needed):
                # Generate unique RFID tag
                rfid_tag = f"RFID{str(uuid.uuid4().hex)[:8].upper()}"
                
                # Random aisle position along shelves (not in walkways)
                aisle = random.choice(aisles)
                # Position on shelf edge (left or right of aisle center)
                shelf_offset = random.choice([-35, 35])  # Shelf width offset
                x = aisle['x'] + shelf_offset + random.uniform(-5, 5)
                y = random.uniform(aisle['y_min'] + 20, aisle['y_max'] - 20)
                
                new_item = InventoryItem(
                    rfid_tag=rfid_tag,
                    product_id=product.id,
                    status='present',
                    x_position=round(x, 2),
                    y_position=round(y, 2)
                )
                db.add(new_item)
                items_created += 1
    
    db.commit()
    
    logger.info(f"Populated stock: {items_created} items created for {products_updated} products")
    
    return {
        "success": True,
        "items_created": items_created,
        "products_updated": products_updated,
        "message": f"Created {items_created} inventory items for {products_updated} products"
    }

@router.post("", status_code=201)
def create_product(product_data: ProductCreate, db: Session = Depends(get_db)):
    """Create a new product in the catalog"""
    existing = db.query(Product).filter(Product.sku == product_data.sku).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Product with SKU {product_data.sku} already exists")
    
    product = Product(
        sku=product_data.sku,
        name=product_data.name,
        category=product_data.category,
        unit_price=product_data.unit_price,
        reorder_threshold=product_data.reorder_threshold,
        optimal_stock_level=product_data.optimal_stock_level
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    
    logger.info(f"Created product {product.id}: {product.name} (SKU: {product.sku})")
    
    return product.to_dict()

@router.put("/{product_id}")
def update_product(product_id: int, product_data: ProductCreate, db: Session = Depends(get_db)):
    """Update a product in the catalog"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if SKU is being changed to an existing one
    if product_data.sku != product.sku:
        existing = db.query(Product).filter(Product.sku == product_data.sku).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Product with SKU {product_data.sku} already exists")
    
    product.sku = product_data.sku
    product.name = product_data.name
    product.category = product_data.category
    product.unit_price = product_data.unit_price
    product.reorder_threshold = product_data.reorder_threshold
    product.optimal_stock_level = product_data.optimal_stock_level
    
    db.commit()
    db.refresh(product)
    
    logger.info(f"Updated product {product.id}: {product.name} (SKU: {product.sku})")
    
    return product.to_dict()

@router.post("/{product_id}/adjust-stock")
def adjust_product_stock(product_id: int, adjustment: dict, db: Session = Depends(get_db)):
    """Adjust product stock by adding or removing inventory items
    
    Body: {"current_stock": 10, "max_detected": 15}
    This will add/remove items to match current_stock and ensure max_detected is at least that value
    """
    from ..models import InventoryItem
    import random
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    target_current = adjustment.get('current_stock')
    target_max = adjustment.get('max_detected')
    
    # Get current counts
    current_present = db.query(InventoryItem).filter(
        InventoryItem.product_id == product_id,
        InventoryItem.status == 'present'
    ).count()
    
    total_items = db.query(InventoryItem).filter(
        InventoryItem.product_id == product_id
    ).count()
    
    if target_current is not None:
        diff = target_current - current_present
        
        if diff > 0:
            # Need to add items or change status to present
            # First try to reactivate not present items
            inactive_items = db.query(InventoryItem).filter(
                InventoryItem.product_id == product_id,
                InventoryItem.status != 'present'
            ).limit(diff).all()
            
            for item in inactive_items:
                item.status = 'present'
                item.last_seen_at = datetime.utcnow()
                diff -= 1
            
            # Create new items if still needed
            for i in range(diff):
                new_item = InventoryItem(
                    rfid_tag=f"RFID_{random.randint(10000, 99999)}",
                    product_id=product_id,
                    status='present',
                    x_position=random.uniform(100, 900),
                    y_position=random.uniform(100, 700)
                )
                db.add(new_item)
        
        elif diff < 0:
            # Need to remove items (mark as not present)
            items_to_remove = db.query(InventoryItem).filter(
                InventoryItem.product_id == product_id,
                InventoryItem.status == 'present'
            ).limit(abs(diff)).all()
            
            for item in items_to_remove:
                item.status = 'not present'
    
    if target_max is not None and target_max > total_items:
        # Add items to reach max_detected (as not present)
        diff = target_max - total_items
        for i in range(diff):
            new_item = InventoryItem(
                rfid_tag=f"RFID_{random.randint(10000, 99999)}",
                product_id=product_id,
                status='not present',
                x_position=random.uniform(100, 900),
                y_position=random.uniform(100, 700)
            )
            db.add(new_item)
    
    db.commit()
    
    logger.info(f"Adjusted stock for product {product_id}: current={target_current}, max={target_max}")
    
    return {"success": True, "message": "Stock adjusted successfully"}

@router.get("/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get a specific product by ID"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product.to_dict()

@router.get("/{product_id}/items")
def get_product_items(product_id: int, db: Session = Depends(get_db)):
    """Get all unique RFID-tagged items for a specific product"""
    from ..models import InventoryItem
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    items = db.query(InventoryItem).filter(
        InventoryItem.product_id == product_id
    ).order_by(InventoryItem.status.desc(), InventoryItem.rfid_tag).all()
    
    return [
        {
            "id": item.id,
            "rfid_tag": item.rfid_tag,
            "status": item.status,
            "x_position": item.x_position,
            "y_position": item.y_position,
            "zone_id": item.zone_id,
            "last_seen_at": item.last_seen_at.isoformat() if item.last_seen_at else None,
            "created_at": item.created_at.isoformat()
        }
        for item in items
    ]
