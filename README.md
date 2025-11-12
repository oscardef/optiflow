# OptiFlow - Real-time Store Tracking System

A UWB (Ultra-Wideband) positioning system for tracking items and employees in retail stores. Features an interactive map interface with real-time triangulation, aisle navigation simulation, and missing item detection.

## 🎯 What It Does

- **Real-time Position Tracking**: Uses UWB triangulation to calculate precise 2D positions
- **Interactive Store Map**: Canvas-based visualization with drag-and-drop anchor configuration
- **Item Tracking**: Persistent item display with status monitoring (present/missing)
- **Realistic Simulation**: Walk patterns through store aisles with proximity-based detection
- **Missing Item Alerts**: Automatic detection and notification when items disappear

---

## 🚀 Quick Start (5 Minutes - No Hardware!)

### Automated Setup

```bash
# One command to install and start everything!
./start.sh
```

This script will:
- ✅ Check prerequisites (Docker, Python, Homebrew)
- ✅ Install & start Mosquitto MQTT broker
- ✅ Install Python dependencies
- ✅ Start all Docker containers
- ✅ Verify services are running

### Manual Setup (if you prefer)

<details>
<summary>Click to expand manual setup steps</summary>

```bash
# 1. Install Mosquitto MQTT broker
brew install mosquitto
brew services start mosquitto

# 2. Install Python dependencies
pip3 install paho-mqtt

# 3. Start Docker services
docker compose up -d
```

</details>

### Configure Anchors

1. Open http://localhost:3000 in your browser
2. Click **"Setup Mode"** button
3. Click on the map to place 3-4 anchors (corners of the store work best)
4. Click **"Finish Setup"** when done

### Run Simulator

```bash
# Terminal 1: Start simulator
python3 esp32_simulator.py

# Terminal 2: Send START command
mosquitto_pub -h localhost -t 'store/control' -m 'START'
```

### Step 4: Watch Magic Happen ✨

You should now see:
- 🔵 Blue dot (tag) moving through aisles
- 🟠 Orange squares (items detected and present)
- 🔴 Red squares (missing items) with alerts in sidebar
- 📊 Live position updates with confidence scores

---

## 🏗️ System Architecture

```
┌─────────────────┐
│  ESP32 / Sim    │  Simulates/reads UWB distances
└────────┬────────┘
         │ MQTT
         ▼
┌─────────────────┐
│ Mosquitto MQTT  │  Message broker
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  MQTT Bridge    │  Forwards MQTT → HTTP
└────────┬────────┘
         │ HTTP POST
         ▼
┌─────────────────┐
│  FastAPI        │  • Triangulation algorithm
│  Backend        │  • Anchor management
└────────┬────────┘  • Position calculation
         │
         ▼
┌─────────────────┐
│  PostgreSQL     │  Stores measurements,
│  Database       │  anchors, positions, items
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Next.js        │  Interactive map dashboard
│  Frontend       │  with real-time updates
└─────────────────┘
```

---

## 📊 How It Works

### 1. UWB Triangulation

The system uses **trilateration** to calculate 2D positions from distance measurements:

- **2 anchors**: Weighted midpoint (~50% confidence)
- **3+ anchors**: Least-squares algorithm (70-90% confidence)

**Algorithm:**
```
For each anchor i: (x - x_i)² + (y - y_i)² = r_i²

Linearize and solve: position = (A^T A)^-1 (A^T b)

Confidence = exp(-avg_error / 50)
```

### 2. Store Simulation

The simulator creates a realistic store environment:

- **4 vertical aisles** (x = 200, 400, 600, 800 cm)
- **1 cross aisle** (y = 400 cm)
- **15+ items** distributed throughout aisles
- **Tag navigation** follows aisle patterns (up/down movement)
- **Boundary constraints** keep tag within 50-950cm x 50-750cm

### 3. Item Detection

- **RFID range**: 100cm detection radius
- **Status tracking**: present/missing/unknown
- **Missing probability**: 2% chance when detected
- **Persistent display**: All items stay on map regardless of detection

---

## 🎮 Using the System

### Anchor Setup Mode

1. Click **"Setup Mode"**
2. **Click** on map to place new anchors
3. **Drag** existing anchors to reposition
4. **Delete** anchors via sidebar
5. Click **"Finish Setup"**

**Tip:** Place anchors at store corners for best triangulation accuracy.

### Simulator Configuration

Edit `esp32_simulator.py` to customize:

```python
STORE_WIDTH = 1000   # Store width in cm
STORE_HEIGHT = 800   # Store height in cm
RFID_RANGE = 100     # Detection range in cm
UPDATE_INTERVAL = 0.5  # Seconds between updates
```

### Manual Testing

```bash
# Check backend health
curl http://localhost:8000

# List configured anchors
curl http://localhost:8000/anchors | jq

# Get latest positions
curl http://localhost:8000/positions/latest | jq

# Get all detections (items)
curl http://localhost:8000/data/latest?limit=100 | jq
```

---

## 🔧 API Endpoints

### Anchors
- `GET /anchors` - List all anchors
- `POST /anchors` - Create anchor (auto-called from UI)
- `PUT /anchors/{id}` - Update anchor position
- `DELETE /anchors/{id}` - Remove anchor

### Positions
- `GET /positions/latest` - Recent calculated positions
- `POST /calculate-position` - Manually trigger triangulation

