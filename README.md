# OptiFlow - Real-time Inventory Tracking System

A wearable RFID + UWB positioning system for Decathlon employees to passively scan products and track their locations in real-time.

## � What It Does

OptiFlow tracks product locations in retail stores using:
- **UWB (Ultra-Wideband)** positioning for precise location tracking
- **RFID** for product identification (coming soon)
- **Real-time dashboard** showing live inventory positions and distances

## �🏗️ System Architecture

```
ESP32-S3 + DWM3001CDK (UWB Tag)
         ↓ WiFi/MQTT
    MacBook Mosquitto Broker
         ↓ MQTT Bridge
    FastAPI Backend
         ↓
    PostgreSQL Database
         ↑ REST API
    Next.js Dashboard
```

## 🚀 Quick Start (Simulator Mode - No Hardware Needed!)

### Simple 3-Step Setup

```bash
# 1. Start the system
./start_system.sh

# 2. In a new terminal, start the simulator
./start_simulator.sh

# 3. In another terminal, send the START command
mosquitto_pub -h localhost -t 'store/control' -m 'START'

# 4. Open your browser
# Frontend: http://localhost:3000
```

**What you'll see:**
- 📍 Click "Setup Mode" to place 3-4 anchors on the map
- 🏃 Watch the simulated tag walk through store aisles
- 📦 See items appear on the map (orange squares)
- ⚠️ Missing items turn red with alerts in sidebar
- 📊 Live position tracking with triangulation

**Common Issues:**

If `pip install paho` gives Python 2 error:
```bash
pip3 install paho-mqtt  # Use pip3 for Python 3
```

If Docker commands fail in new terminals:
```bash
# Add Docker to your PATH permanently
echo 'export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

---

## 🔧 Full Setup Guide (With Real Hardware)

### Prerequisites

- **macOS** with Homebrew installed
- **Docker Desktop** installed and running
- **Arduino IDE** with ESP32 support (for hardware mode)
- **Hardware** (optional): ESP32-S3, DWM3001CDK UWB modules (1 tag + 1-4 anchors)

---

## 📦 Step 1: Install Mosquitto MQTT Broker

```bash
# Install Mosquitto
brew install mosquitto

# Configure Mosquitto
sudo nano /opt/homebrew/etc/mosquitto/mosquitto.conf
```

Add these lines at the end:
```
listener 1883 0.0.0.0
allow_anonymous true
```

Start Mosquitto:
```bash
brew services start mosquitto

# Verify it's running
brew services info mosquitto
# Should show: Running: ✔
```

---

## 🐳 Step 2: Start Backend Services

```bash
cd optiflow

# Copy environment template
cp .env.example .env

# Start all services (PostgreSQL, FastAPI, Frontend, MQTT Bridge)
docker compose up -d

# Check all services are running
docker compose ps
```

Expected output:
```
NAME                     STATUS      PORTS
optiflow-backend         Up          0.0.0.0:8000->8000/tcp
optiflow-db              Up          0.0.0.0:5432->5432/tcp
optiflow-frontend        Up          0.0.0.0:3000->3000/tcp
optiflow-mqtt-bridge     Up
```

**Verify services:**
```bash
# Test backend
curl http://localhost:8000
# Should return: {"status":"online","service":"OptiFlow Backend"}

# Check MQTT bridge logs
docker logs optiflow-mqtt-bridge --tail 10
# Should show: ✅ Connected to MQTT broker

