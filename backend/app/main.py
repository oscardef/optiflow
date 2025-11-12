from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List

from .database import get_db, init_db
from .models import Detection, UWBMeasurement
from .schemas import DataPacket, LatestDataResponse, DetectionResponse, UWBMeasurementResponse

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
        
        # Store detections
        detection_ids = []
        for det in packet.detections:
            detection = Detection(
                timestamp=timestamp,
                product_id=det.product_id,
                product_name=det.product_name
            )
            db.add(detection)
            db.flush()
            detection_ids.append(detection.id)
        
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
        
        return {
            "status": "success",
            "detections_stored": len(detection_ids),
            "uwb_measurements_stored": len(uwb_ids)
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
            product_name=d.product_name
        ) for d in detections],
        "uwb_measurements": [UWBMeasurementResponse(
            id=u.id,
            timestamp=u.timestamp.isoformat(),
            mac_address=u.mac_address,
            distance_cm=u.distance_cm,
            status=u.status
        ) for u in uwb_measurements]
    }

@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get basic statistics about stored data"""
    total_detections = db.query(Detection).count()
    total_uwb = db.query(UWBMeasurement).count()
    
    # Get latest timestamps
    latest_detection = db.query(Detection).order_by(Detection.timestamp.desc()).first()
    latest_uwb = db.query(UWBMeasurement).order_by(UWBMeasurement.timestamp.desc()).first()
    
    return {
        "total_detections": total_detections,
        "total_uwb_measurements": total_uwb,
        "latest_detection_time": latest_detection.timestamp.isoformat() if latest_detection else None,
        "latest_uwb_time": latest_uwb.timestamp.isoformat() if latest_uwb else None
    }
