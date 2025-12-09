"""
WebSocket Manager for Real-time Data Broadcasting
==================================================
Broadcasts position updates and detection events to connected clients.
"""
from typing import List, Set
from fastapi import WebSocket
import json
import asyncio
from .core import logger


class ConnectionManager:
    """Manages WebSocket connections and broadcasts"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            logger.debug("No active WebSocket connections to broadcast to")
            return
        
        message_json = json.dumps(message)
        disconnected = set()
        
        logger.info(f"📡 Broadcasting {message.get('type', 'unknown')} to {len(self.active_connections)} clients")
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
    
    async def broadcast_position_update(self, position_data: dict):
        """Broadcast employee position update"""
        await self.broadcast({
            "type": "position_update",
            "data": position_data
        })
    
    async def broadcast_detection_update(self, detections: List[dict]):
        """Broadcast RFID detection updates"""
        await self.broadcast({
            "type": "detection_update",
            "data": {
                "detections": detections,
                "count": len(detections)
            }
        })
    
    async def broadcast_item_update(self, items: List[dict]):
        """Broadcast inventory item updates (with positions)"""
        await self.broadcast({
            "type": "item_update",
            "data": {
                "items": items,
                "count": len(items)
            }
        })


# Global connection manager instance
manager = ConnectionManager()
