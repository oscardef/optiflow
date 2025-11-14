#!/usr/bin/env python3
"""
ESP32 UWB Simulator
===================
Simulates an ESP32 device sending UWB measurements via MQTT.
This allows testing the entire backend pipeline without physical hardware.

Usage:
    python esp32_simulator.py [--broker 172.20.10.3] [--interval 0.5] [--api http://localhost:8000]

Simulates:
- Tag moving around the store (independent of anchor positions)
- Distance measurements to configured anchors (fetched from backend)
- Realistic noise and signal variations
- RFID detections of items
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
UPDATE_INTERVAL = 0.15  # seconds between updates (faster for more fluid movement)

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
    {'x': 200, 'y_start': 150, 'y_end': 700, 'width': 80},  # Aisle 1 - full coverage
    {'x': 400, 'y_start': 120, 'y_end': 700, 'width': 80},  # Aisle 2 - higher and lower
    {'x': 600, 'y_start': 120, 'y_end': 700, 'width': 80},  # Aisle 3 - higher and lower
    {'x': 800, 'y_start': 120, 'y_end': 700, 'width': 80},  # Aisle 4 - higher and lower
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
        self.reported_status = None  # Track last reported status to backend

class TagSimulator:
    """Simulates a tag moving around the store with aisle-following behavior"""
    
    def __init__(self, anchor_positions):
        """
        Initialize tag simulator
        
        Args:
            anchor_positions: List of (x, y) tuples for anchor positions (only used for distance calculations)
        """
        self.anchor_positions = anchor_positions
        
        # Tag starts at top of Aisle 1
        # Movement is completely independent of anchor positions!
        self.x = AISLES[0]['x']
        self.y = AISLES[0]['y_start']
        
        # Movement state for back-and-forth pattern
        self.current_aisle = 0  # Start at Aisle 1 (index 0)
        self.direction = 'forward'  # 'forward' = 1->4, 'backward' = 4->1
        self.movement_phase = 'going_down'  # 'going_down', 'going_up', 'at_cross'
        self.target_x = AISLES[0]['x']
        self.target_y = AISLES[0]['y_end']
        self.speed = 150  # cm/s (5x faster - was 30 cm/s)
        self.first_pass_complete = False  # Track if we've done first pass
        self.pass_count = 0  # Count how many complete passes through store
        self.aisles_visited = set()  # Track which aisles visited this pass
        
        # Initialize store items
        self.items = self._generate_store_items()
        self.detection_range = 150  # cm - RFID detection range (1.5 meters)
        self.expected_items = {item.product_id: item for item in self.items}  # All items are expected
        # Don't remove items initially - wait for first pass to complete
        
    def _generate_store_items(self):
        """Generate hundreds of hardcoded items at fixed shelf locations"""
        items = []
        item_id = 1
        
        # Product catalog with categories
        product_catalog = [
            # Sports Equipment
            ("Basketball", "Sports"), ("Soccer Ball", "Sports"), ("Tennis Ball", "Sports"),
            ("Baseball", "Sports"), ("Volleyball", "Sports"), ("Football", "Sports"),
            ("Tennis Racket", "Sports"), ("Badminton Set", "Sports"), ("Table Tennis Paddle", "Sports"),
            
            # Footwear
            ("Running Shoes", "Footwear"), ("Training Shoes", "Footwear"), ("Basketball Shoes", "Footwear"),
            ("Soccer Cleats", "Footwear"), ("Tennis Shoes", "Footwear"), ("Hiking Boots", "Footwear"),
            ("Casual Sneakers", "Footwear"), ("Sandals", "Footwear"), ("Flip Flops", "Footwear"),
            
            # Fitness Equipment
            ("Yoga Mat", "Fitness"), ("Resistance Bands", "Fitness"), ("Jump Rope", "Cardio"),
            ("Dumbbells 5lb", "Weights"), ("Dumbbells 10lb", "Weights"), ("Dumbbells 15lb", "Weights"),
            ("Kettlebell", "Weights"), ("Exercise Ball", "Fitness"), ("Foam Roller", "Fitness"),
            ("Pull-up Bar", "Fitness"), ("Ab Wheel", "Fitness"), ("Ankle Weights", "Fitness"),
            
            # Accessories
            ("Water Bottle", "Accessories"), ("Gym Bag", "Accessories"), ("Sports Backpack", "Accessories"),
            ("Gym Towel", "Accessories"), ("Sweatband", "Accessories"), ("Sports Watch", "Accessories"),
            ("Fitness Tracker", "Accessories"), ("Headphones", "Electronics"), ("Armband", "Accessories"),
            
            # Apparel
            ("Sports Jersey", "Apparel"), ("Athletic Shorts", "Apparel"), ("Track Pants", "Apparel"),
            ("Athletic Socks", "Apparel"), ("Compression Shorts", "Apparel"), ("Tank Top", "Apparel"),
            ("Hoodie", "Apparel"), ("Windbreaker", "Apparel"), ("Sports Bra", "Apparel"),
            
            # Swimming
            ("Swimming Goggles", "Swimming"), ("Swim Cap", "Swimming"), ("Kickboard", "Swimming"),
            ("Pull Buoy", "Swimming"), ("Swim Fins", "Swimming"), ("Nose Clip", "Swimming"),
            
            # Cycling
            ("Bicycle Helmet", "Cycling"), ("Bike Gloves", "Cycling"), ("Cycling Jersey", "Cycling"),
            ("Bike Lock", "Cycling"), ("Water Bottle Holder", "Cycling"), ("Bike Light", "Cycling"),
            
            # Nutrition
            ("Protein Powder", "Nutrition"), ("Energy Bar", "Nutrition"), ("Protein Bar", "Nutrition"),
            ("Sports Drink", "Nutrition"), ("Electrolyte Mix", "Nutrition"), ("Pre-Workout", "Nutrition"),
            ("BCAA", "Nutrition"), ("Creatine", "Nutrition"), ("Multivitamin", "Nutrition"),
        ]
        
        # Place items systematically in aisles with high density
        for aisle_idx, aisle in enumerate(AISLES):
            # Calculate shelf positions (4 shelves per aisle, both sides)
            shelf_positions = []
            
            # Left side shelves
            for shelf in range(4):
                x_pos = aisle['x'] - 25  # 25cm from aisle center
                shelf_positions.append(('left', shelf, x_pos))
            
            # Right side shelves  
            for shelf in range(4):
                x_pos = aisle['x'] + 25  # 25cm from aisle center
                shelf_positions.append(('right', shelf, x_pos))
            
            # Items per shelf (15-20 items per shelf level)
            items_per_shelf = 18
            aisle_length = aisle['y_end'] - aisle['y_start']
            
            for side, shelf_level, x_pos in shelf_positions:
                for item_slot in range(items_per_shelf):
                    # Calculate Y position along the shelf
                    y_pos = aisle['y_start'] + (aisle_length * (item_slot + 0.5) / items_per_shelf)
                    
                    # Select product from catalog (cycle through)
                    product = product_catalog[(item_id - 1) % len(product_catalog)]
                    
                    item = Item(
                        product_id=f"RFID_{item_id:04d}",
                        product_name=f"{product[0]} ({product[1]})",
                        x=x_pos,
                        y=y_pos
                    )
                    items.append(item)
                    item_id += 1
        
        # Add items in cross-aisle area
        for x_pos in range(200, 900, 50):
            for side_offset in [-30, 30]:
                y_pos = CROSS_AISLE_Y + side_offset
                product = product_catalog[(item_id - 1) % len(product_catalog)]
                item = Item(
                    product_id=f"RFID_{item_id:04d}",
                    product_name=f"{product[0]} ({product[1]})",
                    x=x_pos,
                    y=y_pos
                )
                items.append(item)
                item_id += 1
        
        print(f"📦 Generated {len(items)} items in store")
        return items
    
    def _check_for_missing_items(self):
        """
        After first pass, randomly mark some detected items as missing
        Small chance per pass to simulate items going missing
        """
        if not self.first_pass_complete:
            return
        
        # Only check items that were previously detected as present
        detected_items = [item for item in self.items if item.detected and not item.missing]
        
        if not detected_items:
            return
        
        # Small chance (1-2%) that an item goes missing each pass
        num_to_mark_missing = int(len(detected_items) * random.uniform(0.01, 0.02))
        
        if num_to_mark_missing > 0:
            items_to_mark = random.sample(detected_items, min(num_to_mark_missing, len(detected_items)))
            
            for item in items_to_mark:
                item.missing = True
                item.detected = False  # Will be re-detected as missing
                print(f"⚠️  Item went missing: {item.product_name} ({item.product_id})")
    
    def _randomly_remove_items(self):
        """Legacy function - no longer used. Items only go missing after first pass."""
        pass
        
    def _generate_store_items_legacy(self):
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
        """
        Back-and-forth navigation pattern:
        Forward (1->4): Down aisle 1, cross to 2, up 2, down 2, cross to 3, up 3, down 3, cross to 4, up 4, down 4
        Backward (4->1): Cross to 3, up 3, down 3, cross to 2, up 2, down 2, cross to 1, up 1, down 1
        Repeat...
        """
        aisle = AISLES[self.current_aisle]
        
        if self.movement_phase == 'going_down':
            self.target_x = aisle['x']
            self.target_y = aisle['y_end']
        elif self.movement_phase == 'going_up':
            self.target_x = aisle['x']
            self.target_y = aisle['y_start']
        elif self.movement_phase == 'at_cross':
            self.target_x = aisle['x']
            self.target_y = CROSS_AISLE_Y
    
    def update_position(self, dt):
        """
        Update tag position with simple back-and-forth navigation
        
        IMPORTANT: Employee movement is completely independent of anchor positions!
        The employee walks through aisles following a predefined path regardless
        of where anchors are placed. This simulates real-world behavior where
        employees follow store layout, not UWB anchor positions.
        """
        # Set current target
        self._choose_next_target()
        
        # Calculate direction to target
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        distance = math.sqrt(dx**2 + dy**2)
        
        # Check if we reached a waypoint
        if distance < 25:  # Within 25cm of target (looser for high speed)
            self.aisles_visited.add(self.current_aisle)
            
            if self.movement_phase == 'going_down':
                # Just finished going down, now go to cross aisle
                self.movement_phase = 'at_cross'
                
            elif self.movement_phase == 'at_cross':
                # At cross aisle, determine next move
                if self.current_aisle == 0 and self.direction == 'forward':
                    # Finished aisle 1, move to aisle 2
                    self.current_aisle = 1
                    self.movement_phase = 'going_up'
                    
                elif self.direction == 'forward' and self.current_aisle < len(AISLES) - 1:
                    # Moving forward, go to next aisle
                    self.current_aisle += 1
                    self.movement_phase = 'going_up'
                    
                elif self.direction == 'forward' and self.current_aisle == len(AISLES) - 1:
                    # Just finished last aisle going forward, switch to backward
                    self.direction = 'backward'
                    self.current_aisle = len(AISLES) - 2  # Go to aisle 3
                    self.movement_phase = 'going_up'
                    
                elif self.direction == 'backward' and self.current_aisle > 0:
                    # Moving backward, go to previous aisle
                    self.current_aisle -= 1
                    self.movement_phase = 'going_up'
                    
                elif self.direction == 'backward' and self.current_aisle == 0:
                    # Back at aisle 1, completed a full cycle
                    if len(self.aisles_visited) == len(AISLES):
                        # Visited all aisles, complete the pass
                        self.pass_count += 1
                        self.aisles_visited.clear()
                        
                        if self.pass_count == 1:
                            print(f"\n✅ First pass complete! Starting to simulate missing items...\n")
                            self.first_pass_complete = True
                        
                        if self.first_pass_complete:
                            self._check_for_missing_items()
                    
                    # Start going forward again
                    self.direction = 'forward'
                    self.movement_phase = 'going_down'
                    
            elif self.movement_phase == 'going_up':
                # Just finished going up, now go down
                self.movement_phase = 'going_down'
                
            return
        
        # Move toward target
        move_distance = self.speed * dt
        if move_distance > distance:
            move_distance = distance
        
        # Normalize direction and move ONLY in Y direction when in aisle
        aisle = AISLES[self.current_aisle]
        
        if abs(self.y - CROSS_AISLE_Y) > 50:
            # In vertical part of aisle - lock X, move only Y
            self.x = aisle['x']  # Lock to exact aisle center
            self.y += (dy / abs(dy)) * move_distance if dy != 0 else 0
        else:
            # In cross aisle - can move horizontally
            self.x += (dx / distance) * move_distance
            self.y += (dy / distance) * move_distance
        
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
        """
        Detect items within 1.5m range of employee position
        Only send to backend when item is first detected or status changes
        This prevents redundant database writes and query limit issues
        """
        detections = []
        
        # Find all items within detection range
        for item in self.items:
            distance = math.sqrt((self.x - item.x)**2 + (self.y - item.y)**2)
            
            if distance < self.detection_range:
                # Item is within range - determine current status
                current_status = "missing" if item.missing else "present"
                
                # Only send to backend if status changed or first detection
                if item.reported_status != current_status:
                    detections.append({
                        "product_id": item.product_id,
                        "product_name": item.product_name,
                        "x_position": item.x,
                        "y_position": item.y,
                        "status": current_status
                    })
                    
                    # Update tracking
                    item.reported_status = current_status
                    item.detected = True
                    item.last_seen = datetime.utcnow()
        
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

def fetch_anchors_from_backend(api_url):
    """Fetch anchor configuration from backend API"""
    try:
        import requests
        response = requests.get(f"{api_url}/anchors", timeout=5)
        if response.status_code == 200:
            anchors_data = response.json()
            # Filter only active anchors
            active_anchors = [a for a in anchors_data if a.get('is_active', True)]
            
            if len(active_anchors) < 2:
                print(f"⚠️  Warning: Only {len(active_anchors)} active anchor(s) found. Need at least 2 for positioning.")
                return None
            
            # Extract positions and MAC addresses
            anchor_positions = [(a['x_position'], a['y_position']) for a in active_anchors]
            anchor_macs = [a['mac_address'] for a in active_anchors]
            
            print(f"✅ Loaded {len(active_anchors)} anchors from backend:")
            for i, anchor in enumerate(active_anchors):
                print(f"   {anchor['name']}: {anchor['mac_address']} @ ({anchor['x_position']:.0f}, {anchor['y_position']:.0f})")
            
            return anchor_positions, anchor_macs
        else:
            print(f"⚠️  Backend returned status {response.status_code}")
            return None
    except Exception as e:
        print(f"⚠️  Could not fetch anchors from backend: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="ESP32 UWB Simulator")
    parser.add_argument("--broker", default=MQTT_BROKER, help="MQTT broker address")
    parser.add_argument("--port", type=int, default=MQTT_PORT, help="MQTT broker port")
    parser.add_argument("--interval", type=float, default=UPDATE_INTERVAL, help="Update interval in seconds")
    parser.add_argument("--api", default="http://localhost:8000", help="Backend API URL")
    args = parser.parse_args()
    
    # Fetch anchor configuration from backend
    print("📡 Fetching anchor configuration from backend...")
    anchor_config = fetch_anchors_from_backend(args.api)
    
    if anchor_config is None:
        print("\n❌ ERROR: Could not load anchors from backend.")
        print("   Please configure anchors in the web interface first:")
        print("   1. Open http://localhost:3000")
        print("   2. Click 'Setup Mode'")
        print("   3. Place at least 2 anchors on the map")
        print("   4. Click 'Finish Setup'")
        print("   5. Run this simulator again\n")
        return
    
    anchor_positions, anchor_macs = anchor_config
    
    # Use the MAC addresses from backend
    global ANCHORS
    ANCHORS = anchor_macs
    
    print("\n🚀 ESP32 UWB Simulator")
    print("=" * 50)
    print(f"MQTT Broker: {args.broker}:{args.port}")
    print(f"Backend API: {args.api}")
    print(f"Publishing to: {TOPIC_DATA}")
    print(f"Update interval: {args.interval}s")
    print(f"Store size: {STORE_WIDTH}x{STORE_HEIGHT} cm")
    print(f"Anchors configured: {len(ANCHORS)}")
    print("=" * 50)
    
    # Initialize simulator
    tag_sim = TagSimulator(anchor_positions)
    
    # Setup MQTT client
    userdata = {'running': True}  # Auto-start enabled
    client = mqtt.Client(userdata=userdata)
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(args.broker, args.port, 60)
        client.loop_start()
        
        print("\n✅ Simulator started automatically")
        print(f"   Employee will walk through all aisles following predefined path")
        print(f"   Movement is INDEPENDENT of anchor positions (simulates real behavior)")
        print(f"   View live tracking: http://localhost:3000")
        print(f"   Send 'STOP' to pause: mosquitto_pub -h {args.broker} -t {TOPIC_CONTROL} -m 'STOP'\n")
        
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
                    aisle_info = f"Aisle {tag_sim.current_aisle + 1}" if tag_sim.current_aisle < len(AISLES) else "Transit"
                    
                    # Display direction based on movement phase
                    if tag_sim.movement_phase == 'going_down':
                        direction_info = "↓ Down"
                    elif tag_sim.movement_phase == 'going_up':
                        direction_info = "↑ Up"
                    else:
                        direction_info = "→ Cross"
                    
                    pass_info = f"Pass {tag_sim.pass_count + 1}"
                    dir_arrow = "→" if tag_sim.direction == 'forward' else "←"
                    
                    # Only print every 5th update to reduce console spam
                    if packet_count % 5 == 0:
                        print(f"📤 [{packet_count}] {pass_info} {dir_arrow} | {aisle_info} {direction_info} - Position: ({tag_sim.x:.0f}, {tag_sim.y:.0f})")
                        if detections:
                            missing_count = sum(1 for d in detections if d.get('status') == 'missing')
                            present_count = len(detections) - missing_count
                            if missing_count > 0:
                                print(f"   🏷️  Detected: {present_count} present, ⚠️  {missing_count} missing")
                            else:
                                print(f"   🏷️  Detected: {len(detections)} items")
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
