import json
import os
import time
import requests
import paho.mqtt.client as mqtt

# Configuration from environment variables
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "store/aisle1")
API_URL = os.getenv("API_URL", "http://localhost:8000")

print(f"🔌 MQTT Bridge starting...")
print(f"   Broker: {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
print(f"   Topic: {MQTT_TOPIC}")
print(f"   API: {API_URL}")

def on_connect(client, userdata, flags, rc):
    """Callback when connected to MQTT broker"""
    if rc == 0:
        print(f"✅ Connected to MQTT broker")
        client.subscribe(MQTT_TOPIC)
        print(f"📡 Subscribed to topic: {MQTT_TOPIC}")
    else:
        print(f"❌ Failed to connect to MQTT broker. Return code: {rc}")

def on_message(client, userdata, msg):
    """Callback when message received from MQTT"""
    try:
        # Decode and parse the message
        payload = msg.payload.decode('utf-8')
        print(f"\n📥 Received message on {msg.topic}")
        print(f"   Full Payload: {payload}")
        
        data = json.loads(payload)
        
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
        else:
            print(f"⚠️  API returned status {response.status_code}: {response.text}")
    
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON received: {e}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to forward data to API: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def on_disconnect(client, userdata, rc):
    """Callback when disconnected from MQTT broker"""
    if rc != 0:
        print(f"⚠️  Unexpected disconnection. Reconnecting...")

def main():
    """Main function to start MQTT bridge"""
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
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    # Connect to broker
    try:
        client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
        
        # Start listening loop
        print("🎧 MQTT Bridge running. Press Ctrl+C to stop.")
        client.loop_forever()
    
    except KeyboardInterrupt:
        print("\n🛑 Shutting down MQTT bridge...")
        client.disconnect()
    except Exception as e:
        print(f"❌ Fatal error: {e}")

if __name__ == "__main__":
    main()
