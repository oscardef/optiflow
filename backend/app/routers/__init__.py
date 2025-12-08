"""API Routers"""
from .anchors import router as anchors_router
from .positions import router as positions_router
from .data import router as data_router
from .products import router as products_router
from .analytics import router as analytics_router
# zones router removed - zones system deprecated
from .config import router as config_router
from .simulation import router as simulation_router
from .items import router as items_router
from .setup import router as setup_router

__all__ = [
    "anchors_router",
    "positions_router",
    "data_router",
    "products_router",
    "analytics_router",
    "zones_router",
    "config_router",
    "simulation_router",
    "items_router",
    "setup_router"
]
