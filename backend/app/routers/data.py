"""Data ingestion and retrieval router"""
import math
import json
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List

from ..database import get_db
from ..models import (
    Detection, UWBMeasurement, TagPosition, Anchor,
    InventoryItem, Product, PurchaseEvent, ProductLocationHistory, StockLevel
)
from ..schemas import (
    DataPacket, DetectionResponse, UWBMeasurementResponse, LatestDataResponse,
    HardwarePacket
)
from ..triangulation import TriangulationService
from ..config import config_state, ConfigMode
from ..core import logger
from ..websocket_manager import manager as ws_manager

router = APIRouter(tags=["data"])

@router.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time data streaming.
    Clients connect here to receive live position and detection updates.
    """
    logger.info(f"WebSocket connection attempt from {websocket.client}")
    await ws_manager.connect(websocket)
    logger.info(f"WebSocket connected successfully from {websocket.client}")
    try:
        # Keep connection alive and handle incoming messages if needed
        while True:
            # Wait for any client messages (ping/pong, etc.)
            data = await websocket.receive_text()
            logger.debug(f"WebSocket received: {data}")
            # Echo back for keep-alive
            await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected from {websocket.client}")
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)

@router.post("/data", status_code=201)
async def receive_data(packet: HardwarePacket, db: Session = Depends(get_db)):
    """
    Receive hardware format data (RFID + UWB) from ESP32 devices or simulation.
    Automatically calculates position if 2+ anchors available.
    Broadcasts updates to WebSocket clients in real-time.
    
    Hardware format:
    {
        "polling_cycle": 1,
        "timestamp": 123456,  # milliseconds since boot
        "uwb": {"n_anchors": 2, "anchors": [...]},
        "rfid": {"tag_count": 2, "tags": [...]}
    }
    """
    try:
        # Log incoming data
        logger.info(f"Received hardware packet: cycle={packet.polling_cycle}, RFID={packet.rfid.tag_count}, UWB={packet.uwb.n_anchors or 0} (Mode: {config_state.mode.value})")
        
        timestamp = datetime.utcnow()
        rfid_tags_processed = 0
        uwb_measurements_processed = 0
        position_calculated = False
        calculated_position = None
        
        # Store RFID detections
        for tag in packet.rfid.tags:
            # All detected tags are implicitly "present"
            det = Detection(
                timestamp=timestamp,
                product_id=tag.epc,
                product_name=f"Item-{tag.epc[-8:]}" if tag.epc else "Unknown",
                x_position=None,
                y_position=None,
                status="present"
            )
            db.add(det)
            db.flush()
            rfid_tags_processed += 1
            
            # Sync to inventory_items table
            inventory_item = db.query(InventoryItem).filter(
                InventoryItem.rfid_tag == tag.epc
            ).first()
            
            if not inventory_item:
                # Create new inventory item (find or create product first)
                product = db.query(Product).filter(Product.name == det.product_name).first()
                if not product:
                    # Create a generic product for this item
                    product = Product(
                        sku=f"GEN-{tag.epc}",
                        name=det.product_name,
                        category="General",
                        unit_price=29.99,
                        reorder_threshold=10,
                        optimal_stock_level=50
                    )
                    db.add(product)
                    db.flush()
                
                # Create inventory item
                inventory_item = InventoryItem(
                    rfid_tag=tag.epc,
                    product_id=product.id,
                    status="present",
                    x_position=None,  # Will be set by triangulation
                    y_position=None,
                    last_seen_at=timestamp
                )
                db.add(inventory_item)
            else:
                # Update existing inventory item
                inventory_item.status = "present"
                inventory_item.last_seen_at = timestamp
        
        # Store UWB measurements
        if packet.uwb.available is not False and packet.uwb.anchors:
            for anchor in packet.uwb.anchors:
                if anchor.average_distance_cm is not None and anchor.measurements > 0:
                    measurement = UWBMeasurement(
                        timestamp=timestamp,
                        mac_address=anchor.mac_address,
                        distance_cm=anchor.average_distance_cm,
                        status="0x01"  # OK status
                    )
                    db.add(measurement)
                    db.flush()
                    uwb_measurements_processed += 1
        
        db.commit()
        
        # Try to calculate position if we have enough data
        try:
            anchors_config = db.query(Anchor).filter(Anchor.is_active == True).all()
            logger.info(f"Position calculation: {len(anchors_config)} anchors configured, {uwb_measurements_processed} UWB measurements received")
            
            if len(anchors_config) >= 2 and packet.uwb.anchors and len(packet.uwb.anchors) >= 2:
                measurements = []
                configured_macs = {a.mac_address for a in anchors_config}
                received_macs = {anchor.mac_address for anchor in packet.uwb.anchors}
                logger.info(f"Configured anchor MACs: {configured_macs}")
                logger.info(f"Received UWB MACs: {received_macs}")
                
                for uwb_anchor in packet.uwb.anchors:
                    if uwb_anchor.average_distance_cm is None or uwb_anchor.measurements == 0:
                        continue
                    anchor_config = next((a for a in anchors_config if a.mac_address == uwb_anchor.mac_address), None)
                    if anchor_config:
                        measurements.append((
                            anchor_config.x_position,
                            anchor_config.y_position,
                            uwb_anchor.average_distance_cm
                        ))
                        logger.info(f"Matched anchor {uwb_anchor.mac_address} at ({anchor_config.x_position}, {anchor_config.y_position})")
                    else:
                        logger.warning(f"No anchor configured for MAC: {uwb_anchor.mac_address}")
                
                if len(measurements) >= 2:
                    result = TriangulationService.calculate_position(measurements)
                    if result:
                        x, y, confidence = result
                        calculated_position = {"x": x, "y": y, "confidence": confidence}
                        
                        # Store the employee/tag position
                        position = TagPosition(
                            timestamp=timestamp,
                            tag_id="employee",
                            x_position=x,
                            y_position=y,
                            confidence=confidence,
                            num_anchors=len(measurements)
                        )
                        db.add(position)
                        position_calculated = True
                        logger.info(f"✅ Employee position calculated: ({x:.1f}, {y:.1f}) confidence={confidence:.2f}")
                        
                        # Update detected items' positions based on mode
                        for tag in packet.rfid.tags:
                            inventory_item = db.query(InventoryItem).filter(
                                InventoryItem.rfid_tag == tag.epc
                            ).first()
                            
                            if inventory_item:
                                # SIMULATION MODE: Items already have shelf positions in database
                                # Just mark them as detected, don't override their positions
                                
                                # PRODUCTION MODE: Set position to where employee detected it
                                if config_state.mode == ConfigMode.PRODUCTION:
                                    inventory_item.x_position = x
                                    inventory_item.y_position = y
                                    logger.info(f"   [PRODUCTION] Updated item {tag.epc} to employee position ({x:.1f}, {y:.1f})")
                                elif inventory_item.x_position is None:
                                    # SIMULATION: Only set position if item has none
                                    inventory_item.x_position = x
                                    inventory_item.y_position = y
                                    logger.warning(f"   [SIMULATION] Item {tag.epc} had no position, set to ({x:.1f}, {y:.1f})")
                        
                        db.commit()
                        
                        # === SMART MISSING ITEM INFERENCE ===
                        # Infer items that should have been detected but weren't
                        newly_missing_items = []
                        
                        # Safety parameters
                        RFID_DETECTION_RANGE_CM = 60.0  # Match simulation config
                        CLOSE_RANGE_CM = 50.0  # Only infer for items clearly in range
                        MIN_CONSECUTIVE_MISSES = 3  # Minimum misses before considering
                        MAX_CONSECUTIVE_MISSES = 5  # Maximum misses (randomized per item)
                        INFERENCE_PROBABILITY = 0.15  # Only 15% chance to infer even after threshold
                        MAX_INFERENCES_PER_PASS = 2  # Max items to mark missing per scan
                        
                        import random
                        
                        # Get the set of RFID tags that were detected
                        detected_tags = {tag.epc for tag in packet.rfid.tags}
                        
                        # Use inference for items that weren't detected
                        # Find items that are currently present and have known positions
                        present_items_in_range = db.query(InventoryItem).filter(
                            InventoryItem.status == 'present',
                            InventoryItem.x_position.isnot(None),
                            InventoryItem.y_position.isnot(None)
                        ).all()
                        
                        # Track detection misses and per-item thresholds (use module-level cache)
                        if not hasattr(receive_data, '_detection_misses'):
                            receive_data._detection_misses = {}  # {rfid_tag: miss_count}
                        if not hasattr(receive_data, '_item_thresholds'):
                            receive_data._item_thresholds = {}  # {rfid_tag: required_misses}
                        
                        inference_candidates = []  # Collect candidates instead of immediately marking
                        
                        for item in present_items_in_range:
                            # Skip if this item was detected
                            if item.rfid_tag in detected_tags:
                                # Reset miss counter when detected
                                receive_data._detection_misses[item.rfid_tag] = 0
                                continue
                            
                            # Calculate distance from scanner to item's known position
                            dx = item.x_position - x
                            dy = item.y_position - y
                            distance = math.sqrt(dx * dx + dy * dy)
                            
                            # SAFETY CHECK 1: Only infer for items CLEARLY in close range
                            # This prevents false positives from items at edge of detection range
                            if distance <= CLOSE_RANGE_CM:
                                # SAFETY CHECK 2: Require multiple consecutive misses
                                current_misses = receive_data._detection_misses.get(item.rfid_tag, 0)
                                receive_data._detection_misses[item.rfid_tag] = current_misses + 1
                                
                                # SAFETY CHECK 3: Each item has randomized threshold (3-5 misses)
                                if item.rfid_tag not in receive_data._item_thresholds:
                                    receive_data._item_thresholds[item.rfid_tag] = random.randint(MIN_CONSECUTIVE_MISSES, MAX_CONSECUTIVE_MISSES)
                                
                                item_threshold = receive_data._item_thresholds[item.rfid_tag]
                                
                                # SAFETY CHECK 4: Only mark missing after threshold + random probability
                                if receive_data._detection_misses[item.rfid_tag] >= item_threshold:
                                    # SAFETY CHECK 5: Random probability to prevent mass inference
                                    if random.random() < INFERENCE_PROBABILITY:
                                        inference_candidates.append((item, distance, receive_data._detection_misses[item.rfid_tag]))
                            else:
                                # Item too far away, reset counter
                                receive_data._detection_misses[item.rfid_tag] = 0
                        
                        # SAFETY CHECK 6: Limit number of inferences per pass to prevent mass disappearance
                        if inference_candidates:
                            # Sort by miss count (highest first) and take only first N
                            inference_candidates.sort(key=lambda x: x[2], reverse=True)
                            selected = inference_candidates[:MAX_INFERENCES_PER_PASS]
                            
                            for item, distance, misses in selected:
                                item.status = 'not present'
                                newly_missing_items.append(item)
                                logger.info(f"   📦❌ Inferred MISSING: {item.rfid_tag} (distance: {distance:.0f}cm, misses: {misses})")
                                # Reset counter and threshold after marking missing
                                receive_data._detection_misses[item.rfid_tag] = 0
                                receive_data._item_thresholds.pop(item.rfid_tag, None)
                        
                        if newly_missing_items:
                            db.commit()
                            logger.info(f"   🧮 Marked {len(newly_missing_items)} item(s) as 'not present' (inferred)")
                        
                        # Broadcast real-time updates to WebSocket clients
                        await ws_manager.broadcast_position_update({
                            "timestamp": timestamp.isoformat(),
                            "tag_id": "employee",
                            "x": x,
                            "y": y,
                            "confidence": confidence,
                            "num_anchors": len(measurements)
                        })
                        
                        # Broadcast updated items (detected + newly missing)
                        updated_items = []
                        for tag in packet.rfid.tags:
                            inv_item = db.query(InventoryItem).filter(
                                InventoryItem.rfid_tag == tag.epc
                            ).first()
                            if inv_item and inv_item.x_position is not None:
                                prod = db.query(Product).filter(Product.id == inv_item.product_id).first()
                                updated_items.append({
                                    "rfid_tag": inv_item.rfid_tag,
                                    "product_name": prod.name if prod else "Unknown",
                                    "x": inv_item.x_position,
                                    "y": inv_item.y_position,
                                    "status": inv_item.status
                                })
                        
                        # Also include newly missing items in the broadcast
                        for item in newly_missing_items:
                            prod = db.query(Product).filter(Product.id == item.product_id).first()
                            updated_items.append({
                                "rfid_tag": item.rfid_tag,
                                "product_name": prod.name if prod else "Unknown",
                                "x": item.x_position,
                                "y": item.y_position,
                                "status": item.status
                            })
                        
                        if updated_items:
                            await ws_manager.broadcast_item_update(updated_items)
                        
                        # Broadcast updated missing items count for the sidebar
                        if newly_missing_items:
                            missing_items_list = db.query(InventoryItem, Product)\
                                .join(Product, InventoryItem.product_id == Product.id)\
                                .filter(InventoryItem.status == 'not present')\
                                .filter(InventoryItem.last_seen_at.isnot(None))\
                                .all()
                            
                            missing_data = [{
                                "rfid_tag": item.rfid_tag,
                                "product_name": product.name,
                                "x": item.x_position,
                                "y": item.y_position,
                                "status": item.status
                            } for item, product in missing_items_list]
                            
                            await ws_manager.broadcast_missing_update(missing_data)
                        
        except Exception as pos_error:
            logger.warning(f"Position calculation failed: {pos_error}")
        
        return {
            "status": "success",
            "rfid_tags_processed": rfid_tags_processed,
            "uwb_measurements_processed": uwb_measurements_processed,
            "position_calculated": position_calculated,
            "position": calculated_position
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error storing data: {str(e)}")

@router.get("/data/latest", response_model=LatestDataResponse)
def get_latest_data(limit: int = 50, db: Session = Depends(get_db)):
    """Get the most recent detections and UWB measurements"""
    detections = db.query(Detection)\
        .order_by(Detection.timestamp.desc())\
        .limit(limit)\
        .all()
    
    uwb_measurements = db.query(UWBMeasurement)\
        .order_by(UWBMeasurement.timestamp.desc())\
        .limit(limit)\
        .all()
    
    return {
        "detections": [DetectionResponse(
            id=d.id,
            timestamp=d.timestamp.isoformat(),
            product_id=d.product_id,
            product_name=d.product_name,
            x_position=d.x_position,
            y_position=d.y_position,
            status=d.status
        ) for d in detections],
        "uwb_measurements": [UWBMeasurementResponse(
            id=u.id,
            timestamp=u.timestamp.isoformat(),
            mac_address=u.mac_address,
            distance_cm=u.distance_cm,
            status=u.status
        ) for u in uwb_measurements]
    }

@router.get("/data/items", response_model=List[DetectionResponse])
def get_all_items(db: Session = Depends(get_db)):
    """Get all items from inventory that have positions (have been detected)
    
    Returns all items with valid positions - no limit applied since items
    should persist on the map once detected.
    """
    # Get all items with valid positions (both present and missing)
    # No limit - all detected items should persist on the map
    items = db.query(InventoryItem, Product)\
        .join(Product, InventoryItem.product_id == Product.id)\
        .filter(InventoryItem.x_position.isnot(None))\
        .filter(InventoryItem.y_position.isnot(None))\
        .order_by(InventoryItem.id)\
        .all()
    
    return [DetectionResponse(
        id=item.id,
        timestamp=item.last_seen_at.isoformat() if item.last_seen_at else None,
        product_id=item.rfid_tag,
        product_name=product.name,
        x_position=item.x_position,
        y_position=item.y_position,
        status=item.status
    ) for item, product in items]

@router.get("/data/missing", response_model=List[DetectionResponse])
def get_missing_items(db: Session = Depends(get_db)):
    """Get all missing items (status = 'not present' AND was previously seen)
    
    Only returns items that were previously detected by the simulation but are now missing.
    Items that have never been seen (last_seen_at is NULL) are not returned.
    """
    missing_items = db.query(InventoryItem, Product)\
        .join(Product, InventoryItem.product_id == Product.id)\
        .filter(InventoryItem.status == 'not present')\
        .filter(InventoryItem.last_seen_at.isnot(None))\
        .all()
    
    return [DetectionResponse(
        id=item.id,
        timestamp=item.last_seen_at.isoformat() if item.last_seen_at else None,
        product_id=item.rfid_tag,
        product_name=product.name,
        x_position=item.x_position,
        y_position=item.y_position,
        status=item.status
    ) for item, product in missing_items]

@router.delete("/data/clear")
def clear_tracking_data(keep_hours: int = 0, delete_items: bool = False, db: Session = Depends(get_db)):
    """
    Clear old tracking data (positions, detections, UWB measurements, inventory)
    
    Args:
        keep_hours: Keep data from the last N hours. Default 0 = clear everything
        delete_items: If True, completely delete inventory items (for fresh start). 
                      If False (default), just reset item status and positions.
    """
    try:
        inventory_deleted = 0
        purchase_events_deleted = 0
        location_history_deleted = 0
        stock_levels_reset = 0
        products_deleted = 0
        
        if keep_hours > 0:
            cutoff_time = datetime.utcnow() - timedelta(hours=keep_hours)

            positions_deleted = db.query(TagPosition).filter(
                TagPosition.timestamp < cutoff_time
            ).delete()
            
            detections_deleted = db.query(Detection).filter(
                Detection.timestamp < cutoff_time
            ).delete()
            
            uwb_deleted = db.query(UWBMeasurement).filter(
                UWBMeasurement.timestamp < cutoff_time
            ).delete()
            
            inventory_deleted = db.query(InventoryItem).filter(
                InventoryItem.last_seen_at < cutoff_time
            ).delete()
            
            location_history_deleted = db.query(ProductLocationHistory).filter(
                ProductLocationHistory.last_updated < cutoff_time
            ).delete()
        else:
            positions_deleted = db.query(TagPosition).delete()
            detections_deleted = db.query(Detection).delete()
            uwb_deleted = db.query(UWBMeasurement).delete()
            
            if delete_items:
                # Complete deletion - for fresh start in simulation mode
                inventory_deleted = db.query(InventoryItem).delete()
                products_deleted = db.query(Product).delete()
                logger.info(f"Deleted all items ({inventory_deleted}) and products ({products_deleted})")
            else:
                # Reset inventory items to initial state (not visible on map until simulation runs)
                # Also reset positions so simulation can set fresh shelf positions
                items_reset = db.query(InventoryItem).update({
                    InventoryItem.status: 'not present',
                    InventoryItem.last_seen_at: None,
                    InventoryItem.x_position: None,
                    InventoryItem.y_position: None
                })
                inventory_deleted = 0  # Items not deleted, just reset
            
            purchase_events_deleted = db.query(PurchaseEvent).delete()
            location_history_deleted = db.query(ProductLocationHistory).delete()
            
            # Reset all stock levels to zero (fresh start for heatmap)
            stock_levels = db.query(StockLevel).all()
            for stock_level in stock_levels:
                stock_level.max_items_seen = 0
                stock_level.current_count = 0
                stock_level.missing_count = 0
            stock_levels_reset = len(stock_levels)
        
        db.commit()
        
        logger.info(f"Cleared data: {positions_deleted} positions, {detections_deleted} detections, {uwb_deleted} UWB, location_history={location_history_deleted}")
        
        return {
            "message": "Tracking data cleared successfully" + (" (items deleted)" if delete_items else " (items reset)"),
            "positions_deleted": positions_deleted,
            "detections_deleted": detections_deleted,
            "uwb_measurements_deleted": uwb_deleted,
            "inventory_items_deleted": inventory_deleted,
            "products_deleted": products_deleted,
            "purchase_events_deleted": purchase_events_deleted,
            "location_history_deleted": location_history_deleted,
            "stock_levels_reset": stock_levels_reset
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search/items")
def search_items(q: str, db: Session = Depends(get_db)):
    """Search for items by name or RFID tag"""
    from sqlalchemy import func, case
    
    search_term = f"%{q}%"
    
    subquery = db.query(
        InventoryItem.product_id,
        func.min(InventoryItem.id).label('first_item_id'),
        func.count(InventoryItem.id).label('total_count'),
        func.sum(case((InventoryItem.status == 'present', 1), else_=0)).label('present_count'),
        func.sum(case((InventoryItem.status == 'not present', 1), else_=0)).label('missing_count')
    )\
    .group_by(InventoryItem.product_id)\
    .subquery()
    
    results_query = db.query(
        InventoryItem,
        Product,
        subquery.c.total_count,
        subquery.c.present_count,
        subquery.c.missing_count
    )\
    .join(Product, InventoryItem.product_id == Product.id)\
    .join(subquery, InventoryItem.id == subquery.c.first_item_id)\
    .filter(
        (Product.name.ilike(search_term)) |
        (InventoryItem.rfid_tag.ilike(search_term)) |
        (Product.sku.ilike(search_term))
    )\
    .limit(50)\
    .all()
    
    results = []
    for item, product, total_count, present_count, missing_count in results_query:
        results.append({
            "rfid_tag": item.rfid_tag,
            "product_id": product.id,
            "name": product.name,
            "sku": product.sku,
            "category": product.category,
            "x": item.x_position,
            "y": item.y_position,
            "status": "present" if present_count > 0 else "not present",
            "last_seen": item.last_seen_at.isoformat() if item.last_seen_at else None,
            "count": {
                "total": total_count,
                "present": present_count,
                "missing": missing_count
            }
        })
    
    return {
        "query": q,
        "total_results": len(results),
        "items": results
    }

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get basic statistics about stored data"""
    total_detections = db.query(Detection).count()
    total_uwb = db.query(UWBMeasurement).count()
    
    unique_items = db.query(Detection.product_id).distinct().count()
    missing_items = db.query(Detection.product_id)\
        .filter(Detection.status == 'not present')\
        .distinct().count()
    
    latest_detection = db.query(Detection).order_by(Detection.timestamp.desc()).first()
    latest_uwb = db.query(UWBMeasurement).order_by(UWBMeasurement.timestamp.desc()).first()
    
    return {
        "total_detections": total_detections,
        "unique_items": unique_items,
        "missing_items": missing_items,
        "total_uwb_measurements": total_uwb,
        "latest_detection_time": latest_detection.timestamp.isoformat() if latest_detection else None,
        "latest_uwb_time": latest_uwb.timestamp.isoformat() if latest_uwb else None
    }

