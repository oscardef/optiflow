#!/bin/bash

echo "📡 ESP32 Simulator Helper"
echo "=========================================="
echo ""
echo "This script helps you run the ESP32 simulator"
echo ""
echo "Make sure Docker containers are running first!"
echo "If not, run: ./start_system.sh"
echo ""
echo "=========================================="
echo ""

# Check if paho-mqtt is installed
if ! python3 -c "import paho.mqtt.client" 2>/dev/null; then
    echo "❌ paho-mqtt not installed"
    echo "Installing now..."
    pip3 install paho-mqtt
    echo ""
fi

# Get MQTT broker IP (from docker network)
MQTT_HOST=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' optiflow-mqtt-1 2>/dev/null)

if [ -z "$MQTT_HOST" ]; then
    echo "⚠️  Could not detect MQTT broker IP"
    echo "Using localhost (make sure Docker is running)"
    MQTT_HOST="localhost"
fi

echo "✅ MQTT Broker: $MQTT_HOST"
echo ""
echo "Starting simulator in 3 seconds..."
echo "To stop: Press Ctrl+C"
echo ""
sleep 3

python3 esp32_simulator.py
