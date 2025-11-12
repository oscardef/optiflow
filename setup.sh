#!/bin/bash

echo "🚀 Setting up OptiFlow..."
echo ""

# Install backend dependencies
echo "📦 Installing backend dependencies..."
cd backend
pip install -r requirements.txt
cd ..

# Install frontend dependencies
echo "📦 Installing frontend dependencies (Tailwind, etc.)..."
cd frontend
npm install
cd ..

# Install simulator dependencies
echo "📦 Installing simulator dependencies..."
pip install paho-mqtt

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Start Docker services: docker compose up -d"
echo "2. Start frontend: cd frontend && npm run dev"
echo "3. Run simulator: python esp32_simulator.py"
echo "4. Send START signal: mosquitto_pub -h 172.20.10.3 -t store/control -m 'START'"
echo ""
echo "Open http://localhost:3000 in your browser"