# Open dashboard in browser
open http://localhost:3000
```

---

## 🔧 Step 3: Configure DWM3001CDK Anchors

You need at least **1 anchor** (up to 4 for triangulation).

### For Each Anchor Board:

1. **Connect via USB** to your computer
2. **Open Serial Monitor** (115200 baud)
3. **Run these commands** (press Enter after each):

```bash
STAT           # Check current mode
INITR          # Initialize as Responder (anchor)
RESPF          # Start as anchor in active mode
SAVE           # Save configuration
RESET          # Restart the anchor
```

Expected output:
```
OK
UCI>RESPF
OK
```

4. **Disconnect USB** - anchor will run autonomously
5. **Power anchor** via USB or battery
6. **Repeat for all anchors** (you'll configure them with different MAC addresses automatically)

---

## 📱 Step 4: Upload ESP32 Firmware

### Hardware Setup

**Wiring (ESP32-S3 to DWM3001CDK Tag):**
```
ESP32 GPIO17 (TX)  →  DWM3001CDK P0.08 (RX)
ESP32 GPIO18 (RX)  →  DWM3001CDK P0.06 (TX)
ESP32 GND          →  DWM3001CDK GND
```

### Arduino IDE Configuration

1. **Open File:**
   ```
   UART_UWB_TEST/esp32_dwm3001_cli/esp32_uwb_simple_mqtt.ino
   ```

2. **Configure Board:**
   - **Board**: "ESP32S3 Dev Module"
   - **Upload Speed**: 921600
   - **USB CDC On Boot**: Enabled
   - **Port**: Select your ESP32's port

3. **Verify WiFi Settings** (lines 32-34):
   ```cpp
   const char* ssid = "Oscar";          // Your WiFi hotspot name
   const char* password = "password";    // Your WiFi password
   const char* mqtt_server = "172.20.10.3";  // Your MacBook IP
   ```
   
   💡 **Find your MacBook IP:**
   ```bash
   # If using hotspot:
   ipconfig getifaddr en0
   # or
   ipconfig getifaddr en1
   ```

4. **Upload Sketch** (Click Upload button)

5. **Open Serial Monitor** (115200 baud)

---

## ▶️ Step 5: Start Data Collection

### Watch ESP32 Serial Monitor

You should see:
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

### Configure DWM3001CDK Tag

In Serial Monitor, type:
```bash
STAT           # Check status
INITF          # Initialize as tag (if not already)
```

### Send START Signal

```bash
# From your terminal:
mosquitto_pub -h 172.20.10.3 -t store/control -m 'START'
```

**ESP32 Serial Monitor will show:**
```
[CONTROL] START received!
[SYSTEM] Now publishing UWB data

[UWB] >>> SESSION START <<<
[UWB] >>> SESSION END <<<

=== UWB Session #1 ===
Timestamp: 2024-11-12T00:00:02
Measurements: 1
  - 0x0001 @ 62.0cm (SUCCESS)

[MQTT] ✓ Published to store/aisle1 - Session #1 (1 measurements)
```

---

## 📊 Step 6: View Live Data

### 1. Dashboard (Best Option)
Open browser: **http://localhost:3000**

You'll see:
- **System Stats**: Total measurements collected
- **Recent UWB Measurements**: Live distance readings
- **Auto-refresh**: Updates every 2 seconds

### 2. Backend API
```bash
# Get latest data
curl -s 'http://localhost:8000/data/latest?limit=10' | python3 -m json.tool

# Get statistics
curl http://localhost:8000/stats
```

### 3. Database Query
```bash
docker compose exec -T postgres psql -U optiflow -d optiflow -c \
  "SELECT timestamp, mac_address, distance_cm FROM uwb_measurements ORDER BY timestamp DESC LIMIT 10;"
```

### 4. Live Logs
```bash
# Watch MQTT bridge
docker logs -f optiflow-mqtt-bridge

# Watch backend
docker logs -f optiflow-backend

# Watch all services
docker compose logs -f
```

---

## � Stopping the System

```bash
# Stop all Docker services
docker compose down

# Stop Mosquitto
brew services stop mosquitto

# Stop ESP32 (unplug or press reset)
```

---

## 🔄 Restarting the System

```bash
# 1. Start Mosquitto (if not running)
brew services start mosquitto

# 2. Start Docker services
docker compose up -d

# 3. Power on ESP32 (will auto-connect)

# 4. Send START signal
mosquitto_pub -h 172.20.10.3 -t store/control -m 'START'
```

---

## 📡 System Endpoints & Topics

### MQTT Topics

| Topic | Publisher | Purpose | Format |
|-------|-----------|---------|--------|
| `store/aisle1` | ESP32 | UWB measurement data | JSON |
| `store/control` | You/Backend | Control signals | `"START"` |
| `store/status` | ESP32 | Device status | `"ESP32_READY"` |

### HTTP Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `http://localhost:8000/` | GET | Backend health check |
| `http://localhost:8000/data` | POST | Receive data (MQTT bridge uses this) |
| `http://localhost:8000/data/latest?limit=N` | GET | Get recent measurements |
| `http://localhost:8000/stats` | GET | System statistics |
| `http://localhost:3000` | GET | Dashboard UI |

### Data Format

ESP32 publishes to `store/aisle1`:
```json
{
  "timestamp": "2024-11-12T15:30:00",
  "detections": [],
  "uwb_measurements": [
    {
      "mac_address": "0x0001",
      "distance_cm": 62.5,
      "status": "SUCCESS"
    }
  ]
}
```

## 📊 Project Structure

```
optiflow/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py            # API routes
│   │   ├── models.py          # SQLAlchemy models
│   │   ├── schemas.py         # Pydantic schemas
│   │   └── database.py        # DB connection
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                   # Next.js dashboard
│   ├── app/
│   │   ├── page.tsx           # Main page
│   │   ├── layout.tsx         # Root layout
│   │   └── components/
│   │       └── Dashboard.tsx  # Dashboard component
│   ├── package.json
│   └── Dockerfile
├── mqtt_bridge/               # MQTT-to-API bridge
│   ├── mqtt_to_api.py
│   ├── requirements.txt
│   └── Dockerfile
├── MQTT_TEST/                 # ESP32 firmware
├── UART_UWB_TEST/             # UWB testing code
├── docker-compose.yml
├── .env.example
└── README.md
```