@router.get("/items/{rfid_tag}")
def get_item_detail(rfid_tag: str, db: Session = Depends(get_db)):
    """Get detailed information about a specific item by RFID tag"""
    item = db.query(InventoryItem)\
        .filter(InventoryItem.rfid_tag == rfid_tag)\
        .first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    product = db.query(Product).filter(Product.id == item.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    same_name_count = db.query(InventoryItem)\
        .filter(
            InventoryItem.product_id == item.product_id,
            InventoryItem.status == "present"
        )\
        .count()
    
    missing_count = db.query(InventoryItem)\
        .filter(
            InventoryItem.product_id == item.product_id,
            InventoryItem.status == "not present"
        )\
        .count()
    
    total_count = db.query(InventoryItem)\
        .filter(InventoryItem.product_id == item.product_id)\
        .count()
    
    return {
        "rfid_tag": item.rfid_tag,
        "product_id": product.id,
        "name": product.name,
        "x_position": item.x_position,
        "y_position": item.y_position,
        "status": item.status,
        "last_seen": item.last_seen_at.isoformat() if item.last_seen_at else None,
        "inventory_summary": {
            "in_stock": same_name_count,
            "missing": missing_count,
            "total": total_count,
            "max_detected": total_count
        }
    }

@router.post("/data/bulk")
def receive_bulk_detections(data: dict, db: Session = Depends(get_db)):
    """
    Receive bulk RFID detections from simulation
    Optimized for high-throughput data ingestion
    """
    detections = data.get("detections", [])
    if not detections:
        return {"status": "success", "processed": 0}
    
    try:
        timestamp = datetime.utcnow()
        processed = 0
        
        for detection in detections:
            # Normalize status
            status_val = detection.get("status", "present")
            if status_val == 'missing':
                status_val = 'not present'
            
            # Store detection
            det = Detection(
                timestamp=timestamp,
                product_id=detection.get("product_id"),
                product_name=detection.get("product_name"),
                x_position=detection.get("x_position"),
                y_position=detection.get("y_position"),
                status=status_val
            )
            db.add(det)
            
            # Update inventory item
            inventory_item = db.query(InventoryItem).filter(
                InventoryItem.rfid_tag == detection.get("product_id")
            ).first()
            
            if inventory_item:
                inventory_item.status = status_val
                inventory_item.x_position = detection.get("x_position")
                inventory_item.y_position = detection.get("y_position")
                # Only update last_seen_at when item is present (detected)
                # This ensures "missing" items only show up if they were previously seen
                if status_val == 'present':
                    inventory_item.last_seen_at = timestamp
            
            processed += 1
        
        db.commit()
        return {"status": "success", "processed": processed}
    
    except Exception as e:
        db.rollback()
        logger.error(f"Bulk detection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/uwb/bulk")
def receive_bulk_uwb(data: dict, db: Session = Depends(get_db)):
    """
    Receive bulk UWB measurements from simulation
    Optimized for high-throughput data ingestion
    """
    measurements = data.get("measurements", [])
    if not measurements:
        return {"status": "success", "processed": 0}
    
    try:
        timestamp = datetime.utcnow()
        processed = 0
        
        for measurement in measurements:
            uwb = UWBMeasurement(
                timestamp=timestamp,
                mac_address=measurement.get("mac_address"),
                distance_cm=measurement.get("distance_cm"),
                status=measurement.get("status", "0x01")
            )
            db.add(uwb)
            processed += 1
        
        # Try triangulation if we have enough measurements
        if len(measurements) >= 2:
            try:
                anchors = db.query(Anchor).filter(Anchor.is_active == True).all()
                if len(anchors) >= 2:
                    # Build measurement tuples (anchor_x, anchor_y, distance)
                    anchor_dict = {a.mac_address: (a.x_position, a.y_position) for a in anchors}
                    measurement_tuples = []
                    for m in measurements:
                        mac = m.get("mac_address")
                        if mac in anchor_dict:
                            ax, ay = anchor_dict[mac]
                            distance = m.get("distance_cm", 0)
                            measurement_tuples.append((ax, ay, distance))
                    
                    if len(measurement_tuples) >= 2:
                        result = TriangulationService.calculate_position(measurement_tuples)
                        if result:
                            x, y, confidence = result
                            
                            if confidence > 0:
                                # Store calculated position
                                position = TagPosition(
                                    timestamp=timestamp,
                                    tag_id="employee",
                                    x_position=x,
                                    y_position=y,
                                    confidence=confidence,
                                    num_anchors=len(measurement_tuples)
                                )
                                db.add(position)
            except Exception as e:
                logger.warning(f"Triangulation failed: {e}")
        
        db.commit()
        return {"status": "success", "processed": processed}
    
    except Exception as e:
        db.rollback()
        logger.error(f"Bulk UWB error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
