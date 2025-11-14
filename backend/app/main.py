from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional

from .database import get_db, init_db
from .models import Detection, UWBMeasurement, Anchor, TagPosition
from .schemas import (
    DataPacket, LatestDataResponse, DetectionResponse, UWBMeasurementResponse,
    AnchorCreate, AnchorUpdate, AnchorResponse, TagPositionResponse
)
from .triangulation import TriangulationService

app = FastAPI(title="OptiFlow API", version="1.0.0")

# CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    """Initialize database on startup"""
    init_db()
    print("✅ Database initialized")

@app.get("/")
def root():
    """Health check endpoint"""
    return {"status": "online", "service": "OptiFlow Backend"}

@app.post("/data", status_code=201)
def receive_data(packet: DataPacket, db: Session = Depends(get_db)):
    """
    Receive detection packet from MQTT bridge
    
    Expected format:
    {
        "timestamp": "2024-11-12T10:30:00",
        "detections": [
            {"product_id": "RFID001", "product_name": "Running Shoes"}
        ],
        "uwb_measurements": [
            {"mac_address": "A1:B2:C3", "distance_cm": 150.5, "status": "0x01"}
        ]
    }
    """
    try:
        # Parse timestamp
        timestamp = datetime.fromisoformat(packet.timestamp.replace('Z', '+00:00'))
        
        # Store detections - UPDATE existing records instead of always creating new ones
        detection_ids = []
        for det in packet.detections:
            # Check if this item already exists (find most recent detection)
            existing = db.query(Detection)\
                .filter(Detection.product_id == det.product_id)\
                .order_by(Detection.timestamp.desc())\
                .first()
            
            status = det.status if det.status else "present"
            
            # Only create new record if status changed or first detection
            if not existing or existing.status != status:
                detection = Detection(
                    timestamp=timestamp,
                    product_id=det.product_id,
                    product_name=det.product_name,
                    x_position=det.x_position,
                    y_position=det.y_position,
                    status=status
                )
                db.add(detection)
                db.flush()
                detection_ids.append(detection.id)
            else:
                # Item already exists with same status - just update timestamp
                existing.timestamp = timestamp
                db.flush()
                detection_ids.append(existing.id)
        
        # Store UWB measurements
        uwb_ids = []
        for uwb in packet.uwb_measurements:
            measurement = UWBMeasurement(
                timestamp=timestamp,
                mac_address=uwb.mac_address,
                distance_cm=uwb.distance_cm,
                status=uwb.status
            )
            db.add(measurement)
            db.flush()
            uwb_ids.append(measurement.id)
        
        db.commit()
        
        # AUTO-CALCULATE POSITION if we have enough anchor data
        position_calculated = False
        try:
            # Get active anchors
            anchors = db.query(Anchor).filter(Anchor.is_active == True).all()
            
            if len(anchors) < 2:
                print(f"⚠️  Cannot calculate position: only {len(anchors)} active anchor(s). Need at least 2.")
            
            if len(anchors) >= 2 and len(packet.uwb_measurements) >= 2:
                # Build measurement list from incoming data
                measurements = []
                for uwb in packet.uwb_measurements:
                    anchor = next((a for a in anchors if a.mac_address == uwb.mac_address), None)
                    if anchor:
                        measurements.append((
                            anchor.x_position,
                            anchor.y_position,
                            uwb.distance_cm
                        ))
                
                if len(measurements) >= 2:
                    result = TriangulationService.calculate_position(measurements)
                    if result:
                        x, y, confidence = result
                        position = TagPosition(
                            timestamp=timestamp,
                            tag_id="tag_0x42",  # Default tag ID (could extract from packet later)
                            x_position=x,
                            y_position=y,
                            confidence=confidence,
                            num_anchors=len(measurements)
                        )
                        db.add(position)
                        db.commit()
                        position_calculated = True
        except Exception as pos_error:
            print(f"⚠️ Position calculation failed: {pos_error}")
            # Don't fail the whole request if position calc fails
        
        return {
            "status": "success",
            "detections_stored": len(detection_ids),
            "uwb_measurements_stored": len(uwb_ids),
            "position_calculated": position_calculated
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error storing data: {str(e)}")

@app.get("/data/latest", response_model=LatestDataResponse)
def get_latest_data(limit: int = 50, db: Session = Depends(get_db)):
    """
    Get the most recent detections and UWB measurements
    
    Query params:
    - limit: Maximum number of records to return (default: 50)
    """
    # Get recent detections (last hour by default, or latest N)
    detections = db.query(Detection)\
        .order_by(Detection.timestamp.desc())\
        .limit(limit)\
        .all()
    
    # Get recent UWB measurements
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

@app.get("/data/items", response_model=List[DetectionResponse])
def get_all_items(db: Session = Depends(get_db)):
    """
    Get all unique items with their latest status
    Returns the most recent detection for each product_id
    This prevents issues with query limits causing items to disappear
    """
    # Get all detections ordered by timestamp descending
    all_detections = db.query(Detection)\
        .order_by(Detection.timestamp.desc())\
        .all()
    
    # Group by product_id to get only the latest detection of each item
    latest_items = {}
    for item in all_detections:
        if item.product_id not in latest_items:
            latest_items[item.product_id] = item
    
    return [DetectionResponse(
        id=d.id,
        timestamp=d.timestamp.isoformat(),
        product_id=d.product_id,
        product_name=d.product_name,
        x_position=d.x_position,
        y_position=d.y_position,
        status=d.status
    ) for d in latest_items.values()]

@app.get("/data/missing", response_model=List[DetectionResponse])
def get_missing_items(db: Session = Depends(get_db)):
    """
    Get all missing items (status = 'missing')
    This endpoint returns ALL missing items regardless of employee position
    Used for persistent missing items display on frontend
    """
    missing_items = db.query(Detection)\
        .filter(Detection.status == 'missing')\
        .order_by(Detection.timestamp.desc())\
        .all()
    
    # Group by product_id to get only the latest status of each item
    latest_missing = {}
    for item in missing_items:
        if item.product_id not in latest_missing:
            latest_missing[item.product_id] = item
    
    return [DetectionResponse(
        id=d.id,
        timestamp=d.timestamp.isoformat(),
        product_id=d.product_id,
        product_name=d.product_name,
        x_position=d.x_position,
        y_position=d.y_position,
        status=d.status
    ) for d in latest_missing.values()]

@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get basic statistics about stored data"""
    total_detections = db.query(Detection).count()
    total_uwb = db.query(UWBMeasurement).count()
    
    # Count unique items (by product_id)
    unique_items = db.query(Detection.product_id).distinct().count()
    missing_items = db.query(Detection.product_id)\
        .filter(Detection.status == 'missing')\
        .distinct().count()
    
    # Get latest timestamps
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

# ============================================
# ANCHOR MANAGEMENT ENDPOINTS
# ============================================

@app.get("/anchors", response_model=List[AnchorResponse])
def get_anchors(db: Session = Depends(get_db)):
    """Get all configured anchors"""
    anchors = db.query(Anchor).all()
    return [AnchorResponse(
        id=a.id,
        mac_address=a.mac_address,
        name=a.name,
        x_position=a.x_position,
        y_position=a.y_position,
        is_active=a.is_active,
        created_at=a.created_at.isoformat(),
        updated_at=a.updated_at.isoformat()
    ) for a in anchors]

@app.post("/anchors", response_model=AnchorResponse, status_code=201)
def create_anchor(anchor: AnchorCreate, db: Session = Depends(get_db)):
    """Create a new anchor configuration"""
    # Check if anchor with this MAC already exists
    existing = db.query(Anchor).filter(Anchor.mac_address == anchor.mac_address).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Anchor with MAC {anchor.mac_address} already exists")
    
    new_anchor = Anchor(
        mac_address=anchor.mac_address,
        name=anchor.name,
        x_position=anchor.x_position,
        y_position=anchor.y_position,
        is_active=anchor.is_active
    )
    db.add(new_anchor)
    db.commit()
    db.refresh(new_anchor)
    
    return AnchorResponse(
        id=new_anchor.id,
        mac_address=new_anchor.mac_address,
        name=new_anchor.name,
        x_position=new_anchor.x_position,
        y_position=new_anchor.y_position,
        is_active=new_anchor.is_active,
        created_at=new_anchor.created_at.isoformat(),
        updated_at=new_anchor.updated_at.isoformat()
    )

@app.put("/anchors/{anchor_id}", response_model=AnchorResponse)
def update_anchor(anchor_id: int, anchor_update: AnchorUpdate, db: Session = Depends(get_db)):
    """Update an existing anchor configuration"""
    anchor = db.query(Anchor).filter(Anchor.id == anchor_id).first()
    if not anchor:
        raise HTTPException(status_code=404, detail=f"Anchor {anchor_id} not found")
    
    # Update fields if provided
    if anchor_update.name is not None:
        anchor.name = anchor_update.name
    if anchor_update.x_position is not None:
        anchor.x_position = anchor_update.x_position
    if anchor_update.y_position is not None:
        anchor.y_position = anchor_update.y_position
    if anchor_update.is_active is not None:
        anchor.is_active = anchor_update.is_active
    
    anchor.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(anchor)
    
    return AnchorResponse(
        id=anchor.id,
        mac_address=anchor.mac_address,
        name=anchor.name,
        x_position=anchor.x_position,
        y_position=anchor.y_position,
        is_active=anchor.is_active,
        created_at=anchor.created_at.isoformat(),
        updated_at=anchor.updated_at.isoformat()
    )

@app.delete("/anchors/{anchor_id}", status_code=204)
def delete_anchor(anchor_id: int, db: Session = Depends(get_db)):
    """Delete an anchor configuration"""
    anchor = db.query(Anchor).filter(Anchor.id == anchor_id).first()
    if not anchor:
        raise HTTPException(status_code=404, detail=f"Anchor {anchor_id} not found")
    
    db.delete(anchor)
    db.commit()
    return None

# ============================================
# TAG POSITION / TRIANGULATION ENDPOINTS
# ============================================

@app.get("/positions/latest", response_model=List[TagPositionResponse])
def get_latest_positions(limit: int = 50, db: Session = Depends(get_db)):
    """Get the most recent calculated tag positions"""
    positions = db.query(TagPosition)\
        .order_by(TagPosition.timestamp.desc())\
        .limit(limit)\
        .all()
    
    return [TagPositionResponse(
        id=p.id,
        timestamp=p.timestamp.isoformat(),
        tag_id=p.tag_id,
        x_position=p.x_position,
        y_position=p.y_position,
        confidence=p.confidence,
        num_anchors=p.num_anchors
    ) for p in positions]

@app.post("/calculate-position")
def calculate_position(tag_id: str, db: Session = Depends(get_db)):
    """
    Calculate current position of a tag based on recent UWB measurements
    
    This endpoint:
    1. Gets the latest UWB measurements for all active anchors
    2. Looks up anchor positions from the database
    3. Performs trilateration to calculate tag position
    4. Stores the result in tag_positions table
    """
    # Get active anchors
    anchors = db.query(Anchor).filter(Anchor.is_active == True).all()
    
    if len(anchors) < 2:
        raise HTTPException(
            status_code=400, 
            detail="At least 2 active anchors required for position calculation"
        )
    
    # Get latest UWB measurement for each anchor (within last 5 seconds)
    cutoff_time = datetime.utcnow() - timedelta(seconds=5)
    measurements = []
    
    for anchor in anchors:
        uwb = db.query(UWBMeasurement)\
            .filter(
                UWBMeasurement.mac_address == anchor.mac_address,
                UWBMeasurement.timestamp >= cutoff_time
            )\
            .order_by(UWBMeasurement.timestamp.desc())\
            .first()
        
        if uwb:
            # Convert cm to same units as anchor positions
            measurements.append((
                anchor.x_position,
                anchor.y_position,
                uwb.distance_cm
            ))
    
    if len(measurements) < 2:
        raise HTTPException(
            status_code=400,
            detail="Not enough recent measurements. Need at least 2 anchors with data from last 5 seconds"
        )
    
    # Calculate position using triangulation
    result = TriangulationService.calculate_position(measurements)
    
    if result is None:
        raise HTTPException(status_code=500, detail="Position calculation failed")
    
    x, y, confidence = result
    
    # Store the calculated position
    position = TagPosition(
        timestamp=datetime.utcnow(),
        tag_id=tag_id,
        x_position=x,
        y_position=y,
        confidence=confidence,
        num_anchors=len(measurements)
    )
    db.add(position)
    db.commit()
    db.refresh(position)
    
    return TagPositionResponse(
        id=position.id,
        timestamp=position.timestamp.isoformat(),
        tag_id=position.tag_id,
        x_position=position.x_position,
        y_position=position.y_position,
        confidence=position.confidence,
        num_anchors=position.num_anchors
    )


@app.delete("/data/clear")
def clear_tracking_data(
    keep_hours: int = 0,
    db: Session = Depends(get_db)
):
    """
    Clear old tracking data (positions, detections, UWB measurements)
    
    Args:
        keep_hours: Keep data from the last N hours. Default 0 = clear everything
    """
    try:
        if keep_hours > 0:
            cutoff_time = datetime.utcnow() - timedelta(hours=keep_hours)
            
            # Delete old positions
            positions_deleted = db.query(TagPosition).filter(
                TagPosition.timestamp < cutoff_time
            ).delete()
            
            # Delete old detections
            detections_deleted = db.query(Detection).filter(
                Detection.timestamp < cutoff_time
            ).delete()
            
            # Delete old UWB measurements
            uwb_deleted = db.query(UWBMeasurement).filter(
                UWBMeasurement.timestamp < cutoff_time
            ).delete()
        else:
            # Clear everything
            positions_deleted = db.query(TagPosition).delete()
            detections_deleted = db.query(Detection).delete()
            uwb_deleted = db.query(UWBMeasurement).delete()
        
        db.commit()
        
        return {
            "message": "Tracking data cleared successfully",
            "positions_deleted": positions_deleted,
            "detections_deleted": detections_deleted,
            "uwb_measurements_deleted": uwb_deleted
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
