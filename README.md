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

### Step 1: Automated Setup

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

### Step 2: Generate Store Inventory

**NEW: Generate realistic store inventory with thousands of products!**

```bash
# Generate 3000 items with realistic variants (sizes, colors, styles)
python3 -m simulation.generate_inventory --items 3000
```

This creates:
- **1,500+ unique product variants** (Running Shoes - Pro Black 9, Athletic T-Shirt - Medium Blue, etc.)
- **3,000 RFID-tagged items** distributed across the store
- **Realistic categories**: Footwear, Apparel, Sports Equipment, Fitness, Accessories, Electronics, Nutrition

💡 **See [Inventory Generation Guide](docs/INVENTORY_GENERATION.md) for advanced options**

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

### Step 3: Configure Anchors

1. Open http://localhost:3000 in your browser
2. Click **"⚙️ Setup Mode"** button
3. Click on the map to place anchors at your physical anchor locations
   - Minimum: 2 anchors (basic positioning)
   - Recommended: 4 anchors (best accuracy)
   - Place at corners or edges of store for optimal triangulation
4. Drag anchors to adjust positions if needed
5. Click **"✓ Finish Setup"** when done

**Important:** The simulator will automatically load anchor positions from the backend!

### Step 4: Run Simulator

```bash
# Start simulator with real-time analytics tracking
python3 -m simulation.main --analytics

# Note: Simulation now uses database inventory!
# --mode is still available but mainly affects shopper behavior
# --speed 2.0      # 2x speed (default 1.0)
# --analytics      # Enable real-time analytics tracking
```

### Step 5: Generate Historical Analytics (Optional)

```bash
# Generate 30 days of historical data for analytics dashboard
python3 -m simulation.backfill_history --days 30 --density normal

# Or use the frontend: Analytics → Generate Data button
```

### Step 6: Watch Magic Happen ✨

You should now see:
- 🚶 **Blue employee icon** moving through aisles (UWB triangulated position)
- **Dashed circle** around employee showing 1.5m RFID detection range
- ✅ **Green squares** for items detected within range (RFID)
- ⚠️ **Red squares** for missing items (displayed on map AND in sidebar)
- 📊 Live position updates with confidence scores
- 📋 **Restock Queue** sidebar showing all missing items

**How it works:**
1. UWB anchors triangulate employee position every 0.5s
2. Employee walks through aisles following realistic patterns
3. RFID detects items within 2 meters of employee
4. Items persist on map even after employee walks away
5. Missing items are flagged when expected items aren't detected

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

### 1. Employee Tracking (UWB Triangulation)

The system uses **trilateration** to calculate employee's 2D position:

- **2 anchors**: Weighted midpoint (~50% confidence)
- **3+ anchors**: Least-squares algorithm (70-90% confidence)
- **Update rate**: 6-7 times per second (0.15s interval)
- **Accuracy**: Typically 20-50cm with 4 anchors

### 2. Item Detection (RFID Simulation)

- **Detection range**: 1.5m radius around employee
- **Persistent display**: Items stay on map after detection
- **Status tracking**: present/missing
- **First pass**: All items detected as "present" (baseline inventory)
- **Later passes**: 1-2% chance items go missing per pass
- **Smart reporting**: Only reports status changes, not duplicate scans (prevents database bloat)

### 3. Movement Pattern

Employee follows realistic back-and-forth pattern:
```
Aisle 1 (down) → Cross aisle → Aisle 2 (up/down) → Cross aisle →
Aisle 3 (up/down) → Cross aisle → Aisle 4 (up/down) → Walk back to start
```

- **Speed**: 30 cm/s (realistic walking pace)
- **Updates**: 6-7 per second for smooth tracking
- **Movement**: Independent of anchor positions (follows store layout)

### 4. Data Efficiency

**Backend optimizations:**
- Only creates new Detection record when item status changes
- Updates timestamp for unchanged items (no duplicate records)
- New `/data/items` endpoint returns unique items (not raw detection logs)

**Result**: Database grows ~30-50x slower, items never disappear from map

---

## 🎮 Using the System

### API Endpoints

```bash
# Check backend health
curl http://localhost:8000

# List configured anchors
curl http://localhost:8000/anchors | jq

# Get latest position
curl http://localhost:8000/positions/latest?limit=1 | jq

# Get all unique items (with latest status)
curl http://localhost:8000/data/items | jq

# Get only missing items
curl http://localhost:8000/data/missing | jq

# Clear all tracking data
curl -X DELETE http://localhost:8000/data/clear
```

