"""
OptiFlow Simulator - Main Entry Point
======================================
CLI interface for running the modular simulation system.

Usage:
    python -m simulation.main --mode realistic --speed 1.0
    python -m simulation.main --mode demo --api http://localhost:8000
"""

import argparse
import sys
import time
import json
from datetime import datetime
import paho.mqtt.client as mqtt
import requests

from .config import SimulationConfig, SimulationMode
from .inventory import InventoryGenerator, PRODUCT_CATALOG, Item, Product as ProductDataClass
from .shopper import ShopperSimulator
from .scanner import ScannerSimulator
from .analytics_tracker import AnalyticsTracker


def fetch_anchors_from_backend(api_url: str):
    """Fetch anchor configuration from backend API"""
    try:
        response = requests.get(f"{api_url}/anchors", timeout=5)
        
        if response.status_code == 200:
            anchors = response.json()
            active_anchors = [a for a in anchors if a.get('is_active', True)]
            
            if len(active_anchors) < 2:
                print(f"⚠️  Warning: Only {len(active_anchors)} active anchor(s) found. Need at least 2.")
                return None
            
            anchor_positions = [(a['x_position'], a['y_position']) for a in active_anchors]
            anchor_macs = [a['mac_address'] for a in active_anchors]
            
            print(f"✅ Loaded {len(active_anchors)} anchors from backend:")
            for anchor in active_anchors:
                print(f"   {anchor['name']}: {anchor['mac_address']} @ ({anchor['x_position']:.0f}, {anchor['y_position']:.0f})")
            
            return anchor_positions, anchor_macs
        else:
            print(f"⚠️  Backend returned status {response.status_code}")
            return None
    
    except Exception as e:
        print(f"⚠️  Could not fetch anchors from backend: {e}")
        return None


def on_connect(client, userdata, flags, rc):
    """MQTT connection callback"""
    if rc == 0:
        print(f"✅ Connected to MQTT broker at {userdata['config'].mqtt.broker}")
        client.subscribe(userdata['config'].mqtt.topic_control)
        userdata['mqtt_connected'] = True
    else:
        print(f"❌ Connection failed with code {rc}")
        userdata['mqtt_connected'] = False


def on_disconnect(client, userdata, rc):
    """MQTT disconnection callback"""
    userdata['mqtt_connected'] = False
    if rc != 0:
        print(f"⚠️  Lost connection to MQTT broker. Will attempt to reconnect...")


def on_message(client, userdata, msg):
    """MQTT message callback"""
    command = msg.payload.decode().strip().upper()
    if command == "STOP":
        userdata['running'] = False
        print("\n⏸️  Paused by MQTT command")
    elif command == "START":
        userdata['running'] = True
        print("\n▶️  Resumed by MQTT command")


