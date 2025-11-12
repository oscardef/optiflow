#!/usr/bin/env python3
"""
ESP32 UWB Simulator
===================
Simulates an ESP32 device sending UWB measurements via MQTT.
This allows testing the entire backend pipeline without physical hardware.

Usage:
    python esp32_simulator.py [--broker 172.20.10.3] [--interval 0.5]

Simulates:
- Tag moving around the store
- Distance measurements to 4 anchors
- Realistic noise and signal variations
- Optional RFID detections
"""

import paho.mqtt.client as mqtt
import json
import time
import math
import random
import argparse
from datetime import datetime

# Default configuration
MQTT_BROKER = "172.20.10.3"
MQTT_PORT = 1883
TOPIC_DATA = "store/aisle1"
TOPIC_STATUS = "store/status"
TOPIC_CONTROL = "store/control"

# Simulation parameters
TAG_ID = "tag_0x42"
UPDATE_INTERVAL = 0.5  # seconds between updates

# Anchor MAC addresses (must match your anchor configuration)
ANCHORS = [
    "0x0001",
    "0x0002", 
    "0x0003",
    "0x0004"
]

# Store dimensions (in cm)
STORE_WIDTH = 1000  # 10 meters
STORE_HEIGHT = 800  # 8 meters

# Aisle configuration (vertical aisles)
AISLES = [
    {'x': 200, 'y_start': 150, 'y_end': 700, 'width': 80},  # Aisle 1
    {'x': 400, 'y_start': 150, 'y_end': 700, 'width': 80},  # Aisle 2
    {'x': 600, 'y_start': 150, 'y_end': 700, 'width': 80},  # Aisle 3
    {'x': 800, 'y_start': 150, 'y_end': 700, 'width': 80},  # Aisle 4
]

# Cross aisle (horizontal, connecting all vertical aisles)
CROSS_AISLE_Y = 400
CROSS_AISLE_HEIGHT = 80

class Item:
    """Represents a physical item in the store"""
    def __init__(self, product_id, product_name, x, y):
        self.product_id = product_id
        self.product_name = product_name
        self.x = x
        self.y = y
        self.detected = False
        self.last_seen = None
        self.missing = False

