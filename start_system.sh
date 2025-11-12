#!/bin/bash

echo "🚀 Starting OptiFlow System"
echo "=========================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop first."
    exit 1
fi

# Start Docker containers
echo "📦 Starting Docker containers..."
docker compose up -d

# Wait for containers to be ready
echo "⏳ Waiting for services to start..."
sleep 5

# Check if containers are running
echo ""
echo "📊 Container Status:"
docker compose ps

echo ""
echo "=========================================="
echo "✅ System is ready!"
echo ""
echo "🌐 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000"
echo "🔧 API Docs: http://localhost:8000/docs"
echo ""
echo "📡 To start the ESP32 simulator:"
echo "   1. In a new terminal, run: python3 esp32_simulator.py"
echo "   2. In another terminal, send START: mosquitto_pub -h localhost -t 'store/control' -m 'START'"
echo ""
echo "🛑 To stop: docker compose down"
echo "=========================================="