## 🛠️ Development

### Run Backend Only

```bash
cd backend
pip install -r requirements.txt
export DATABASE_URL="postgresql://optiflow:optiflow_dev@localhost:5432/optiflow"
uvicorn app.main:app --reload
```

### Run Frontend Only

```bash
cd frontend
npm install
npm run dev
```

### Run MQTT Bridge Only

```bash
cd mqtt_bridge
pip install -r requirements.txt
export MQTT_BROKER_HOST="localhost"
export API_URL="http://localhost:8000"
python mqtt_to_api.py
```

## 📊 Database Schema

### `detections` table
- `id` (Primary Key)
- `timestamp` (DateTime)
- `product_id` (String)
- `product_name` (String)

### `uwb_measurements` table
- `id` (Primary Key)
- `timestamp` (DateTime)
- `mac_address` (String)
- `distance_cm` (Float)
- `status` (String, nullable)

## 🔮 Future Enhancements

- [ ] WebSocket support for real-time dashboard updates
- [ ] Server-side triangulation from UWB measurements
- [ ] Analytics dashboard (heatmaps, restock predictions)
- [ ] Authentication & multi-user support
- [ ] Mobile app for employees
- [ ] Alert system for missing inventory
- [ ] Integration with Decathlon inventory systems

---

## 🐛 Troubleshooting

### Issue: MQTT Bridge Shows "Network Unreachable"

**Symptoms:**
```
❌ Fatal error: [Errno 101] Network is unreachable
```

**Fix:**
```bash
# 1. Check Mosquitto is running
ps aux | grep mosquitto | grep -v grep

# 2. If not running, start it
brew services start mosquitto

# 3. Verify your MacBook IP matches .env
cat .env | grep MQTT_BROKER_HOST
# Should be your actual IP (e.g., 172.20.10.3), not localhost

# 4. Restart MQTT bridge
docker compose restart mqtt_bridge
```

---

### Issue: ESP32 Not Connecting to WiFi

**Symptoms:**
```
[WiFi] Connecting...
...................
[WiFi] Failed!
```

**Fix:**
1. Check WiFi credentials in firmware (lines 32-34)
2. Verify hotspot "Oscar" is active
3. Make sure ESP32 is in range
4. Check password is correct

---

### Issue: No UWB Measurements (0 measurements)

**Symptoms:**
```
=== UWB Session #1 ===
Measurements: 0
```

**Fix:**
1. **Power on anchor boards** - they must be running
2. **Configure anchors** as RESPF mode:
   ```bash
   INITR
   RESPF
   SAVE
   ```
3. **Check anchor LEDs** are blinking
4. **Verify same session parameters** on tag and anchors
5. **Move tag closer** to anchors (within 10 meters)

---

### Issue: Dashboard Shows "Disconnected"

**Fix:**
```bash
# 1. Check backend is running
curl http://localhost:8000
# Should return: {"status":"online"...}

# 2. Check Docker containers
docker compose ps
# All should show "Up"

# 3. Restart if needed
docker compose restart backend frontend

# 4. Clear browser cache and refresh
```

---

### Issue: Data Not Appearing on Dashboard

**Fix:**
```bash
# 1. Verify ESP32 received START signal
# In Serial Monitor, you should see:
# [CONTROL] START received!

# 2. Send START signal again
mosquitto_pub -h 172.20.10.3 -t store/control -m 'START'

# 3. Check MQTT bridge is receiving data
docker logs optiflow-mqtt-bridge --tail 20
# Should show: 📥 Received message...

# 4. Check database has data
docker compose exec -T postgres psql -U optiflow -d optiflow -c \
  "SELECT COUNT(*) FROM uwb_measurements;"

# 5. Wait for frontend auto-refresh (2 seconds)
```

---

### Issue: "Cannot find DWM3001CDK serial port"

**Fix:**
1. Check USB cable supports data (not just power)
2. Install CH340/CP2102 drivers if needed
3. Check port permissions on macOS:
   ```bash
   ls -l /dev/cu.*
   ```
4. Try different USB port

---

### Issue: Docker Services Won't Start

**Fix:**
```bash
# 1. Check Docker Desktop is running
docker ps
# If error, start Docker Desktop

# 2. Check for port conflicts
lsof -i :8000  # Backend
lsof -i :3000  # Frontend
lsof -i :5432  # PostgreSQL

# 3. Kill conflicting processes or change ports in docker-compose.yml

# 4. Clean start
docker compose down -v  # Warning: deletes database!
docker compose up --build
```