### Data
- `POST /data` - Receive UWB measurements (MQTT bridge uses this)
- `GET /data/latest?limit=N` - Recent detections with locations

---

## 📁 Project Structure

```
optiflow/
├── backend/                     # FastAPI backend
│   ├── app/
│   │   ├── main.py             # API endpoints
│   │   ├── models.py           # Database models
│   │   ├── schemas.py          # Pydantic schemas
│   │   ├── triangulation.py   # Position calculation algorithm
│   │   └── database.py         # DB connection
│   └── Dockerfile
├── frontend/                    # Next.js dashboard
│   ├── app/
│   │   ├── page.tsx           # Main dashboard page
│   │   └── components/
│   │       └── StoreMap.tsx   # Interactive canvas map
│   └── Dockerfile
├── mqtt_bridge/                # MQTT → HTTP bridge
│   ├── mqtt_to_api.py
│   └── Dockerfile
├── firmware/                    # ESP32 hardware code (optional)
│   ├── UWB_TEST/              # UWB setup guides
│   └── RFID_TEST/             # RFID integration docs
├── scripts/                     # Optional helper scripts
│   ├── setup.sh               # Manual dependency installation
│   └── test_system.sh         # System validation tests
├── esp32_simulator.py          # Hardware simulator (no ESP32 needed!)
├── start.sh                    # One-command startup script
├── docker-compose.yml          # Service orchestration
└── README.md                   # This file
```

---

## 🐛 Troubleshooting

### Docker Command Not Found

```bash
# Add Docker to PATH permanently
echo 'export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Python Module Not Found

```bash
# Use pip3 for Python 3 (not pip which may use Python 2)
pip3 install paho-mqtt
```

### No Positions Calculated

**Check:**
1. At least 2 anchors configured: `curl http://localhost:8000/anchors`
2. UWB measurements arriving: `curl http://localhost:8000/data/latest?limit=5`
3. Simulator is running and received START command

### Frontend Shows "Disconnected"

```bash
# Restart backend
docker compose restart backend

# Check logs
docker logs optiflow-backend --tail 50
```

### Items Not Appearing on Map

```bash
# Rebuild frontend with updated code
docker compose build frontend --no-cache
docker compose up -d frontend
```

### Simulator Connection Failed

```bash
# Check Mosquitto is running
brew services list | grep mosquitto

# Restart if needed
brew services restart mosquitto

# Verify your Mac's IP (if using hotspot)
ipconfig getifaddr en0
```

---

## 🛑 Stopping the System

```bash
# Stop all Docker containers
docker compose down

# Stop simulator (Ctrl+C in simulator terminal)

# Stop Mosquitto (optional)
brew services stop mosquitto
```

---

## 🎓 Real Hardware Setup (Optional)

### Hardware Requirements

- **ESP32-S3** development board
- **DWM3001CDK** UWB modules (1 tag + 2-4 anchors)
- USB cables for programming

### Anchor Configuration

For each DWM3001CDK anchor:

```
1. Connect USB, open Serial Monitor (115200 baud)
2. Type: INITR [Enter]
3. Type: RESPF [Enter]
4. Type: SAVE [Enter]
5. Disconnect, power via USB/battery
```

### ESP32 Firmware

1. Open `UART_UWB_TEST/esp32_dwm3001_cli/esp32_uwb_simple_mqtt.ino` in Arduino IDE
2. Configure WiFi settings (lines 32-34):
   ```cpp
   const char* ssid = "YourWiFi";
   const char* password = "YourPassword";
   const char* mqtt_server = "192.168.1.X";  // Your Mac IP
   ```
3. Select Board: "ESP32S3 Dev Module"
4. Upload sketch
5. Send START command: `mosquitto_pub -h localhost -t store/control -m 'START'`

---

## 🔮 What's Next

### Current Features ✅
- Interactive map with triangulation
- Anchor configuration UI
- ESP32 simulator with realistic movement
- Item tracking with missing item detection
- Aisle-following navigation pattern

### Future Enhancements 🚧
- WebSocket for real-time updates (no polling)
- RFID reader integration with ESP32
- Heatmap visualization of movement patterns
- Multi-store support
- Mobile app for employees
- Machine learning for anomaly detection
- Integration with inventory management systems

---

## �️ Helper Scripts

### Main Script

- **`./start.sh`** - One-command system startup
  - Checks prerequisites
  - Installs dependencies
  - Starts all services
  - Verifies everything is running

### Optional Scripts (in `scripts/` folder)

- **`scripts/setup.sh`** - Manual dependency installation only
- **`scripts/test_system.sh`** - Comprehensive system validation
  - Tests all endpoints
  - Creates/deletes test anchors
  - Verifies MQTT broker
  - Checks frontend accessibility

**Usage:**
```bash
# Test your system
./scripts/test_system.sh

# Manual setup (if you don't want automated script)
./scripts/setup.sh
```

---

## �📞 Support & Commands

**Quick Links:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

**Common Commands:**
```bash
# Start system
./start.sh

# Stop system
docker compose down

# Restart a service
docker compose restart backend

# View logs
docker compose logs -f

# Test system health
./scripts/test_system.sh

# Access database
docker compose exec postgres psql -U optiflow optiflow
```

---

## 📝 License

MIT License - Built for retail innovation and warehouse optimization.

---

**Need help?** Check the troubleshooting section above or review the logs with `docker compose logs`.
