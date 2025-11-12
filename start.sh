#!/bin/bash

# OptiFlow Quick Start Script
# This script helps you start the entire system with one command

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "🚀 OptiFlow Quick Start"
echo "======================================"
echo ""

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is in use
port_in_use() {
    lsof -i ":$1" >/dev/null 2>&1
}

# Step 1: Check prerequisites
echo "📋 Checking prerequisites..."

if ! command_exists docker; then
    echo -e "${RED}❌ Docker not found${NC}"
    echo "Please install Docker Desktop and add it to your PATH:"
    echo "  echo 'export PATH=\"/Applications/Docker.app/Contents/Resources/bin:\$PATH\"' >> ~/.zshrc"
    echo "  source ~/.zshrc"
    exit 1
fi

if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running${NC}"
    echo "Please start Docker Desktop first."
    exit 1
fi

if ! command_exists brew; then
    echo -e "${YELLOW}⚠️  Homebrew not found (needed for Mosquitto MQTT)${NC}"
    echo "Install from: https://brew.sh"
    exit 1
fi

if ! command_exists python3; then
    echo -e "${RED}❌ Python 3 not found${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites OK${NC}"
echo ""

# Step 2: Check/Start Mosquitto
echo "📡 Checking MQTT broker (Mosquitto)..."

if ! command_exists mosquitto; then
    echo -e "${YELLOW}⚠️  Mosquitto not installed${NC}"
    echo "Installing Mosquitto..."
    brew install mosquitto
fi

if ! brew services list | grep mosquitto | grep -q started; then
    echo "Starting Mosquitto..."
    brew services start mosquitto
    sleep 2
fi

echo -e "${GREEN}✅ Mosquitto running${NC}"
echo ""

# Step 3: Install Python dependencies
echo "🐍 Checking Python dependencies..."

if ! python3 -c "import paho.mqtt.client" 2>/dev/null; then
    echo "Installing paho-mqtt..."
    pip3 install paho-mqtt
fi

echo -e "${GREEN}✅ Python dependencies OK${NC}"
echo ""

# Step 4: Start Docker containers
echo "🐳 Starting Docker containers..."

docker compose up -d

# Wait for services
echo "⏳ Waiting for services to start..."
sleep 5

# Check containers
BACKEND_STATUS=$(docker compose ps | grep optiflow-backend | grep -c "Up" || echo "0")
FRONTEND_STATUS=$(docker compose ps | grep optiflow-frontend | grep -c "Up" || echo "0")

if [ "$BACKEND_STATUS" -eq "0" ] || [ "$FRONTEND_STATUS" -eq "0" ]; then
    echo -e "${RED}❌ Some containers failed to start${NC}"
    echo "Run 'docker compose logs' to see errors"
    exit 1
fi

echo -e "${GREEN}✅ Docker containers running${NC}"
echo ""

# Step 5: Test backend
echo "🧪 Testing backend..."
sleep 2

if curl -s http://localhost:8000/ | grep -q "online"; then
    echo -e "${GREEN}✅ Backend responding${NC}"
else
    echo -e "${YELLOW}⚠️  Backend not responding yet (may need more time)${NC}"
fi
echo ""

# Summary
echo "======================================"
echo -e "${GREEN}✅ System is ready!${NC}"
echo "======================================"
echo ""
echo "🌐 Frontend:  http://localhost:3000"
echo "🔧 Backend:   http://localhost:8000"
echo "🔧 API Docs:  http://localhost:8000/docs"
echo ""
echo -e "${BLUE}📍 Next Steps:${NC}"
echo ""
echo "1. Open http://localhost:3000 in your browser"
echo "2. Click 'Setup Mode' and place 3-4 anchors on the map"
echo "3. In a new terminal, run the simulator:"
echo -e "   ${YELLOW}python3 esp32_simulator.py${NC}"
echo "4. In another terminal, send START command:"
echo -e "   ${YELLOW}mosquitto_pub -h localhost -t 'store/control' -m 'START'${NC}"
echo ""
echo "🛑 To stop: ${YELLOW}docker compose down${NC}"
echo ""
