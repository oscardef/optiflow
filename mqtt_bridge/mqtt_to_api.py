import json
import os
import signal
import sys
import time
import requests
import paho.mqtt.client as mqtt

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
        
        # Validate hardware format
        if "polling_cycle" not in data or "rfid" not in data or "uwb" not in data:
            print(f"   ❌ Invalid format - missing required fields (polling_cycle, rfid, uwb)")
            return
        
        print(f"   📟 Hardware format (polling_cycle: {data.get('polling_cycle', '?')})")
        
        # Log data
        rfid_count = data.get("rfid", {}).get("tag_count", 0)
        uwb_section = data.get("uwb", {})
        uwb_count = uwb_section.get("n_anchors", 0) if uwb_section.get("available", True) else 0
        print(f"   🏷️  RFID tags: {rfid_count}")
        print(f"   📏 UWB anchors: {uwb_count}")
        
        # Forward hardware format directly to FastAPI backend
        response = requests.post(
            f"{API_URL}/data",
            json=data,
            timeout=5
        )
        
        if response.status_code == 201:
            result = response.json()
            print(f"✅ Data forwarded successfully:")
            print(f"   RFID tags processed: {result.get('rfid_tags_processed', 0)}")
            print(f"   UWB measurements processed: {result.get('uwb_measurements_processed', 0)}")
            if result.get('position_calculated'):
                pos = result.get('position', {})
                print(f"   📍 Position calculated: ({pos.get('x', '?'):.1f}, {pos.get('y', '?'):.1f})")
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
