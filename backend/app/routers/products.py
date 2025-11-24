"""Product management router"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

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

@router.get("/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get a specific product by ID"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product.to_dict()

@router.get("/summary")
def get_products_summary(db: Session = Depends(get_db)):
    """Get all products with their current stock levels"""
    results = db.query(Product, StockLevel).outerjoin(
        StockLevel, Product.id == StockLevel.product_id
    ).all()
    
    return [
        {
            **product.to_dict(),
            "stock_level": stock_level.to_dict() if stock_level else {
                "current_count": 0,
                "missing_count": 0,
                "sold_today": 0,
                "priority_score": 0.0
            }
        }
        for product, stock_level in results
    ]