class TagSimulator:
    """Simulates a tag moving around the store with aisle-following behavior"""
    
    def __init__(self, anchor_positions):
        """
        Initialize tag simulator
        
        Args:
            anchor_positions: List of (x, y) tuples for anchor positions
        """
        self.anchor_positions = anchor_positions
        
        # Tag starts at entrance (front center)
        self.x = STORE_WIDTH / 2
        self.y = 100
        
        # Movement state
        self.current_aisle = None
        self.direction = 'down'  # 'down', 'up', 'left', 'right'
        self.target_x = None
        self.target_y = None
        self.speed = 80  # cm/s (walking speed)
        
        # Initialize store items
        self.items = self._generate_store_items()
        self.detection_range = 100  # cm - RFID detection range
        self.missing_items = []  # Track items that went missing
        
    def _generate_store_items(self):
        """Generate items placed throughout the store aisles"""
        items = []
        item_templates = [
            ("Running Shoes", "Footwear"),
            ("Basketball", "Sports"),
            ("Water Bottle", "Accessories"),
            ("Yoga Mat", "Fitness"),
            ("Resistance Bands", "Fitness"),
            ("Tennis Racket", "Sports"),
            ("Gym Bag", "Accessories"),
            ("Dumbbells", "Weights"),
            ("Jump Rope", "Cardio"),
            ("Sports Jersey", "Apparel"),
            ("Soccer Ball", "Sports"),
            ("Protein Powder", "Nutrition"),
            ("Athletic Socks", "Apparel"),
            ("Swimming Goggles", "Swimming"),
            ("Bicycle Helmet", "Cycling"),
        ]
        
        item_id = 1
        # Place items along each aisle
        for aisle in AISLES:
            # 3-5 items per aisle
            num_items = random.randint(3, 5)
            for i in range(num_items):
                # Place items along the aisle with some spacing
                y_position = aisle['y_start'] + (aisle['y_end'] - aisle['y_start']) * (i + 1) / (num_items + 1)
                x_offset = random.uniform(-20, 20)  # Some randomness
                
                template = random.choice(item_templates)
                item = Item(
                    product_id=f"RFID_{item_id:03d}",
                    product_name=f"{template[0]} ({template[1]})",
                    x=aisle['x'] + x_offset,
                    y=y_position
                )
                items.append(item)
                item_id += 1
        
        return items
    
    def _choose_next_target(self):
        """Choose next navigation target (aisle-following pattern)"""
        if self.current_aisle is None:
            # Start by entering first aisle
            self.current_aisle = 0
            aisle = AISLES[self.current_aisle]
            self.target_x = aisle['x']
            self.target_y = aisle['y_start']
            self.direction = 'entering'
        elif self.direction == 'entering':
            # Move down the aisle
            aisle = AISLES[self.current_aisle]
            self.target_y = aisle['y_end']
            self.direction = 'down'
        elif self.direction == 'down':
            # Reached end of aisle, go to cross aisle
            self.target_y = CROSS_AISLE_Y
            self.direction = 'to_cross'
        elif self.direction == 'to_cross':
            # Move to next aisle via cross aisle
            self.current_aisle += 1
            if self.current_aisle >= len(AISLES):
                # Finished all aisles, go back to start
                self.current_aisle = 0
                self.target_x = STORE_WIDTH / 2
                self.target_y = 100
                self.direction = 'returning'
            else:
                aisle = AISLES[self.current_aisle]
                self.target_x = aisle['x']
                self.direction = 'cross_to_aisle'
        elif self.direction == 'cross_to_aisle':
            # Enter next aisle going up
            aisle = AISLES[self.current_aisle]
            self.target_y = aisle['y_start']
            self.direction = 'up'
        elif self.direction == 'up':
            # Reached top of aisle, continue to next aisle
            self.target_y = CROSS_AISLE_Y
            self.direction = 'to_cross'
        elif self.direction == 'returning':
            # Returned to start, begin again
            self.current_aisle = None
            self._choose_next_target()
    
    def update_position(self, dt):
        """Update tag position (aisle-following with realistic movement)"""
        # Choose target if we don't have one
        if self.target_x is None or self.target_y is None:
            self._choose_next_target()
        
        # Calculate direction to target
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        distance = math.sqrt(dx**2 + dy**2)
        
        # If we're close to target, choose next target
        if distance < 20:  # Within 20cm of target
            self._choose_next_target()
            return
        
        # Move toward target
        move_distance = self.speed * dt
        if move_distance > distance:
            move_distance = distance
        
        # Normalize direction and move
        self.x += (dx / distance) * move_distance
        self.y += (dy / distance) * move_distance
        
        # Add slight wandering (realistic human movement)
        wander = 5  # cm
        self.x += random.uniform(-wander, wander)
        self.y += random.uniform(-wander, wander)
        
        # Ensure we stay within store boundaries
        self.x = max(50, min(STORE_WIDTH - 50, self.x))
        self.y = max(50, min(STORE_HEIGHT - 50, self.y))
    
    def measure_distances(self):
        """Calculate distances to all anchors with realistic noise"""
        measurements = []
        
        for i, (anchor_x, anchor_y) in enumerate(self.anchor_positions):
            # True distance
            true_distance = math.sqrt(
                (self.x - anchor_x)**2 + (self.y - anchor_y)**2
            )
            
            # Add realistic UWB measurement noise (~10-30cm std dev)
            noise_std = 15  # cm
            measured_distance = true_distance + random.gauss(0, noise_std)
            
            # UWB has minimum range (~10cm) and measurements are always positive
            measured_distance = max(10, measured_distance)
            
            # Occasionally simulate a bad measurement (multipath, NLOS)
            if random.random() < 0.05:  # 5% bad measurements
                measured_distance += random.uniform(-100, 100)
                status = "ERROR"
            else:
                status = "SUCCESS"
            
            measurements.append({
                "mac_address": ANCHORS[i],
                "distance_cm": round(measured_distance, 1),
                "status": status
            })
        
        return measurements
    
    def get_rfid_detections(self):
        """Detect items within range and check for missing items"""
        detections = []
        new_missing = []
        
        for item in self.items:
            distance = math.sqrt((self.x - item.x)**2 + (self.y - item.y)**2)
            
            if distance < self.detection_range:
                # Within detection range
                if not item.missing:
                    # 2% chance item goes missing (stolen/moved)
                    if random.random() < 0.02:
                        item.missing = True
                        item.last_seen = datetime.utcnow()
                        new_missing.append(item)
                        print(f"   ⚠️  MISSING: {item.product_name} at ({item.x:.0f}, {item.y:.0f})")
                    else:
                        # Item detected normally
                        detections.append({
                            "product_id": item.product_id,
                            "product_name": item.product_name,
                            "x_position": item.x,
                            "y_position": item.y,
                            "status": "present"
                        })
                        item.detected = True
                        item.last_seen = datetime.utcnow()
                else:
                    # Item is missing - report it
                    detections.append({
                        "product_id": item.product_id,
                        "product_name": item.product_name,
                        "x_position": item.x,
                        "y_position": item.y,
                        "status": "missing"
                    })
        
        # Store missing items for notification
        if new_missing:
            self.missing_items.extend(new_missing)
        
        return detections
    
    def get_all_items(self):
        """Return all items in the store for initial map population"""
        return [{
            "product_id": item.product_id,
            "product_name": item.product_name,
            "x_position": item.x,
            "y_position": item.y,
            "status": "missing" if item.missing else "present" if item.detected else "unknown"
        } for item in self.items]

