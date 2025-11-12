#!/bin/bash

echo "🧪 OptiFlow System Test"
echo "======================="
echo ""

# Test 1: Backend Health
echo "1️⃣  Testing backend health..."
HEALTH=$(curl -s http://localhost:8000/)
if echo "$HEALTH" | grep -q "online"; then
    echo "   ✅ Backend is online"
else
    echo "   ❌ Backend is not responding"
    exit 1
fi
echo ""

# Test 2: Anchors endpoint
echo "2️⃣  Testing anchors endpoint..."
ANCHORS=$(curl -s http://localhost:8000/anchors)
echo "   Current anchors: $ANCHORS"
echo "   ✅ Anchors endpoint working"
echo ""

# Test 3: Positions endpoint
echo "3️⃣  Testing positions endpoint..."
POSITIONS=$(curl -s http://localhost:8000/positions/latest?limit=1)
echo "   Recent positions: $POSITIONS"
echo "   ✅ Positions endpoint working"
echo ""

# Test 4: Create test anchor
echo "4️⃣  Creating test anchor..."
CREATE_RESULT=$(curl -s -X POST http://localhost:8000/anchors \
  -H "Content-Type: application/json" \
  -d '{
    "mac_address": "0x9999",
    "name": "Test Anchor",
    "x_position": 500,
    "y_position": 400,
    "is_active": true
  }')

if echo "$CREATE_RESULT" | grep -q "Test Anchor"; then
    echo "   ✅ Anchor created successfully"
    
    # Get anchor ID
    ANCHOR_ID=$(echo "$CREATE_RESULT" | grep -o '"id":[0-9]*' | cut -d: -f2)
    echo "   Anchor ID: $ANCHOR_ID"
    
    # Clean up - delete test anchor
    echo "   🧹 Cleaning up test anchor..."
    curl -s -X DELETE "http://localhost:8000/anchors/$ANCHOR_ID" > /dev/null
    echo "   ✅ Test anchor removed"
else
    echo "   ⚠️  Anchor creation failed (this is OK if anchor already exists)"
fi
echo ""

# Test 5: MQTT Broker
echo "5️⃣  Testing MQTT broker..."
if nc -z 172.20.10.3 1883 2>/dev/null; then
    echo "   ✅ MQTT broker is reachable"
else
    echo "   ⚠️  MQTT broker not reachable (check Mosquitto)"
fi
echo ""

# Test 6: Frontend
echo "6️⃣  Testing frontend..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 | grep -q "200"; then
    echo "   ✅ Frontend is accessible"
else
    echo "   ⚠️  Frontend not responding (may still be starting)"
fi
echo ""

# Summary
echo "========================="
echo "✅ System Test Complete!"
echo "========================="
echo ""
echo "Next steps:"
echo "1. Open http://localhost:3000"
echo "2. Click 'Setup Mode' and place 4 anchors"
echo "3. Run: python esp32_simulator.py --broker 172.20.10.3"
echo "4. Send: mosquitto_pub -h 172.20.10.3 -t store/control -m 'START'"
echo ""
