# OptiFlow

Real-time inventory tracking system combining UWB (Ultra-Wideband) positioning and RFID detection for retail environments. The system provides precise employee tracking, automated inventory monitoring, and comprehensive analytics.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Hardware Integration](#hardware-integration)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

---

## Overview

OptiFlow is a full-stack inventory management solution that tracks:

- **Employee Position**: UWB triangulation provides sub-meter accuracy positioning
- **Item Detection**: RFID scanning detects items within proximity of employees
- **Stock Levels**: Real-time monitoring of present/missing items
- **Analytics**: Historical trends, product velocity, and AI-powered insights

### Key Features

| Feature | Description |
|---------|-------------|
| Real-time Tracking | 6-7 position updates per second with confidence scoring |
| Dual Database | Separate databases for simulation and production environments |
| Interactive Dashboard | Canvas-based store visualization with drag-and-drop anchor configuration |
| Stock Heatmap | Visual representation of inventory depletion by location |
| Analytics Suite | Product velocity, category performance, demand forecasting |
| Hardware Ready | ESP32 firmware for RFID + UWB integration |

---

## Architecture

### System Overview

```
                                    OPTIFLOW SYSTEM ARCHITECTURE
    
    ┌─────────────────────────────────────────────────────────────────────────────────┐
    │                              PRESENTATION LAYER                                  │
    │  ┌─────────────────────────────────────────────────────────────────────────┐   │
    │  │                        Next.js Frontend (Port 3000)                      │   │
    │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │   │
    │  │  │  Store Map   │  │  Admin Panel │  │  Analytics   │  │  Restock    │  │   │
    │  │  │  (Canvas)    │  │  (Settings)  │  │  Dashboard   │  │  Queue      │  │   │
    │  │  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────┘  │   │
    │  └─────────────────────────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          │ HTTP/REST
                                          ▼
    ┌─────────────────────────────────────────────────────────────────────────────────┐
    │                               APPLICATION LAYER                                  │
    │  ┌─────────────────────────────────────────────────────────────────────────┐   │
    │  │                      FastAPI Backend (Port 8000)                         │   │
    │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │   │
    │  │  │ Triangula-  │  │   Data      │  │  Analytics  │  │   Simulation    │ │   │
    │  │  │ tion Engine │  │   Ingestion │  │  Engine     │  │   Controller    │ │   │
    │  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘ │   │
    │  └─────────────────────────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────────────────────────┘
                                          │
                          ┌───────────────┼───────────────┐
                          │               │               │
                          ▼               ▼               ▼
    ┌─────────────────────────────────────────────────────────────────────────────────┐
    │                                 DATA LAYER                                       │
    │  ┌───────────────────────┐              ┌───────────────────────┐               │
    │  │  PostgreSQL           │              │  PostgreSQL           │               │
    │  │  Simulation DB        │              │  Production DB        │               │
    │  │  (Port 5432)          │              │  (Port 5433)          │               │
    │  │                       │              │                       │               │
    │  │  - Inventory Items    │              │  - Inventory Items    │               │
    │  │  - Products           │              │  - Products           │               │
    │  │  - Zones              │              │  - Zones              │               │
    │  │  - Anchors            │              │  - Anchors            │               │
    │  │  - Analytics Data     │              │  - Analytics Data     │               │
    │  └───────────────────────┘              └───────────────────────┘               │
    └─────────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow Diagram

```
                              HARDWARE/SIMULATION DATA FLOW

    ┌──────────────────┐          ┌──────────────────┐
    │   ESP32 + UWB    │          │   Python         │
    │   + RFID         │          │   Simulator      │
    │   (Hardware)     │          │   (Development)  │
    └────────┬─────────┘          └────────┬─────────┘
             │                              │
             │ MQTT                         │ MQTT
             │ (store/aisle1)               │ (store/aisle1)
             ▼                              ▼
    ┌─────────────────────────────────────────────────┐
    │              Mosquitto MQTT Broker              │
    │                   (Port 1883)                   │
    └─────────────────────┬───────────────────────────┘
                          │
                          │ Subscribe
                          ▼
    ┌─────────────────────────────────────────────────┐
    │              MQTT Bridge Service                │
    │                                                 │
    │   - Transforms hardware JSON to API format     │
    │   - Forwards to backend via HTTP POST          │
    └─────────────────────┬───────────────────────────┘
                          │
                          │ HTTP POST /data
                          ▼
    ┌─────────────────────────────────────────────────┐
    │              FastAPI Backend                    │
    │                                                 │
    │   1. Receive UWB distances + RFID detections   │
    │   2. Match anchors by MAC address              │
    │   3. Triangulate employee position             │
    │   4. Update item statuses (present/missing)    │
    │   5. Record analytics events                   │
    └─────────────────────┬───────────────────────────┘
                          │
                          │ SQL
                          ▼
    ┌─────────────────────────────────────────────────┐
    │              PostgreSQL Database                │
    │                                                 │
    │   Tables:                                       │
    │   - inventory_items (RFID tags, positions)     │
    │   - products (SKU, name, category)             │
    │   - tag_positions (calculated positions)       │
    │   - anchors (UWB anchor configurations)        │
    │   - zones (store areas)                        │
    │   - purchase_events (analytics)                │
    │   - stock_snapshots (historical data)          │
    └─────────────────────────────────────────────────┘
```

### Position Calculation

```
                        REAL-TIME POSITION CALCULATION

    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
    │  Anchor 1   │     │  Anchor 2   │     │  Anchor 3   │     │  Anchor 4   │
    │  (Corner)   │     │  (Corner)   │     │  (Corner)   │     │  (Corner)   │
    └──────┬──────┘     └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
           │                   │                   │                   │
           │ d1 = 245cm        │ d2 = 312cm        │ d3 = 198cm        │ d4 = 287cm
           │                   │                   │                   │
           └───────────────────┴───────────────────┴───────────────────┘
                                         │
                                         ▼
                        ┌────────────────────────────────┐
                        │    Triangulation Algorithm     │
                        │                                │
                        │  - 2 anchors: Weighted midpoint│
                        │  - 3+ anchors: Least squares   │
                        │  - Confidence: 0.3 - 0.95      │
                        └────────────────┬───────────────┘
                                         │
                                         ▼
                        ┌────────────────────────────────┐
                        │   Employee Position            │
                        │   x: 423.5, y: 287.2           │
                        │   confidence: 0.87             │
                        └────────────────────────────────┘
```

### Frontend Component Architecture

```
                           FRONTEND ARCHITECTURE

    ┌─────────────────────────────────────────────────────────────────┐
    │                         page.tsx (Main)                         │
    │  ┌──────────────────────────────────────────────────────────┐  │
    │  │  State Management                                         │  │
    │  │  - Mode (simulation/real)                                 │  │
    │  │  - Items, Positions, Anchors                              │  │
    │  │  - Simulation Status                                      │  │
    │  └──────────────────────────────────────────────────────────┘  │
    │                              │                                  │
    │           ┌──────────────────┼──────────────────┐              │
    │           ▼                  ▼                  ▼              │
    │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐  │
    │  │   StoreMap.tsx  │ │  Dashboard.tsx  │ │ Admin Panel     │  │
    │  │                 │ │                 │ │                 │  │
    │  │  - Canvas       │ │  - Stats Cards  │ │  - Mode Toggle  │  │
    │  │  - Anchors      │ │  - Item List    │ │  - Item Count   │  │
    │  │  - Items        │ │  - Restock Queue│ │  - Start/Stop   │  │
    │  │  - Employee     │ │                 │ │  - Clear Data   │  │
    │  │  - Heatmap      │ │                 │ │                 │  │
    │  │  - Zones        │ │                 │ │                 │  │
    │  └─────────────────┘ └─────────────────┘ └─────────────────┘  │
    └─────────────────────────────────────────────────────────────────┘
                                    │
                                    │ /analytics
                                    ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                    Analytics Dashboard                          │
    │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐  │
    │  │ AnalyticsOver-  │ │ ProductVelocity │ │ DemandForecast  │  │
    │  │ view.tsx        │ │ Chart.tsx       │ │ Chart.tsx       │  │
    │  └─────────────────┘ └─────────────────┘ └─────────────────┘  │
    │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐  │
    │  │ CategoryDonut   │ │ TopProducts     │ │ AIClusterView   │  │
    │  │ .tsx            │ │ Table.tsx       │ │ .tsx            │  │
    │  └─────────────────┘ └─────────────────┘ └─────────────────┘  │
    └─────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Docker | 20.10+ | Container runtime |
| Docker Compose | 2.0+ | Service orchestration |
| Python | 3.9+ | Simulation scripts |
| Node.js | 18+ | Frontend development (optional) |

### Required Services

| Service | Port | Description |
|---------|------|-------------|
| Mosquitto | 1883 | MQTT message broker |

### macOS Installation

```bash
# Install Docker Desktop (includes Docker Compose)
# Download from: https://www.docker.com/products/docker-desktop

# Install Mosquitto MQTT broker
brew install mosquitto
brew services start mosquitto

# Install Python dependencies
pip3 install paho-mqtt requests
```

### Linux Installation

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Mosquitto
sudo apt-get install mosquitto mosquitto-clients

# Install Python dependencies
pip3 install paho-mqtt requests
```

---

## Installation

### Quick Start

```bash
# Clone repository
git clone https://github.com/oscardef/optiflow.git
cd optiflow

# Start all services
docker compose up -d

# Verify services are running
docker compose ps

# Generate inventory (simulation mode)
python3 -m simulation.generate_inventory --items 3000

# Access the dashboard
open http://localhost:3000
```

### Service Ports

| Service | Port | URL |
|---------|------|-----|
| Frontend | 3000 | http://localhost:3000 |
| Backend API | 8000 | http://localhost:8000 |
| API Documentation | 8000 | http://localhost:8000/docs |
| Simulation Database | 5432 | postgresql://localhost:5432/optiflow_simulation |
| Production Database | 5433 | postgresql://localhost:5433/optiflow_real |

---

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Database
POSTGRES_USER=optiflow
POSTGRES_PASSWORD=optiflow_dev

# MQTT
MQTT_BROKER_HOST=host.docker.internal
MQTT_BROKER_PORT=1883

# API
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Anchor Configuration

1. Open the dashboard at http://localhost:3000
2. Click "Setup Mode" in the header
3. Click on the map to place anchors at physical locations
4. Minimum 2 anchors required, 4 recommended for optimal accuracy
5. Click "Finish Setup" when complete

### Store Zones

Zones are automatically created for simulation mode:

| Zone | Area | Type |
|------|------|------|
| Entrance | 0-200 x 0-160 | entrance |
| Aisle 1-4 | 200-1000 x 0-400 | aisle |
| Cross Aisle | 0-1000 x 360-440 | aisle |
| Aisle 5-8 | 200-1000 x 440-800 | aisle |
| Checkout | 0-200 x 640-800 | checkout |

---

## Usage

### Running the Simulation

```bash
# Basic simulation with analytics
python3 -m simulation.main --analytics

# Custom speed (2x faster)
python3 -m simulation.main --analytics --speed 2.0

# Custom item count
python3 -m simulation.generate_inventory --items 5000
python3 -m simulation.main --analytics
```

### Dashboard Features

**Store Map**
- Blue circle: Employee position (UWB triangulated)
- Dashed circle: RFID detection range (1.5m)
- Green squares: Present items
- Red squares: Missing items
- Orange diamonds: UWB anchors

**Heatmap Mode**
- Toggle with "Heatmap" button
- Green: Full stock
- Yellow/Orange: Partial depletion
- Red: Significant missing items

**Admin Panel**
- Mode toggle: Switch between simulation and real hardware
- Item count: Configure number of items for simulation
- Start/Stop: Control simulation execution
- Clear items: Reset inventory data

### Generating Historical Data

```bash
# Generate 30 days of analytics data
python3 -m simulation.backfill_history --days 30 --density normal

# Generate high-density data for testing
python3 -m simulation.backfill_history --days 7 --density high
```

---

## API Reference

### Core Endpoints

#### Data Ingestion

```
POST /data
```
Receives detection and UWB measurement data from hardware or simulation.

Request body:
```json
{
  "timestamp": "2025-12-02T10:00:00Z",
  "tag_id": "employee",
  "detections": [
    {"product_id": "RFID001", "status": "present", "x_position": 400, "y_position": 300}
  ],
  "uwb_measurements": [
    {"mac_address": "0x0001", "distance_cm": 245.5, "status": "0x01"}
  ]
}
```

#### Position Tracking

```
GET /positions/latest?limit=10
```
Returns latest calculated positions.

Response:
```json
[
  {
    "id": 1,
    "tag_id": "employee",
    "x_position": 423.5,
    "y_position": 287.2,
    "confidence": 0.87,
    "timestamp": "2025-12-02T10:00:00Z"
  }
]
```

#### Inventory

```
GET /data/items
```
Returns all inventory items with current status.

```
GET /data/missing
```
Returns only missing items.

```
DELETE /data/clear
```
Clears all tracking data (detections, positions).

### Anchor Management

```
GET /anchors                    # List all anchors
POST /anchors                   # Create anchor
PUT /anchors/{id}               # Update anchor
DELETE /anchors/{id}            # Delete anchor
```

### Analytics Endpoints

```
GET /analytics/stock-heatmap           # Stock depletion by location
GET /analytics/overview                # Summary metrics
GET /analytics/top-products            # Best performing products
GET /analytics/category-performance    # Performance by category
GET /analytics/stock-trends/{id}       # Historical trends for product
GET /analytics/slow-movers             # Slow-moving inventory
GET /analytics/ai/demand-forecast      # ML-based demand prediction
GET /analytics/ai/abc-analysis         # ABC inventory classification
```

### Simulation Control

```
GET /simulation/status                  # Current simulation state
POST /simulation/start                  # Start simulation
POST /simulation/stop                   # Stop simulation
POST /simulation/generate-inventory     # Generate new inventory
PUT /simulation/params                  # Update simulation parameters
```

### Configuration

```
GET /config/mode                        # Current mode (simulation/real)
POST /config/mode                       # Set mode
GET /config/settings                    # Store configuration
```

---

## Hardware Integration

### Supported Hardware

| Component | Model | Purpose |
|-----------|-------|---------|
| Microcontroller | ESP32-S3 | Main processing unit |
| UWB Module | DWM3001CDK | Distance measurement |
| RFID Reader | JRD-100 (UHF) | Tag detection |

### Wiring Diagram

```
                    ESP32-S3 WIRING

    ┌─────────────────────────────────────────┐
    │              ESP32-S3                    │
    │                                          │
    │  GPIO6 (RX) <-------- RFID TX (Blue)    │
    │  GPIO7 (TX) --------> RFID RX (White)   │
    │  GND <--------------> RFID GND (Black)  │
    │  5V ----------------> RFID VCC (Red)    │
    │                                          │
    │  GPIO18 (RX) <------- DWM P0.19 (TX)    │
    │  GPIO17 (TX) -------> DWM P0.15 (RX)    │
    │  GND <--------------> DWM GND           │
    └─────────────────────────────────────────┘
```

### Firmware Configuration

Edit `firmware/code_esp32/code_esp32.ino`:

```cpp
// WiFi Configuration
const char* WIFI_SSID = "YourNetwork";
const char* WIFI_PASSWORD = "YourPassword";
const char* MQTT_SERVER = "192.168.1.100";  // Your server IP
const int MQTT_PORT = 1883;
```

### Anchor Setup

For each DWM3001CDK anchor:

1. Connect via USB
2. Open serial monitor (115200 baud)
3. Enter configuration commands:
   ```
   INITR
   RESPF
   SAVE
   ```
4. Power anchor and position in store

---

## Development

### Project Structure

```
optiflow/
├── backend/                    # FastAPI backend service
│   ├── app/
│   │   ├── main.py            # Application entry point
│   │   ├── models.py          # SQLAlchemy models
│   │   ├── schemas.py         # Pydantic schemas
│   │   ├── database.py        # Database configuration
│   │   ├── triangulation.py   # Position calculation
│   │   ├── config.py          # Application settings
│   │   ├── routers/           # API route handlers
│   │   │   ├── analytics.py   # Analytics endpoints
│   │   │   ├── anchors.py     # Anchor management
│   │   │   ├── data.py        # Data ingestion
│   │   │   ├── positions.py   # Position queries
│   │   │   ├── products.py    # Product management
│   │   │   ├── simulation.py  # Simulation control
│   │   │   └── zones.py       # Zone management
│   │   └── services/
│   │       └── ai_analytics.py # ML analytics
│   ├── migrations/            # Database migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                   # Next.js frontend
│   ├── app/
│   │   ├── page.tsx           # Main dashboard
│   │   ├── layout.tsx         # App layout
│   │   ├── analytics/         # Analytics page
│   │   ├── admin/             # Admin panel
│   │   └── components/        # React components
│   ├── package.json
│   └── Dockerfile
├── mqtt_bridge/               # MQTT to HTTP bridge
│   ├── mqtt_to_api.py
│   ├── requirements.txt
│   └── Dockerfile
├── simulation/                # Python simulation
│   ├── main.py               # CLI entry point
│   ├── config.py             # Simulation settings
│   ├── inventory.py          # Item generation
│   ├── shopper.py            # Movement patterns
│   ├── scanner.py            # RFID/UWB simulation
│   ├── analytics_tracker.py  # Analytics collection
│   ├── generate_inventory.py # Inventory generator
│   └── backfill_history.py   # Historical data
├── firmware/                  # ESP32 firmware
│   └── code_esp32/
├── docs/                      # Documentation
├── docker-compose.yml
└── README.md
```

### Database Schema

```
                          DATABASE SCHEMA

    ┌─────────────────┐         ┌─────────────────┐
    │    products     │         │     zones       │
    ├─────────────────┤         ├─────────────────┤
    │ id (PK)         │         │ id (PK)         │
    │ sku             │<───┐    │ name            │
    │ name            │    │    │ x_min, x_max    │
    │ category        │    │    │ y_min, y_max    │
    │ price           │    │    │ zone_type       │
    │ optimal_stock   │    │    └────────┬────────┘
    │ reorder_thresh  │    │             │
    └─────────────────┘    │             │
                           │             │
    ┌─────────────────┐    │             │
    │ inventory_items │    │             │
    ├─────────────────┤    │             │
    │ id (PK)         │    │             │
    │ rfid_tag        │    │             │
    │ product_id (FK) │────┘             │
    │ zone_id (FK)    │──────────────────┘
    │ x_position      │
    │ y_position      │
    │ status          │
    └─────────────────┘

    ┌─────────────────┐         ┌─────────────────┐
    │    anchors      │         │  tag_positions  │
    ├─────────────────┤         ├─────────────────┤
    │ id (PK)         │         │ id (PK)         │
    │ mac_address     │         │ tag_id          │
    │ name            │         │ x_position      │
    │ x_position      │         │ y_position      │
    │ y_position      │         │ confidence      │
    │ is_active       │         │ timestamp       │
    └─────────────────┘         └─────────────────┘

    ┌─────────────────┐         ┌─────────────────┐
    │ purchase_events │         │ stock_snapshots │
    ├─────────────────┤         ├─────────────────┤
    │ id (PK)         │         │ id (PK)         │
    │ product_id (FK) │         │ product_id (FK) │
    │ quantity        │         │ stock_level     │
    │ unit_price      │         │ snapshot_time   │
    │ timestamp       │         └─────────────────┘
    └─────────────────┘
```

### Running Tests

```bash
# Backend tests
cd backend
pytest

# System tests
python3 test_system.py

# MQTT tests
python3 test_mqtt.py
```

### Local Development

```bash
# Backend (without Docker)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (without Docker)
cd frontend
npm install
npm run dev
```

---

## Troubleshooting

### Common Issues

**Services won't start**
```bash
# Check port availability
lsof -i :3000 :8000 :5432 :5433

# Restart all services
docker compose down
docker compose up -d

# View logs
docker compose logs backend
docker compose logs frontend
```

**No positions calculated**
```bash
# Verify anchors are configured
curl http://localhost:8000/anchors

# Check for at least 2 active anchors
# Reconfigure anchors in the UI if needed
```

**Items not appearing on map**
```bash
# Verify items exist in database
curl http://localhost:8000/data/items | head

# Regenerate inventory if empty
python3 -m simulation.generate_inventory --items 3000
```

**MQTT connection failed**
```bash
# Verify Mosquitto is running
brew services list | grep mosquitto

# Start Mosquitto
brew services start mosquitto

# Test MQTT
mosquitto_pub -h localhost -t test -m "hello"
```

**Database connection errors**
```bash
# Check database containers
docker compose ps

# Restart databases
docker compose restart postgres-simulation postgres-real

# View database logs
docker compose logs postgres-simulation
```

### Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend

# Last 100 lines
docker compose logs --tail=100 backend
```

### Reset System

```bash
# Clear all data (keep configuration)
curl -X DELETE http://localhost:8000/data/clear

# Full reset (remove volumes)
docker compose down -v
docker compose up -d
```

---

## License

MIT License

---

## Support

- Repository: https://github.com/oscardef/optiflow
- Documentation: See `/docs` directory
- API Reference: http://localhost:8000/docs (when running)
