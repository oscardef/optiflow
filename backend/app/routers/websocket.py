"""WebSocket router for real-time updates"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, case
from typing import List, Set
import asyncio
import json
from datetime import datetime

from ..database import get_db, SessionLocal_simulation, SessionLocal_real
from ..models import TagPosition, Detection, InventoryItem, Product, Zone
from ..config import config_state, ConfigMode
from ..core import logger

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return
        
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                disconnected.add(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            self.active_connections.discard(conn)


# Global connection manager
manager = ConnectionManager()


def get_session():
    """Get appropriate database session based on config mode"""
    if config_state.mode == ConfigMode.SIMULATION:
        return SessionLocal_simulation()
    return SessionLocal_real()


@router.websocket("/ws/positions")
async def websocket_positions(websocket: WebSocket):
    """
    WebSocket endpoint for real-time position updates.
    
    Sends position data every 500ms (matching the UWB update rate).
    Message format:
    {
        "type": "position_update",
        "timestamp": "ISO timestamp",
        "positions": [
            {
                "tag_id": "...",
                "x": float,
                "y": float,
                "confidence": float
            }
        ]
    }
    """
    await manager.connect(websocket)
    last_position_id = 0
    
    try:
        while True:
            # Get database session
            db = get_session()
            try:
                # Get latest positions since last check
                positions = db.query(TagPosition)\
                    .filter(TagPosition.id > last_position_id)\
                    .order_by(TagPosition.timestamp.desc())\
                    .limit(10)\
                    .all()
                
                if positions:
                    last_position_id = max(p.id for p in positions)
                    
                    await websocket.send_json({
                        "type": "position_update",
                        "timestamp": datetime.utcnow().isoformat(),
                        "positions": [
                            {
                                "id": p.id,
                                "tag_id": p.tag_id,
                                "x": p.x_position,
                                "y": p.y_position,
                                "confidence": p.confidence,
                                "num_anchors": p.num_anchors,
                                "timestamp": p.timestamp.isoformat()
                            }
                            for p in positions
                        ]
                    })
            finally:
                db.close()
            
            # Wait before next update (500ms to match UWB update rate)
            await asyncio.sleep(0.5)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@router.websocket("/ws/items")
async def websocket_items(websocket: WebSocket):
    """
    WebSocket endpoint for real-time item status updates.
    
    Sends item updates when changes are detected.
    Message format:
    {
        "type": "item_update",
        "timestamp": "ISO timestamp",
        "items": [
            {
                "rfid_tag": "...",
                "name": "...",
                "x": float,
                "y": float,
                "status": "present" | "not present"
            }
        ],
        "stats": {
            "total": int,
            "present": int,
            "missing": int
        }
    }
    """
    await manager.connect(websocket)
    last_check_time = datetime.utcnow()
    sent_item_ids: set = set()  # Track items we've already sent
    
    try:
        while True:
            db = get_session()
            try:
                # Get items updated since last check with product info
                # Filter out items we've already sent if they have null last_seen_at
                query = db.query(InventoryItem, Product)\
                    .join(Product, InventoryItem.product_id == Product.id)\
                    .filter(InventoryItem.last_seen_at > last_check_time)
                
                updated_items = query.all()
                
                # Filter to only include items that are new or have changed
                items_to_send = [
                    (item, product) for item, product in updated_items
                    if item.id not in sent_item_ids or item.last_seen_at is not None
                ]
                
                if items_to_send:
                    items_data = [
                        {
                            "rfid_tag": item.rfid_tag,
                            "name": product.name if product else "Unknown",
                            "x": item.x_position,
                            "y": item.y_position,
                            "status": item.status,
                            "last_seen": item.last_seen_at.isoformat() if item.last_seen_at else None
                        }
                        for item, product in items_to_send
                    ]
                    
                    # Get overall stats using a single query with aggregation
                    stats_result = db.query(
                        func.count(InventoryItem.id).label('total'),
                        func.sum(case((InventoryItem.status == 'present', 1), else_=0)).label('present'),
                        func.sum(case((InventoryItem.status == 'not present', 1), else_=0)).label('missing')
                    ).first()
                    
                    await websocket.send_json({
                        "type": "item_update",
                        "timestamp": datetime.utcnow().isoformat(),
                        "items": items_data,
                        "stats": {
                            "total": stats_result.total or 0,
                            "present": stats_result.present or 0,
                            "missing": stats_result.missing or 0
                        }
                    })
                    
                    # Track sent items and update check time
                    sent_item_ids.update(item.id for item, _ in items_to_send)
                    last_check_time = datetime.utcnow()
            finally:
                db.close()
            
            # Wait before next check (1 second for items)
            await asyncio.sleep(1.0)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@router.websocket("/ws/combined")
async def websocket_combined(websocket: WebSocket):
    """
    WebSocket endpoint for combined real-time updates (positions + items).
    
    More efficient for clients that need both types of data.
    """
    await manager.connect(websocket)
    last_position_id = 0
    last_item_check = datetime.utcnow()
    sent_item_ids: set = set()  # Track items we've already sent
    
    try:
        while True:
            db = get_session()
            try:
                messages = []
                
                # Check for new positions
                positions = db.query(TagPosition)\
                    .filter(TagPosition.id > last_position_id)\
                    .order_by(TagPosition.timestamp.desc())\
                    .limit(10)\
                    .all()
                
                if positions:
                    last_position_id = max(p.id for p in positions)
                    messages.append({
                        "type": "position_update",
                        "positions": [
                            {
                                "id": p.id,
                                "tag_id": p.tag_id,
                                "x": p.x_position,
                                "y": p.y_position,
                                "confidence": p.confidence,
                                "num_anchors": p.num_anchors,
                                "timestamp": p.timestamp.isoformat()
                            }
                            for p in positions
                        ]
                    })
                
                # Check for item updates with product info
                updated_items = db.query(InventoryItem, Product)\
                    .join(Product, InventoryItem.product_id == Product.id)\
                    .filter(InventoryItem.last_seen_at > last_item_check)\
                    .all()
                
                # Filter to only include items that are new or have changed
                items_to_send = [
                    (item, product) for item, product in updated_items
                    if item.id not in sent_item_ids or item.last_seen_at is not None
                ]
                
                if items_to_send:
                    items_data = [
                        {
                            "rfid_tag": item.rfid_tag,
                            "name": product.name if product else "Unknown",
                            "x": item.x_position,
                            "y": item.y_position,
                            "status": item.status,
                            "last_seen": item.last_seen_at.isoformat() if item.last_seen_at else None
                        }
                        for item, product in items_to_send
                    ]
                    
                    # Get overall stats using a single query with aggregation
                    stats_result = db.query(
                        func.count(InventoryItem.id).label('total'),
                        func.sum(case((InventoryItem.status == 'present', 1), else_=0)).label('present'),
                        func.sum(case((InventoryItem.status == 'not present', 1), else_=0)).label('missing')
                    ).first()
                    
                    messages.append({
                        "type": "item_update",
                        "items": items_data,
                        "stats": {
                            "total": stats_result.total or 0,
                            "present": stats_result.present or 0,
                            "missing": stats_result.missing or 0
                        }
                    })
                    
                    # Track sent items and update check time
                    sent_item_ids.update(item.id for item, _ in items_to_send)
                    last_item_check = datetime.utcnow()
                
                # Send combined update if we have any messages
                if messages:
                    await websocket.send_json({
                        "type": "combined_update",
                        "timestamp": datetime.utcnow().isoformat(),
                        "updates": messages
                    })
            finally:
                db.close()
            
            # Wait 500ms between updates
            await asyncio.sleep(0.5)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# Function to broadcast updates from other parts of the application
async def broadcast_position_update(position_data: dict):
    """Broadcast position update to all connected clients"""
    await manager.broadcast({
        "type": "position_update",
        "timestamp": datetime.utcnow().isoformat(),
        "positions": [position_data]
    })


async def broadcast_item_update(item_data: dict, stats: dict):
    """Broadcast item update to all connected clients"""
    await manager.broadcast({
        "type": "item_update",
        "timestamp": datetime.utcnow().isoformat(),
        "items": [item_data],
        "stats": stats
    })
