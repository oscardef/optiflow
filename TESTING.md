# OptiFlow Testing Guide

## 🧪 Complete System Test

### 1. Start the Backend Stack

```bash
cd /Users/oscar/Documents/GitHub/optiflow
docker compose up -d
```

Verify all services are running:
```bash
docker compose ps
```

Expected output:
```
NAME                     IMAGE                  STATUS      PORTS
optiflow-backend         optiflow-backend       Up          0.0.0.0:8000->8000/tcp
optiflow-db              postgres:15-alpine     Up          0.0.0.0:5432->5432/tcp
optiflow-frontend        optiflow-frontend      Up          0.0.0.0:3000->3000/tcp
optiflow-mqtt-bridge     optiflow-mqtt_bridge   Up
```

### 2. Check Services

**Backend Health:**
```bash
curl http://localhost:8000
# Should return: {"status":"online","service":"OptiFlow Backend"}
```

**Frontend:**
Open browser to: http://localhost:3000

**MQTT Bridge:**
```bash
docker logs optiflow-mqtt-bridge --tail 10
# Should show: ✅ Connected to MQTT broker
```

### 3. Test Message Flow

**Send a test UWB message:**
```bash
mosquitto_pub -h 172.20.10.3 -t store/aisle1 -m '{
  "timestamp": "2024-11-12T16:00:00",
  "detections": [],
  "uwb_measurements": [
    {"mac_address": "0x1234", "distance_cm": 150.5, "status": "SUCCESS"},
    {"mac_address": "0x5678", "distance_cm": 230.8, "status": "SUCCESS"}
  ]
}'
```

**Verify it was received:**
```bash
# Check MQTT bridge logs
docker logs optiflow-mqtt-bridge --tail 5

# Check database
docker compose exec -T postgres psql -U optiflow -d optiflow -c \
  "SELECT * FROM uwb_measurements ORDER BY id DESC LIMIT 5;"

# Check API
curl -s 'http://localhost:8000/data/latest?limit=5' | python3 -m json.tool
```

**Check frontend:**
- Refresh http://localhost:3000
- Should see your test measurements in the "Recent UWB Measurements" table

### 4. Upload ESP32 Firmware

**File:** `UART_UWB_TEST/esp32_dwm3001_cli/esp32_uwb_simple_mqtt.ino`

**Arduino IDE Settings:**
- Board: ESP32S3 Dev Module
- Upload Speed: 921600
- USB CDC On Boot: Enabled

**Upload and Monitor:**
1. Upload sketch to ESP32
2. Open Serial Monitor (115200 baud)
3. Expected output:
   ```
   === ESP32-S3 + DWM3001CDK + MQTT ===
   [UART] DWM3001CDK Ready
   [WiFi] Connecting...
   [WiFi] Connected!
   [WiFi] IP: 172.20.10.4
   [MQTT] Connecting...connected!
   [MQTT] Published ESP32_READY
   [READY] Waiting for START signal...
   ```

### 5. Start Data Collection

**From Python or manually:**
```bash
mosquitto_pub -h 172.20.10.3 -t store/control -m 'START'
```

**Or use the old Python script:**
```python
import paho.mqtt.client as mqtt
client = mqtt.Client()
client.connect("172.20.10.3", 1883, 60)
client.publish("store/control", "START")
```

**Watch ESP32 Serial Monitor:**
- Should see: `[CONTROL] START received!`
- Then UWB sessions appearing every 200ms (if DWM3001CDK is ranging)

### 6. Monitor Live Data

**Watch MQTT bridge:**
```bash
docker logs -f optiflow-mqtt-bridge
```

**Watch backend logs:**
```bash
docker logs -f optiflow-backend
```

**View dashboard:**
- Open http://localhost:3000
- Should auto-refresh every 2 seconds
- See real-time UWB measurements

### 7. Query Data

**Get statistics:**
```bash
curl -s http://localhost:8000/stats | python3 -m json.tool
```

**Get latest data:**
```bash
curl -s 'http://localhost:8000/data/latest?limit=10' | python3 -m json.tool
```

**Direct database query:**
```bash
docker compose exec -T postgres psql -U optiflow -d optiflow -c "
  SELECT 
    timestamp, 
    mac_address, 
    distance_cm, 
    status 
  FROM uwb_measurements 
  ORDER BY timestamp DESC 
  LIMIT 10;
"
```

## 🐛 Troubleshooting

### MQTT Bridge keeps disconnecting
```bash
# Check Mosquitto is running
ps aux | grep mosquitto | grep -v grep

# Restart Mosquitto
brew services restart mosquitto

# Check Mosquitto config
cat /opt/homebrew/etc/mosquitto/mosquitto.conf
# Should have:
#   listener 1883 0.0.0.0
#   allow_anonymous true
```

### ESP32 not connecting to WiFi
- Check SSID/password in firmware
- Verify hotspot "Oscar" is active
- Check ESP32 IP: should be 172.20.10.x

### No UWB data from ESP32
- Check DWM3001CDK wiring:
  - GPIO17 → P0.08
  - GPIO18 → P0.06
  - GND → GND
- Power on anchor boards
- Send START signal
- Check DWM3001CDK is in INITF mode:
  ```
  STAT  (in Serial Monitor)
  ```

### Frontend shows "Disconnected"
```bash
# Check backend is running
curl http://localhost:8000

# Check CORS is enabled (should be by default)
docker logs optiflow-backend | grep CORS
```

### Database errors
```bash
# Restart everything
docker compose down
docker compose up -d

# Check database health
docker compose exec postgres pg_isready -U optiflow
```

## 📊 Expected Data Format

**ESP32 publishes to `store/aisle1`:**
```json
{
  "timestamp": "2024-11-12T15:30:45",
  "detections": [],
  "uwb_measurements": [
    {
      "mac_address": "0x1234",
      "distance_cm": 150.5,
      "status": "SUCCESS"
    }
  ]
}
```

**Backend stores in PostgreSQL:**
- Table: `uwb_measurements`
- Fields: `id`, `timestamp`, `mac_address`, `distance_cm`, `status`

**Frontend displays:**
- Recent UWB Measurements table
- Auto-refreshes every 2 seconds
- Shows MAC address, distance, and status

## 🎯 Quick Test Checklist

- [ ] Backend responds at http://localhost:8000
- [ ] Frontend loads at http://localhost:3000
- [ ] Mosquitto is running
- [ ] MQTT bridge connected
- [ ] Test message flows through
- [ ] Data appears in database
- [ ] Data appears in frontend
- [ ] ESP32 connects to WiFi
- [ ] ESP32 connects to MQTT
- [ ] ESP32 receives START signal
- [ ] UWB data flows to backend
- [ ] Dashboard shows real-time data
