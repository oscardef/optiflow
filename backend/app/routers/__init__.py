"""API Routers"""
from .anchors import router as anchors_router
from .positions import router as positions_router
from .data import router as data_router
from .products import router as products_router
from .analytics import router as analytics_router
from .zones import router as zones_router

__all__ = [
    "anchors_router",
    "positions_router",
    "data_router",
    "products_router",
    "analytics_router",
    "zones_router"
]
