"""
Scanner Simulation (RFID + UWB)
================================
Simulates RFID detection and UWB distance measurements.
Produces EXACT hardware format matching ESP32 output.
"""

import math
import random
from typing import List, Tuple, Dict
from .config import SimulationConfig
from .inventory import Item


class ScannerSimulator:
    """Simulates RFID and UWB scanning in hardware format"""
    
    def __init__(self, config: SimulationConfig, items: List[Item], anchor_positions: List[Tuple[float, float]]):
        self.config = config
        self.items = items
        self.anchor_positions = anchor_positions
        self.polling_cycle = 0
        # Track detected items to update their status
        self._last_detected_items = set()
    
    def get_hardware_packet(self, shopper_x: float, shopper_y: float, anchor_macs: List[str], timestamp_ms: int) -> Dict:
        """
        Generate complete hardware packet matching ESP32 format EXACTLY.
        
        Hardware JSON Format (from firmware/code_esp32/code_esp32.ino):
        {
          "polling_cycle": 1,
          "timestamp": 123456,  // milliseconds since boot
          "uwb": {
            "n_anchors": 2,
            "anchors": [
              {
                "mac_address": "0xABCD",
                "average_distance_cm": 150.5,
                "measurements": 3,
                "total_sessions": 5
              }
            ]
          },
          "rfid": {
            "tag_count": 2,
            "tags": [
              {
                "epc": "E200001234567890ABCD",
                "rssi_dbm": -45
              }
            ]
          }
        }
        """
        self.polling_cycle += 1
        
        # Get RFID tags (hardware format)
        rfid_tags = self._scan_rfid_tags(shopper_x, shopper_y)
        
        # Get UWB measurements (hardware format)
        uwb_anchors = self._measure_uwb_distances(shopper_x, shopper_y, anchor_macs)
        
        # Build hardware packet
        packet = {
            "polling_cycle": self.polling_cycle,
            "timestamp": timestamp_ms,
            "uwb": {
                "n_anchors": len(uwb_anchors),
                "anchors": uwb_anchors
            },
            "rfid": {
                "tag_count": len(rfid_tags),
                "tags": rfid_tags
            }
        }
        
        return packet
    
    def _scan_rfid_tags(self, shopper_x: float, shopper_y: float) -> List[Dict]:
        """
        Scan for RFID tags within detection range.
        Returns hardware format: [{"epc": "...", "rssi_dbm": -45, "status": "present"}, ...]
        Also includes missing items when in range with status="not present"
        """
        tags = []
        detection_range = self.config.tag.rfid_detection_range
        currently_detected = set()
        
        for item in self.items:
            # Skip items with null positions
            if item.x is None or item.y is None:
                continue
                
            # Calculate distance
            dx = item.x - shopper_x
            dy = item.y - shopper_y
            distance = math.sqrt(dx*dx + dy*dy)
            
            if distance <= detection_range:
                # Only detect items that are NOT missing (present on shelf)
                if not item.missing:
                    # Calculate realistic RSSI based on distance
                    # Closer = stronger signal (less negative)
                    # Range: -30 dBm (very close) to -70 dBm (far)
                    rssi = int(-30 - (distance / detection_range) * 40)
                    rssi += random.randint(-3, 3)  # Add noise
                    
                    tags.append({
                        "epc": item.rfid_tag,
                        "rssi_dbm": rssi,
                        "status": "present"
                    })
                    
                    currently_detected.add(item.rfid_tag)
                    item.detected = True
                    item.last_seen = shopper_x, shopper_y
                else:
                    # Item is missing but in range - report as not present
                    # This tells the backend that we expected to see it but didn't
                    tags.append({
                        "epc": item.rfid_tag,
                        "rssi_dbm": 0,  # No signal because it's not there
                        "status": "not present"
                    })
        
        self._last_detected_items = currently_detected
        return tags
    
    def _measure_uwb_distances(self, shopper_x: float, shopper_y: float, anchor_macs: List[str]) -> List[Dict]:
        """
        Measure distances to all anchors with realistic noise.
        Returns hardware format: [{"mac_address": "0x1234", "average_distance_cm": 150.5, "measurements": 3, "total_sessions": 5}, ...]
        """
        anchors = []
        
        for i, (anchor_x, anchor_y) in enumerate(self.anchor_positions):
            # Calculate true distance
            dx = anchor_x - shopper_x
            dy = anchor_y - shopper_y
            true_distance = math.sqrt(dx*dx + dy*dy)
            
            # Add realistic noise (±5cm standard deviation)
            noise = random.gauss(0, 5)
            measured_distance = max(0, true_distance + noise)
            
            # Simulate multiple measurements per anchor (like real hardware)
            num_measurements = random.randint(2, 4)  # ESP32 averages multiple readings
            total_sessions = random.randint(num_measurements, num_measurements + 2)
            
            mac = anchor_macs[i] if i < len(anchor_macs) else f"0x{(i+1):04X}"
            
            anchors.append({
                "mac_address": mac,
                "average_distance_cm": round(measured_distance, 1),
                "measurements": num_measurements,
                "total_sessions": total_sessions
            })
        
        return anchors