def on_connect(client, userdata, flags, rc):
    """Callback when connected to MQTT broker"""
    if rc == 0:
        print(f"✅ Connected to MQTT broker at {MQTT_BROKER}")
        client.subscribe(TOPIC_CONTROL)
        
        # Publish status
        client.publish(TOPIC_STATUS, "ESP32_SIMULATOR_READY")
        print(f"📤 Published status to {TOPIC_STATUS}")
    else:
        print(f"❌ Connection failed with code {rc}")

def on_message(client, userdata, msg):
    """Callback when receiving MQTT messages"""
    print(f"📥 Received: {msg.topic} - {msg.payload.decode()}")
    
    if msg.topic == TOPIC_CONTROL:
        command = msg.payload.decode()
        if command == "START":
            userdata['running'] = True
            print("▶️  Starting simulation...")
        elif command == "STOP":
            userdata['running'] = False
            print("⏸️  Pausing simulation...")

def main():
    parser = argparse.ArgumentParser(description="ESP32 UWB Simulator")
    parser.add_argument("--broker", default=MQTT_BROKER, help="MQTT broker address")
    parser.add_argument("--port", type=int, default=MQTT_PORT, help="MQTT broker port")
    parser.add_argument("--interval", type=float, default=UPDATE_INTERVAL, help="Update interval in seconds")
    parser.add_argument("--anchors", nargs='+', help="Anchor MAC addresses (space separated)")
    args = parser.parse_args()
    
    # Override anchors if provided
    if args.anchors:
        global ANCHORS
        ANCHORS = args.anchors
    
    # Define anchor positions (should match your actual setup)
    # These are in cm coordinates matching the store dimensions
    anchor_positions = [
        (100, 100),      # Anchor 0x0001 - Front Left
        (900, 100),      # Anchor 0x0002 - Front Right
        (900, 700),      # Anchor 0x0003 - Back Right
        (100, 700)       # Anchor 0x0004 - Back Left
    ]
    
    print("🚀 ESP32 UWB Simulator")
    print("=" * 50)
    print(f"MQTT Broker: {args.broker}:{args.port}")
    print(f"Publishing to: {TOPIC_DATA}")
    print(f"Update interval: {args.interval}s")
    print(f"Anchors: {ANCHORS}")
    print(f"Store size: {STORE_WIDTH}x{STORE_HEIGHT} cm")
    print("=" * 50)
    
    # Initialize simulator
    tag_sim = TagSimulator(anchor_positions)
    
    # Setup MQTT client
    userdata = {'running': False}
    client = mqtt.Client(userdata=userdata)
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(args.broker, args.port, 60)
        client.loop_start()
        
        print("\n⏳ Waiting for START command...")
        print(f"   Send: mosquitto_pub -h {args.broker} -t {TOPIC_CONTROL} -m 'START'\n")
        
        last_time = time.time()
        packet_count = 0
        
        while True:
            current_time = time.time()
            dt = current_time - last_time
            
            if userdata['running']:
                # Update tag position
                tag_sim.update_position(dt)
                
                # Generate measurements
                uwb_measurements = tag_sim.measure_distances()
                detections = tag_sim.get_rfid_detections()
                
                # Build packet
                packet = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "detections": detections,
                    "uwb_measurements": uwb_measurements
                }
                
                # Publish to MQTT
                payload = json.dumps(packet)
                result = client.publish(TOPIC_DATA, payload)
                
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    packet_count += 1
                    print(f"📤 [{packet_count}] Published - Tag position: ({tag_sim.x:.0f}, {tag_sim.y:.0f}) cm")
                    if detections:
                        print(f"   🏷️  RFID: {detections[0]['product_name']}")
                else:
                    print(f"❌ Publish failed with code {result.rc}")
            
            last_time = current_time
            time.sleep(args.interval)
    
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping simulator...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        client.loop_stop()
        client.disconnect()
        print("👋 Disconnected")

if __name__ == "__main__":
    main()