def fetch_inventory_from_backend(api_url: str):
    """Fetch products and inventory items from backend database
    Returns tuple of (items_list, products_dict) or None if failed
    """
    try:
        # Fetch products
        print("   Fetching products...")
        products_response = requests.get(f"{api_url}/products", timeout=10)
        if products_response.status_code != 200:
            print(f"   ❌ Failed to fetch products: {products_response.status_code}")
            return None
        
        products_data = products_response.json()
        if not products_data:
            print("   ⚠️  No products found in database")
            print("   Please run: python -m simulation.generate_inventory --items 3000")
            return None
        
        print(f"   ✅ Loaded {len(products_data)} products")
        
        # Fetch inventory items
        print("   Fetching inventory items...")
        items_response = requests.get(f"{api_url}/items", timeout=10)
        if items_response.status_code != 200:
            print(f"   ❌ Failed to fetch items: {items_response.status_code}")
            return None
        
        items_data = items_response.json()
        if not items_data:
            print("   ⚠️  No inventory items found in database")
            print("   Please run: python -m simulation.generate_inventory --items 3000")
            return None
        
        print(f"   ✅ Loaded {len(items_data)} inventory items")
        
        # Build product lookup
        products_by_id = {p['id']: p for p in products_data}
        
        # Convert to simulation Item objects
        simulation_items = []
        for item_data in items_data:
            product_data = products_by_id.get(item_data['product_id'])
            if not product_data:
                continue
            
            # Create Product dataclass
            product = ProductDataClass(
                sku=product_data['sku'],
                name=product_data['name'],
                category=product_data['category']
            )
            
            # Create Item dataclass
            # Items always start as NOT missing in simulation
            # The simulation will detect them as "present" first, then they can go missing
            # based on the disappearance rate after the first pass
            x_pos = item_data.get('x_position') or 0.0
            y_pos = item_data.get('y_position') or 0.0
            
            item = Item(
                rfid_tag=item_data['rfid_tag'],
                product=product,
                x=x_pos if x_pos else 0.0,
                y=y_pos if y_pos else 0.0,
                detected=False,
                last_seen=None,
                missing=False,  # Always start as not missing - will be detected as present first
                reported_status=None
            )
            simulation_items.append(item)
        
        # Check if items need position assignment (all at 0,0 means positions were cleared)
        items_needing_positions = [i for i in simulation_items if i.x == 0.0 and i.y == 0.0]
        if items_needing_positions and len(items_needing_positions) > len(simulation_items) * 0.5:
            print(f"   ⚠️  {len(items_needing_positions)} items have no positions - will redistribute")
            return simulation_items, products_by_id, True  # Flag to redistribute
        
        print(f"   ✅ Converted {len(simulation_items)} items for simulation")
        return simulation_items, products_by_id, False
    
    except Exception as e:
        print(f"   ❌ Error fetching inventory: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    # Parse CLI arguments
    parser = argparse.ArgumentParser(description="OptiFlow Simulation System")
    parser.add_argument("--mode", choices=["demo", "realistic", "stress"], 
                       default="realistic", help="Simulation mode (default: realistic)")
    parser.add_argument("--speed", type=float, default=1.0, 
                       help="Speed multiplier (default: 1.0, range: 0.5-5.0)")
    parser.add_argument("--broker", default="172.20.10.3", 
                       help="MQTT broker address")
    parser.add_argument("--api", default="http://localhost:8000", 
                       help="Backend API URL")
    parser.add_argument("--interval", type=float, default=0.15, 
                       help="Update interval in seconds")
    parser.add_argument("--disappearance", type=float, default=0.015, 
                       help="Item disappearance rate (default: 0.015 = 1.5%%)")
    parser.add_argument("--analytics", action="store_true", 
                       help="Enable real-time analytics tracking")
    parser.add_argument("--snapshot-interval", type=int, default=3600, 
                       help="Seconds between snapshots (default: 3600 = 1 hour)")
    
    args = parser.parse_args()
    
    # Create configuration
    config = SimulationConfig(
        mode=SimulationMode(args.mode),
        speed_multiplier=max(0.5, min(5.0, args.speed)),
        api_url=args.api,
        disappearance_rate=max(0.0, min(0.1, args.disappearance))  # Clamp between 0% and 10%
    )
    config.mqtt.broker = args.broker
    config.tag.update_interval = args.interval
    
    # Print header
    print("\n" + "="*60)
    print("🚀 OptiFlow Simulation System v2.0")
    print("="*60)
    print(f"Mode: {config.mode.value.upper()}")
    print(f"Target items: {config.target_item_count}")
    print(f"Duplicates per SKU: {config.duplicates_per_sku[0]}-{config.duplicates_per_sku[1]}")
    print(f"Speed: {config.speed_multiplier}x")
    print(f"Disappearance rate: {config.disappearance_rate*100:.1f}%")
    print(f"MQTT Broker: {config.mqtt.broker}:{config.mqtt.port}")
    print(f"Backend API: {config.api_url}")
    print(f"Update interval: {config.tag.update_interval}s")
    print("="*60 + "\n")
    
    # Fetch anchor configuration
    print("📡 Fetching anchor configuration from backend...")
    anchor_config = fetch_anchors_from_backend(config.api_url)
    
    if anchor_config is None:
        print("\n❌ ERROR: Could not load anchors from backend.")
        print("   Please configure anchors in the web interface first:")
        print("   1. Open http://localhost:3000")
        print("   2. Configure at least 2 anchors")
        print("   3. Run this simulator again\n")
        return 1
    
    anchor_positions, anchor_macs = anchor_config
    
    # Fetch inventory from backend database
    print("\n📦 Loading inventory from database...")
    inventory_result = fetch_inventory_from_backend(config.api_url)
    
    if inventory_result is None:
        print("\n❌ ERROR: Could not load inventory from backend.")
        print("   Please generate inventory first:")
        print("   python -m simulation.generate_inventory --items 3000\n")
        return 1
    
    items, products_dict, needs_redistribution = inventory_result
    
    if len(items) == 0:
        print("\n❌ ERROR: No items found in inventory.")
        print("   Please generate inventory first:")
        print("   python -m simulation.generate_inventory --items 3000\n")
        return 1
    
    # Redistribute items if positions were cleared
    if needs_redistribution:
        print("\n🔄 Redistributing items to shelf positions...")
        from .inventory import InventoryGenerator
        generator = InventoryGenerator(config)
        generator.distribute_items(items)
        print(f"   ✅ Assigned shelf positions to {len(items)} items")
    
    print(f"\n✅ Loaded {len(items)} items from {len(products_dict)} products")
    
    # Initialize simulators
    print("\n🤖 Initializing simulators...")
    shopper = ShopperSimulator(config, items)
    scanner = ScannerSimulator(config, items, anchor_positions)
    
    # Initialize analytics tracker if enabled
    analytics_tracker = None
    if args.analytics:
        print("\n📊 Enabling real-time analytics tracking...")
        analytics_tracker = AnalyticsTracker(config.api_url, items, args.snapshot_interval)
        analytics_tracker.start()
    
    # Setup MQTT client
    userdata = {'running': True, 'config': config, 'mqtt_connected': False}
    client = mqtt.Client(userdata=userdata)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    # Enable automatic reconnection
    client.reconnect_delay_set(min_delay=1, max_delay=10)
    
    # Try to connect with retries
    max_retries = 5
    retry_delay = 2
    connected = False
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"\n🔌 Connecting to MQTT broker at {config.mqtt.broker}:{config.mqtt.port}... (Attempt {attempt}/{max_retries})")
            client.connect(config.mqtt.broker, config.mqtt.port, 60)
            client.loop_start()
            
            # Wait a bit to see if connection succeeds
            time.sleep(1)
            
            if userdata.get('mqtt_connected', False):
                connected = True
                break
            else:
                print(f"⚠️  Connection attempt {attempt} failed. Retrying in {retry_delay}s...")
                client.loop_stop()
                if attempt < max_retries:
                    time.sleep(retry_delay)
        except Exception as e:
            print(f"❌ Connection error: {e}")
            if attempt < max_retries:
                print(f"   Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
    
    if not connected:
        print("\n❌ ERROR: Could not connect to MQTT broker after multiple attempts.")
        print(f"   Please check:")
        print(f"   1. MQTT broker is running at {config.mqtt.broker}:{config.mqtt.port}")
        print(f"   2. You are connected to the correct WiFi network")
        print(f"   3. Firewall allows connection to port {config.mqtt.port}")
        print(f"\n   For iPhone hotspot users: Make sure you're connected to the hotspot network\n")
        return 1
    
    print("\n✅ Simulation started!")
    print(f"   View live tracking: http://localhost:3000")
    print(f"   MQTT will automatically reconnect if connection is lost")
    print(f"   Press Ctrl+C to quit\n")
    
    last_time = time.time()
    packet_count = 0
    mqtt_warn_shown = False
    
    try:
        while True:
            current_time = time.time()
            dt = current_time - last_time
            
            # Check MQTT connection status
            if not userdata.get('mqtt_connected', False) and not mqtt_warn_shown:
                print("⚠️  MQTT disconnected. Waiting for reconnection...")
                mqtt_warn_shown = True
            elif userdata.get('mqtt_connected', False) and mqtt_warn_shown:
                print("✅ MQTT reconnected successfully!")
                mqtt_warn_shown = False
            
            if userdata['running']:
                # Update shopper position
                shopper.update_position(dt)
                
                # Get current position
                x, y = shopper.get_position()
                
                # Scan for items and measure distances
                detections = scanner.get_rfid_detections(x, y)
                uwb_measurements = scanner.measure_distances(x, y, anchor_macs)
                
                # Build packet
                packet = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "detections": detections,
                    "uwb_measurements": uwb_measurements
                }
                
                # Send to backend API directly (in addition to MQTT)
                try:
                    # Send detections to API
                    if detections:
                        api_response = requests.post(
                            f"{config.api_url}/data/bulk",
                            json={"detections": detections},
                            timeout=2
                        )
                    
                    # Send UWB measurements to API
                    if uwb_measurements:
                        api_response = requests.post(
                            f"{config.api_url}/uwb/bulk",
                            json={"measurements": uwb_measurements},
                            timeout=2
                        )
                except Exception as e:
                    # Silently fail API calls to not spam console
                    pass
                
                # Publish to MQTT (for legacy support)
                payload = json.dumps(packet)
                result = client.publish(config.mqtt.topic_data, payload)
                
                if result.rc == mqtt.MQTT_ERR_SUCCESS or True:  # Count even if MQTT fails
                    packet_count += 1
                    
                    # Print status every 5th update
                    if packet_count % 5 == 0:
                        status = shopper.get_status_info()
                        print(f"📤 [{packet_count}] Pass {status['pass']} {status['direction_arrow']} | "
                              f"{status['aisle']} {status['movement']} - "
                              f"Position: ({status['position'][0]:.0f}, {status['position'][1]:.0f})")
                        
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
            time.sleep(config.tag.update_interval)
    
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping simulator...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Stop analytics tracker if running
        if analytics_tracker:
            analytics_tracker.stop()
        
        client.loop_stop()
        client.disconnect()
        print("👋 Disconnected\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
