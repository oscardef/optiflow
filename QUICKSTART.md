# ⚡ OptiFlow Quick Start Checklist

Use this checklist to get OptiFlow running from scratch.

## ✅ Pre-Setup (One-Time Only)

### Install Prerequisites

- [ ] **Docker Desktop** installed and running
- [ ] **Homebrew** installed (`/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`)
- [ ] **Arduino IDE** installed with ESP32 board support
- [ ] **VS Code** (optional, for development)

### Install Mosquitto

```bash
# Install
brew install mosquitto

# Configure - add these lines to config file:
sudo nano /opt/homebrew/etc/mosquitto/mosquitto.conf
```

Add at end:
```
listener 1883 0.0.0.0
allow_anonymous true
```

Save and exit (Ctrl+X, Y, Enter)

## 🚀 Daily Startup (Run Every Time)

### 1. Terminal: Start Services

```bash
# Navigate to project
cd /Users/oscar/Documents/GitHub/optiflow

# Start Mosquitto (if not running)
brew services start mosquitto

# Start Docker services
docker compose up -d

# Wait 10 seconds for services to initialize
sleep 10

# Verify all services running
docker compose ps
```

Expected: All services show "Up" status ✅

### 2. Hardware: Configure Anchors (First Time Only per Anchor)

For each DWM3001CDK anchor board:

```
1. Connect USB
2. Open Serial Monitor (115200 baud)
3. Type: INITR [Enter]
4. Type: RESPF [Enter]
5. Type: SAVE [Enter]
6. Disconnect USB
7. Power anchor (USB or battery)
8. Repeat for remaining anchors
```

### 3. Arduino: Upload ESP32 Firmware

```
1. Open: UART_UWB_TEST/esp32_dwm3001_cli/esp32_uwb_simple_mqtt.ino
2. Select Board: "ESP32S3 Dev Module"
3. Verify WiFi settings (lines 32-34):
   - ssid = "Oscar" (your hotspot)
   - password = "password"
   - mqtt_server = "172.20.10.3" (your Mac IP)
4. Click Upload
5. Open Serial Monitor (115200 baud)
```

Expected output:
```
[WiFi] Connected!
[WiFi] IP: 172.20.10.4
[MQTT] Connecting...connected!
[READY] Waiting for START signal...
```

### 4. Terminal: Send START Signal

```bash
mosquitto_pub -h 172.20.10.3 -t store/control -m 'START'
```

Expected in Serial Monitor:
```
[CONTROL] START received!
[MQTT] ✓ Published to store/aisle1
```

### 5. Browser: Open Dashboard

```
Open: http://localhost:3000
```

Expected: Dashboard showing live UWB measurements ✅

---

## 🎯 Quick Verification Tests

Run these to verify everything is working:

### Test 1: Backend Health
```bash
curl http://localhost:8000
```
✅ Should return: `{"status":"online"...}`

### Test 2: MQTT Bridge
```bash
docker logs optiflow-mqtt-bridge --tail 5
```
✅ Should show: `✅ Connected to MQTT broker`

### Test 3: Database Has Data
```bash
docker compose exec -T postgres psql -U optiflow -d optiflow -c \
  "SELECT COUNT(*) FROM uwb_measurements;"
```
✅ Should return: count > 0

### Test 4: API Returns Data
```bash
curl -s 'http://localhost:8000/data/latest?limit=1'
```
✅ Should return JSON with measurements

### Test 5: ESP32 Publishing
Check Serial Monitor for:
```
[MQTT] ✓ Published to store/aisle1 - Session #X
```
✅ Should appear every ~200ms

---

## 📊 What You Should See

### Serial Monitor (ESP32)
```
=== UWB Session #42 ===
Timestamp: 2024-11-12T00:05:30
Measurements: 1
  - 0x0001 @ 62.0cm (SUCCESS)

[MQTT] ✓ Published to store/aisle1 - Session #42 (1 measurements)
```

### Dashboard (Browser)
- **System Stats**: Growing count of measurements
- **Recent UWB Measurements**: Table with live distance data
- **Status**: Green "Connected" indicator

### MQTT Bridge Logs
```bash
docker logs -f optiflow-mqtt-bridge
```
Output:
```
📥 Received message on store/aisle1
✅ Data forwarded successfully:
   UWB measurements stored: 1
```

---

## 🛑 Daily Shutdown

```bash
# Stop Docker services
docker compose down

# Stop Mosquitto (optional - can leave running)
brew services stop mosquitto

# Unplug ESP32 or press reset
```

---

## 🔄 Quick Restart (After Errors)

```bash
# Full restart
docker compose down
brew services restart mosquitto
sleep 5
docker compose up -d
sleep 10

# Re-upload ESP32 firmware
# Send START signal again
mosquitto_pub -h 172.20.10.3 -t store/control -m 'START'
```

---

## ⚠️ Common Issues

| Problem | Quick Fix |
|---------|-----------|
| "Network unreachable" | `brew services restart mosquitto` |
| Dashboard shows "Disconnected" | `docker compose restart backend` |
| ESP32 won't connect | Check WiFi hotspot is active |
| No measurements (0) | Power on anchor boards |
| Port conflict (8000/3000) | `lsof -i :PORT` then kill process |

---

## 🎓 Learning Path

Day 1: Get system running (this checklist)
Day 2: Explore [TESTING.md](TESTING.md) - Advanced testing
Day 3: Read [ARCHITECTURE.md](ARCHITECTURE.md) - System design
Day 4: Modify code and experiment!

---

## 📞 Need Help?

1. **Check logs**: `docker compose logs`
2. **Check ESP32**: Serial Monitor at 115200 baud
3. **Verify network**: All devices on same WiFi
4. **Read troubleshooting**: See README.md § Troubleshooting

---

## ✨ Success Criteria

You know it's working when:

- ✅ Dashboard shows green "Connected"
- ✅ Dashboard auto-updates every 2 seconds
- ✅ ESP32 Serial Monitor shows MQTT publishes
- ✅ Distance values change as you move the tag
- ✅ Database count increases: `docker compose exec -T postgres psql -U optiflow -d optiflow -c "SELECT COUNT(*) FROM uwb_measurements;"`

**If all checks pass: 🎉 Congratulations! Your OptiFlow system is live!**