### Simulator Options

```bash
# Enable real-time analytics tracking (recommended)
python3 -m simulation.main --analytics

# Custom snapshot interval (default: 3600s = 1 hour)
python3 -m simulation.main --analytics --snapshot-interval 1800

# Custom MQTT broker
python3 -m simulation.main --broker 192.168.1.100

# Custom mode and speed
python3 -m simulation.main --mode stress --speed 0.5

# Custom backend API
python3 -m simulation.main --api http://192.168.1.100:8000

# Full example with analytics
python3 -m simulation.main --mode realistic --speed 2.0 --analytics --snapshot-interval 600
```

### Analytics Features

The simulation now includes **real-time analytics tracking**:

- **Stock Snapshots**: Periodic captures of inventory levels (configurable interval)
- **Purchase Events**: Automatic recording when items go missing (simulating purchases)
- **Background Thread**: Non-blocking analytics collection during simulation
- **Batch Uploads**: Efficient API calls with queued data

**Usage:**
```bash
# Run simulation with analytics enabled
python3 -m simulation.main --analytics

# Generate historical data for testing
python3 -m simulation.backfill_history --days 30 --density normal

# View analytics dashboard
open http://localhost:3000/analytics
```

### Customize Store Layout

Edit `simulation/config.py`:
```python
STORE_WIDTH = 1000       # Store width in cm
STORE_HEIGHT = 800       # Store height in cm
UPDATE_INTERVAL = 0.15   # Update frequency (lower = more updates)
```



## 📁 Project Structure

```
optiflow/
├── backend/                     # FastAPI backend
│   ├── app/
│   │   ├── main.py             # API endpoints + triangulation
│   │   ├── models.py           # Database models
│   │   ├── schemas.py          # Pydantic schemas
│   │   ├── triangulation.py   # Position calculation
│   │   └── database.py         # DB connection
│   └── Dockerfile
├── frontend/                    # Next.js dashboard
│   ├── app/
│   │   ├── page.tsx           # Main dashboard
│   │   └── components/
│   │       └── StoreMap.tsx   # Interactive map
│   └── Dockerfile
├── mqtt_bridge/                # MQTT → HTTP bridge
│   ├── mqtt_to_api.py
│   └── Dockerfile
├── simulation/                  # Modular simulator
│   ├── main.py                # CLI entry point
│   ├── config.py              # Configuration
│   ├── inventory.py           # Item generation
│   ├── shopper.py             # Movement simulation
│   └── scanner.py             # RFID/UWB scanning
├── firmware/                    # ESP32 hardware docs (optional)
│   ├── UWB_TEST/              # UWB setup guides
│   └── RFID_TEST/             # RFID integration
├── docs/                        # Technical documentation
│   ├── architecture/          # System architecture
│   ├── implementation/        # Implementation guides
│   └── reference/             # Reference materials
├── docker-compose.yml          # Service orchestration
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## 📚 Documentation

For detailed technical documentation, see the [docs/](docs/) directory:
- [Simulation Architecture](docs/architecture/simulation.md) - Modular simulation system design
- [Heatmap Implementation](docs/implementation/heatmap.md) - Stock depletion heatmap details
- [Color Reference](docs/reference/colors.md) - Visual design and color system

---

## 🐛 Troubleshooting

### "Could not load anchors from backend"
```bash
# Check backend is running
curl http://localhost:8000

# If not, restart services
docker compose restart backend

# Configure anchors in web UI at http://localhost:3000
```

### "Items disappearing from map"
This should be fixed! Items now persist regardless of pass count. If still happening:
```bash
# Clear old data and restart
curl -X DELETE http://localhost:8000/data/clear
docker compose restart backend frontend
python3 -m simulation.main --mode realistic
```

### Services won't start
```bash
# Check if ports are in use
lsof -i :3000  # Frontend
lsof -i :8000  # Backend
lsof -i :1883  # MQTT

# Stop Docker and restart
docker compose down
docker compose up -d

# Check logs
docker compose logs backend
docker compose logs frontend
```

### No Positions Calculated
```bash
# Verify at least 2 anchors configured
curl http://localhost:8000/anchors

# Check UWB measurements arriving
curl http://localhost:8000/data/latest?limit=5
```

### Python Module Not Found
```bash
pip3 install -r requirements.txt
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
