"""
Scanner Simulation (RFID + UWB)
================================
Simulates RFID detection and UWB distance measurements.
"""

import math
import random
from typing import List, Tuple, Dict
from .config import SimulationConfig
from .inventory import Item


class ScannerSimulator:
    """Simulates RFID and UWB scanning"""
    
    def __init__(self, config: SimulationConfig, items: List[Item], anchor_positions: List[Tuple[float, float]]):
        self.config = config
        self.items = items
        self.anchor_positions = anchor_positions
    
    def get_rfid_detections(self, shopper_x: float, shopper_y: float) -> List[Dict]:
        """
        Detect items within RFID range
        Returns list of detection dicts
        """
        detections = []
        detection_range = self.config.tag.rfid_detection_range
        
        for item in self.items:
            # Calculate distance
            dx = item.x - shopper_x
            dy = item.y - shopper_y
            distance = math.sqrt(dx*dx + dy*dy)
            
            if distance <= detection_range:
                # Determine status
                if item.missing:
                    status = "missing"
                else:
                    status = "present"
                    item.detected = True
                    item.last_seen = shopper_x, shopper_y
                
                # Only report if status changed or first detection
                if item.reported_status != status or item.reported_status is None:
                    detections.append({
                        "product_id": item.rfid_tag,
                        "product_name": item.product.name,
                        "x_position": item.x,
                        "y_position": item.y,
                        "status": status
                    })
                    item.reported_status = status
        
        return detections
    
    def measure_distances(self, shopper_x: float, shopper_y: float, anchor_macs: List[str]) -> List[Dict]:
        """
        Measure distances to all anchors with realistic noise
        Returns list of UWB measurement dicts
        """
        measurements = []
        
        for i, (anchor_x, anchor_y) in enumerate(self.anchor_positions):
            # Calculate true distance
            dx = anchor_x - shopper_x
            dy = anchor_y - shopper_y
            true_distance = math.sqrt(dx*dx + dy*dy)
            
            # Add realistic noise (±5cm standard deviation)
            noise = random.gauss(0, 5)
            measured_distance = max(0, true_distance + noise)
            
            measurements.append({
                "mac_address": anchor_macs[i] if i < len(anchor_macs) else f"0x000{i+1}",
                "distance_cm": round(measured_distance, 2),
                "status": "0x01"  # OK status
            })
        
        return measurements
