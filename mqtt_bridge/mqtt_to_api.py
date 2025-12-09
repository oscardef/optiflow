import json
import os
import signal
import sys
import time
import requests
import paho.mqtt.client as mqtt
from datetime import datetime

# Configuration from environment variables
MQTT_BROKER_HOST = os.environ.get("MQTT_BROKER", os.environ.get("MQTT_BROKER_HOST", "localhost"))
MQTT_BROKER_PORT = int(os.environ.get("MQTT_PORT", os.environ.get("MQTT_BROKER_PORT", "1883")))
API_URL = os.environ["API_URL"]

# Mode-aware topic configuration
TOPIC_SIMULATION = "store/simulation"
TOPIC_PRODUCTION = "store/production"

# Cache for current system mode
_cached_mode = None
_last_mode_check = 0
MODE_CHECK_INTERVAL = 5  # seconds

print(f"🔌 MQTT Bridge starting...")
print(f"   Broker: {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
print(f"   Mode-aware topics: {TOPIC_SIMULATION}, {TOPIC_PRODUCTION}")
print(f"   API: {API_URL}")


def transform_hardware_to_backend(hardware_data: dict) -> dict:
    """
    Transform hardware JSON format to backend API format.
    
    Hardware format:
    {
        "polling_cycle": 1,
        "timestamp": 123456,  # milliseconds since boot
        "uwb": {
            "n_anchors": 2,
            "anchors": [
                {"mac_address": "0xABCD", "average_distance_cm": 150.5, "measurements": 3, "total_sessions": 5}
            ]
        },
        "rfid": {
            "tag_count": 2,
            "tags": [
                {"epc": "E200001234567890ABCD", "rssi_dbm": -45, "pc": "3000"}
            ]
        }
    }
    
    Backend format:
    {
        "timestamp": "2025-12-02T13:00:00Z",
        "detections": [
            {"product_id": "RFID001", "product_name": "Unknown", "status": "present"}
        ],
        "uwb_measurements": [
            {"mac_address": "0x0001", "distance_cm": 150.5, "status": "0x01"}
        ]
    }
    """
    # Generate ISO timestamp
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    # Transform RFID tags to detections
    detections = []
    rfid_section = hardware_data.get("rfid", {})
    tags = rfid_section.get("tags", [])
    
    for tag in tags:
        epc = tag.get("epc", "")
        rssi = tag.get("rssi_dbm", 0)
        
        # Use EPC as product_id (this is the RFID tag identifier)
        detections.append({
            "product_id": epc,
            "product_name": f"Item-{epc[-8:]}" if epc else "Unknown",
            "status": "present",
            "x_position": None,  # Will be calculated by triangulation
            "y_position": None,
            "rssi_dbm": rssi  # Extra field for signal strength
        })
    
    # Transform UWB anchors to measurements
    uwb_measurements = []
    uwb_section = hardware_data.get("uwb", {})
    
    # Handle case where UWB data is unavailable
    if uwb_section.get("available") is False:
        pass  # No UWB data
    else:
        anchors = uwb_section.get("anchors", [])
        
        for anchor in anchors:
            mac = anchor.get("mac_address", "")
            avg_distance = anchor.get("average_distance_cm")
            measurements_count = anchor.get("measurements", 0)
            
            # Only include anchors with valid measurements
            if avg_distance is not None and measurements_count > 0:
                uwb_measurements.append({
                    "mac_address": mac,
                    "distance_cm": avg_distance,
                    "status": "0x01"  # OK status
                })
    
    return {
        "timestamp": timestamp,
        "detections": detections,
        "uwb_measurements": uwb_measurements
    }


def get_system_mode() -> str:
    """Get current system mode from backend API with caching"""
    global _cached_mode, _last_mode_check
    
    current_time = time.time()
    
    # Use cache if recent
    if _cached_mode and (current_time - _last_mode_check) < MODE_CHECK_INTERVAL:
        return _cached_mode
    
    try:
        response = requests.get(f"{API_URL}/config/mode", timeout=2)
        if response.status_code == 200:
            mode = response.json().get('mode', 'SIMULATION')
            _cached_mode = mode
            _last_mode_check = current_time
            return mode
    except Exception as e:
        # If can't reach backend, return cached or default
        pass
    
    return _cached_mode or "SIMULATION"


def is_hardware_format(data: dict) -> bool:
    """Check if data is in hardware format (has rfid/uwb structure) vs simulation format"""
    return "rfid" in data or ("uwb" in data and "anchors" in data.get("uwb", {}))


def on_connect(client, userdata, flags, rc):
    """Callback when connected to MQTT broker"""
    if rc == 0:
        print(f"✅ Connected to MQTT broker")
        # Subscribe to both simulation and production topics
        # Messages will be filtered based on current mode in on_message
        client.subscribe(TOPIC_SIMULATION)
        client.subscribe(TOPIC_PRODUCTION)
        print(f"📡 Subscribed to topic: {TOPIC_SIMULATION}")
        print(f"📡 Subscribed to topic: {TOPIC_PRODUCTION}")
        print(f"🔍 Mode-aware filtering enabled: Messages filtered by system mode")
    else:
        print(f"❌ Failed to connect to MQTT broker. Return code: {rc}")

def on_message(client, userdata, msg):
    """Callback when message received from MQTT"""
    try:
        # Get current system mode
        current_mode = get_system_mode()
        
        # Decode and parse the message
        payload = msg.payload.decode('utf-8')
        print(f"\n📥 Received message on {msg.topic} (System mode: {current_mode})")
        
        # Filter messages based on mode
        if current_mode == "SIMULATION" and msg.topic != TOPIC_SIMULATION:
            print(f"   ⏭️  Skipping {msg.topic} message (system in SIMULATION mode, expecting {TOPIC_SIMULATION})")
            return
        elif current_mode == "PRODUCTION" and msg.topic != TOPIC_PRODUCTION:
            print(f"   ⏭️  Skipping {msg.topic} message (system in PRODUCTION mode, expecting {TOPIC_PRODUCTION})")
            return
        
        data = json.loads(payload)
        
        # Check if this is hardware format and transform if needed
        if is_hardware_format(data):
            print(f"   📟 Hardware format detected (polling_cycle: {data.get('polling_cycle', '?')})")
            
            # Log raw hardware data
            rfid_count = data.get("rfid", {}).get("tag_count", 0)
            uwb_section = data.get("uwb", {})
            uwb_count = uwb_section.get("n_anchors", 0) if uwb_section.get("available", True) else 0
            print(f"   🏷️  RFID tags: {rfid_count}")
            print(f"   📏 UWB anchors: {uwb_count}")
            
            # Transform to backend format
            data = transform_hardware_to_backend(data)
            print(f"   ✅ Transformed to backend format")
            print(f"      Detections: {len(data['detections'])}")
            print(f"      UWB measurements: {len(data['uwb_measurements'])}")
        else:
            print(f"   📤 Simulation format detected")
        
        # Forward to FastAPI backend
        response = requests.post(
            f"{API_URL}/data",
            json=data,
            timeout=5
        )
        
        if response.status_code == 201:
            result = response.json()
            print(f"✅ Data forwarded successfully:")
            print(f"   Detections stored: {result.get('detections_stored', 0)}")
            print(f"   UWB measurements stored: {result.get('uwb_measurements_stored', 0)}")
            if result.get('position_calculated'):
                pos = result.get('calculated_position', {})
                print(f"   📍 Position calculated: ({pos.get('x', '?')}, {pos.get('y', '?')})")
        else:
            print(f"⚠️  API returned status {response.status_code}: {response.text}")
    
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON received: {e}")
        print(f"   Raw payload: {msg.payload[:200]}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to forward data to API: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

def on_disconnect(client, userdata, rc):
    """Callback when disconnected from MQTT broker"""
    if rc != 0:
        print(f"⚠️  Unexpected disconnection from MQTT broker (code: {rc}). Will attempt to reconnect...")

# Global client reference for signal handling
mqtt_client = None

def signal_handler(signum, frame):
    """Handle shutdown signals (SIGTERM, SIGINT) for graceful cleanup"""
    signal_name = signal.Signals(signum).name
    print(f"\n🛑 Received {signal_name}, shutting down MQTT bridge...")
    if mqtt_client is not None:
        mqtt_client.disconnect()
        mqtt_client.loop_stop()
    sys.exit(0)

def main():
    """Main function to start MQTT bridge"""
    global mqtt_client
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Wait for backend to be ready
    print("⏳ Waiting for backend to be ready...")
    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get(f"{API_URL}/", timeout=2)
            if response.status_code == 200:
                print("✅ Backend is ready")
                break
        except requests.exceptions.RequestException:
            if i < max_retries - 1:
                time.sleep(2)
            else:
                print("⚠️  Backend not responding, but continuing anyway...")
    
    # Create MQTT client
    client = mqtt.Client(client_id="optiflow_bridge")
    mqtt_client = client  # Store reference for signal handler
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    # Connect to broker with retry logic
    while True:
        try:
            print(f"🔄 Attempting to connect to MQTT broker at {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}...")
            client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
            
            # Start listening loop
            print("🎧 MQTT Bridge running. Press Ctrl+C to stop.")
            client.loop_forever()
        
        except SystemExit:
            # Raised by signal handler, exit cleanly
            break
        except Exception as e:
            print(f"❌ MQTT broker connection failed: {e}")
            print(f"🔄 Retrying in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    main()