---

### Issue: High CPU Usage

**Cause:** UWB sessions every 200ms can generate lots of data.

**Fix:**
```bash
# 1. Increase session interval on DWM3001CDK
# Connect to tag and run:
SETAPP block_duration 500  # 500ms = 2Hz instead of 5Hz
SAVE

# 2. Limit frontend refresh rate
# Edit frontend/app/components/Dashboard.tsx
# Change: setInterval(fetchData, 5000)  // 5 seconds instead of 2
```

---

### Getting Help

**Check logs:**
```bash
# ESP32 logs
# → Serial Monitor at 115200 baud

# Backend logs
docker logs optiflow-backend

# MQTT bridge logs
docker logs optiflow-mqtt-bridge

# All logs
docker compose logs
```

**Common Log Messages:**

✅ **Good:**
- `✅ Connected to MQTT broker`
- `✅ Data forwarded successfully`
- `[MQTT] ✓ Published to store/aisle1`

❌ **Bad:**
- `❌ Fatal error: Network is unreachable` → Mosquitto not running
- `failed, rc=-2` → MQTT connection refused
- `Measurements: 0` → Anchors not configured/powered

---

## 📂 Project Structure

```
optiflow/
├── backend/                           # FastAPI backend
│   ├── app/
│   │   ├── main.py                   # API routes & startup
│   │   ├── models.py                 # Database models
│   │   ├── schemas.py                # Pydantic schemas
│   │   └── database.py               # DB connection
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                          # Next.js dashboard
│   ├── app/
│   │   ├── page.tsx                  # Main dashboard page
│   │   └── components/
│   │       └── Dashboard.tsx         # Dashboard component
│   ├── package.json
│   └── Dockerfile
├── mqtt_bridge/                       # MQTT → API bridge
│   ├── mqtt_to_api.py               # Bridge script
│   ├── requirements.txt
│   └── Dockerfile
├── UART_UWB_TEST/                    # ESP32 firmware
│   └── esp32_dwm3001_cli/
│       └── esp32_uwb_simple_mqtt.ino # ⭐ Main ESP32 code
├── docker-compose.yml                 # Orchestration
├── .env                              # Configuration
├── README.md                         # This file
├── TESTING.md                        # Testing guide
└── ARCHITECTURE.md                   # System architecture
```

---

## � What's Next?

### Current Status ✅
- [x] UWB distance measurements working
- [x] Real-time MQTT data pipeline
- [x] PostgreSQL database storage
- [x] REST API backend
- [x] Live dashboard

### Coming Soon 🚧
- [ ] **RFID Integration** - Connect RFID reader to ESP32
- [ ] **Triangulation** - Calculate 2D/3D position from multiple anchors
- [ ] **WebSocket Support** - Push updates instead of polling
- [ ] **Analytics Dashboard** - Heatmaps, movement patterns
- [ ] **Alert System** - Notify when items go missing
- [ ] **Mobile App** - Employee interface

### Future Enhancements 🌟
- [ ] Authentication & multi-user support
- [ ] Integration with Decathlon inventory systems
- [ ] ML-based anomaly detection
- [ ] Predictive restocking
- [ ] Multi-store deployment

---

## 📚 Additional Documentation

- **[TESTING.md](TESTING.md)** - Comprehensive testing guide
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture deep-dive
- **[backend/app/](backend/app/)** - Backend API documentation
- **[frontend/app/](frontend/app/)** - Frontend component documentation

---

## 🤝 Contributing

This is a prototype for Decathlon's smart retail innovation. For questions or contributions, please open an issue.

---

## 📝 License

MIT License - See LICENSE file for details

---

## 👥 Team

Built for Decathlon's warehouse and retail innovation initiatives.

**Hardware Stack:**
- ESP32-S3 microcontroller
- DWM3001CDK UWB modules (Qorvo)
- RFID reader (planned)

**Software Stack:**
- FastAPI (Python)
- PostgreSQL
- Next.js (React/TypeScript)
- Docker
- Mosquitto MQTT

---

## 📞 Support

**Quick Reference:**

| Service | URL/Command | Purpose |
|---------|-------------|---------|
| Dashboard | http://localhost:3000 | Live monitoring |
| Backend API | http://localhost:8000 | REST API |
| API Docs | http://localhost:8000/docs | Interactive API docs |
| Logs | `docker compose logs -f` | View all logs |
| Database | `docker compose exec postgres psql -U optiflow optiflow` | Direct DB access |

**Need Help?**
1. Check the [Troubleshooting](#-troubleshooting) section
2. Review logs: `docker compose logs`
3. Check ESP32 Serial Monitor
4. Verify all services are running: `docker compose ps`
