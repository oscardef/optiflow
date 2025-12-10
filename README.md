# OptiFlow

Real-time inventory tracking system combining UWB (Ultra-Wideband) positioning and RFID detection for retail environments. The system provides precise employee tracking, automated inventory monitoring, and comprehensive analytics.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Mode Separation](#mode-separation)
- [Data Models](#data-models)
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
- **Timestamped Data**: All readings stored with precise timestamps for historical analysis

### Key Features

| Feature | Description |
|---------|-------------|
| Real-time Tracking | 6-7 position updates per second with confidence scoring |
| WebSocket Updates | Live position and item updates pushed to dashboard via WebSocket |
| Dual Database | Separate databases for simulation and production environments |
| Interactive Dashboard | Canvas-based store visualization with drag-and-drop anchor configuration |
| Stock Heatmap | Visual representation of inventory depletion by location |
| Analytics Suite | Product velocity, category performance, demand forecasting, AI clustering |
| Timestamped History | Every reading stored with timestamp for complete audit trail |
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
                                          │ HTTP/REST + WebSocket
                                          ▼
    ┌─────────────────────────────────────────────────────────────────────────────────┐
    │                               APPLICATION LAYER                                  │
    │  ┌─────────────────────────────────────────────────────────────────────────┐   │
    │  │                      FastAPI Backend (Port 8000)                         │   │
    │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │   │
    │  │  │ Triangula-  │  │   Data      │  │  Analytics  │  │   Simulation    │ │   │
    │  │  │ tion Engine │  │   Ingestion │  │  Engine     │  │   Controller    │ │   │
    │  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘ │   │
    │  │  ┌─────────────────────────────────────────────────────────────────────┐ │   │
    │  │  │ WebSocket Manager - Real-time position & item update broadcasting   │ │   │
    │  │  └─────────────────────────────────────────────────────────────────────┘ │   │
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
    │  │  - Products           │              │  - Products           │               │
    │  │  - Inventory Items    │              │  - Inventory Items    │               │
    │  │  - Detections         │              │  - Detections         │               │
    │  │  - UWB Measurements   │              │  - UWB Measurements   │               │
    │  │  - Tag Positions      │              │  - Tag Positions      │               │
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
             │ (store/production)           │ (store/simulation)
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
    │   - Generates UTC timestamp for each packet    │
    │   - Forwards to backend via HTTP POST          │
    └─────────────────────┬───────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────┐
    │              FastAPI Backend                    │
    │                                                 │
    │   1. Receive timestamped data packet           │
    │   2. Store RFID detections with timestamp      │
    │   3. Store UWB measurements with timestamp     │
    │   4. Match anchors by MAC address              │
    │   5. Triangulate employee position             │
    │   6. Update inventory items status & position  │
    │   7. Update last_seen_at for present items     │
    │   8. Record analytics events                   │
    │   9. Broadcast updates via WebSocket           │
    └─────────────────────┬───────────────────────────┘
                          │
                          │ SQL INSERT/UPDATE + WebSocket Broadcast
                          ▼
    ┌─────────────────────────────────────────────────┐
    │              PostgreSQL Database                │
    │                                                 │
    │   Core Tables (with timestamps):                │
    │   - detections (timestamp indexed)             │
    │   - uwb_measurements (timestamp indexed)       │
    │   - tag_positions (timestamp indexed)          │
    │   - inventory_items (last_seen_at, created_at) │
    │   - products (created_at, updated_at)          │
    │   - anchors (created_at, updated_at)           │
    │                                                 │
    │   Analytics Tables (with timestamps):           │
    │   - purchase_events (purchased_at indexed)     │
    │   - stock_snapshots (timestamp indexed)        │
    │   - stock_movements (timestamp indexed)        │
    │   - product_location_history (last_updated)    │
    │   - stock_levels (updated_at, last_restock_at) │
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
                        │   Employee Position Stored     │
                        │   tag_id: "employee"           │
                        │   x: 423.5, y: 287.2           │
                        │   confidence: 0.87             │
                        │   timestamp: 2025-12-08T...    │
                        └────────────────────────────────┘
```

---

## Mode Separation

OptiFlow operates in two distinct modes to **prevent data contamination** between simulation and production hardware:

### Operating Modes

| Mode | Data Source | MQTT Topic | Use Case |
|------|-------------|------------|----------|
| **SIMULATION** | Python simulation | `store/simulation` | Development, testing, demonstrations |
| **PRODUCTION** | ESP32 hardware | `store/production` | Production deployment with actual sensors |

### How It Works

The system enforces complete data separation through **mode-aware MQTT filtering**:

1. **Admin Panel** - Switch modes via UI toggle at `http://localhost:3000/admin`
2. **MQTT Bridge** - Automatically filters messages based on current mode
3. **No Overlap** - Simulation data never intersects with hardware data

```
┌─────────────────────┐
│  Switch Mode        │
│  (Admin Panel)      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  MQTT Bridge        │
│  Checks Mode        │
└──────────┬──────────┘
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
SIMULATION     PRODUCTION
Accept:        Accept:
store/         store/
simulation     production
```

### Quick Commands

```bash
# Switch to SIMULATION mode
curl -X POST http://localhost:8000/config/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "SIMULATION"}'

# Switch to PRODUCTION mode
curl -X POST http://localhost:8000/config/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "PRODUCTION"}'

# Check current mode
curl http://localhost:8000/config/mode
```

---

## Data Models

### Database Schema Relationships

```
                          DATABASE SCHEMA & RELATIONSHIPS

    ┌───────────────────┐
    │    products       │  Master product catalog
    ├───────────────────┤
    │ id (PK)           │
    │ sku (UNIQUE)      │
    │ name              │
    │ category          │
    │ unit_price        │
    │ reorder_threshold │
    │ optimal_stock_lvl │
    │ created_at        │  ← Timestamp when product created
    │ updated_at        │  ← Auto-updated on changes
    └─────────┬─────────┘
              │ 1
              │
              │ N
    ┌─────────┴─────────┐
    │ inventory_items   │  Individual RFID-tagged items
    ├───────────────────┤
    │ id (PK)           │
    │ rfid_tag (UNIQUE) │  ← RFID/EPC identifier
    │ product_id (FK)   │─────┐
    │ x_position        │     │
    │ y_position        │     │
    │ last_seen_at      │  ← Timestamp of last detection
    │ created_at        │  ← Timestamp when first detected
    │ updated_at        │  ← Auto-updated on changes
    └───────────────────┘     │
                              │
    ┌───────────────────┐     │
    │  stock_levels     │     │  Aggregated stock counts per product
    ├───────────────────┤     │
    │ id (PK)           │     │
    │ product_id (FK)   │─────┘
    │ current_count     │
    │ missing_count     │
    │ sold_today        │
    │ max_items_seen    │
    │ last_restock_at   │  ← Timestamp of last restock
    │ priority_score    │
    │ updated_at        │  ← Auto-updated on changes
    └───────────────────┘

    ┌───────────────────┐
    │   detections      │  Raw RFID detection events (append-only log)
    ├───────────────────┤
    │ id (PK)           │
    │ timestamp (IDX)   │  ← UTC timestamp from MQTT packet
    │ product_id        │
    │ product_name      │
    │ x_position        │
    │ y_position        │
    └───────────────────┘

    ┌───────────────────┐
    │ uwb_measurements  │  Raw UWB distance measurements (append-only log)
    ├───────────────────┤
    │ id (PK)           │
    │ timestamp (IDX)   │  ← UTC timestamp from MQTT packet
    │ mac_address       │
    │ distance_cm       │
    │ status            │
    └───────────────────┘

    ┌───────────────────┐
    │  tag_positions    │  Calculated employee positions (append-only log)
    ├───────────────────┤
    │ id (PK)           │
    │ timestamp (IDX)   │  ← UTC timestamp when calculated
    │ tag_id            │  Usually "employee"
    │ x_position        │  ← Calculated via triangulation
    │ y_position        │
    │ confidence        │  0.3 - 0.95
    │ num_anchors       │  Number of anchors used
    └───────────────────┘

    ┌───────────────────┐
    │    anchors        │  UWB anchor configuration
    ├───────────────────┤
    │ id (PK)           │
    │ mac_address (UNQ) │
    │ name              │
    │ x_position        │  ← Physical location on store map
    │ y_position        │
    │ is_active         │
    │ created_at        │
    │ updated_at        │
    └───────────────────┘

    ┌───────────────────────┐
    │  purchase_events      │  Sales analytics
    ├───────────────────────┤
    │ id (PK)               │
    │ inventory_item_id(FK) │
    │ product_id (FK)       │
    │ x_position            │  Where purchased
    │ y_position            │
    │ purchased_at (IDX)    │  ← Timestamp of sale
    └───────────────────────┘

    ┌───────────────────────┐
    │  stock_snapshots      │  Periodic stock level snapshots for trends
    ├───────────────────────┤
    │ id (PK)               │
    │ product_id (FK)       │
    │ timestamp (IDX)       │  ← Snapshot time
    │ present_count         │
    │ missing_count         │
    └───────────────────────┘

    ┌───────────────────────┐
    │  stock_movements      │  Individual stock movement events
    ├───────────────────────┤
    │ id (PK)               │
    │ product_id (FK)       │
    │ movement_type         │  "sale", "restock", "loss", "adjustment"
    │ quantity              │
    │ timestamp (IDX)       │  ← Movement time
    │ notes                 │
    └───────────────────────┘

    ┌─────────────────────────────┐
    │ product_location_history    │  Location-based stock tracking for heatmap
    ├─────────────────────────────┤
    │ id (PK)                     │
    │ product_id (FK)             │
    │ grid_x, grid_y              │  50cm grid cells
    │ x_center, y_center          │
    │ max_items_seen              │
    │ current_count               │
    │ last_updated                │  ← Timestamp of last update
    └─────────────────────────────┘
```

### Key Timestamp Fields

| Table | Timestamp Field | Purpose | Indexed |
|-------|----------------|---------|---------|
| `detections` | `timestamp` | When RFID detection occurred | ✓ |
| `uwb_measurements` | `timestamp` | When UWB distance measured | ✓ |
| `tag_positions` | `timestamp` | When position calculated | ✓ |
| `inventory_items` | `last_seen_at` | Last time item was detected as present | ✗ |
| `inventory_items` | `created_at` | When item first entered system | ✗ |
| `products` | `created_at` | When product added to catalog | ✗ |
| `anchors` | `created_at` | When anchor configured | ✗ |
| `stock_levels` | `last_restock_at` | Last restock event | ✗ |
| `purchase_events` | `purchased_at` | When item was sold | ✓ |
| `stock_snapshots` | `timestamp` | Snapshot capture time | ✓ |
| `stock_movements` | `timestamp` | Movement event time | ✓ |

**Note:** All timestamp fields store UTC datetime values. Indexed timestamps enable efficient time-range queries for analytics and historical data retrieval.

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

# Copy environment example and configure
cp .env.example .env
# Edit .env with your database credentials

# Start all services
docker compose up -d

# Verify services are running
docker compose ps

# Generate inventory (simulation mode)
python3 -m simulation.generate_inventory --items 3000
```

### Service Ports

| Service | Port | URL |
|---------|------|-----|
| Frontend | 3000 | http://localhost:3000 |
| Backend API | 8000 | http://localhost:8000 |
| Backend WebSocket | 8000 | ws://localhost:8000/ws/live |
| API Documentation | 8000 | http://localhost:8000/docs |
| Simulation Database | 5432 | postgresql://localhost:5432/optiflow_simulation |
| Production Database | 5433 | postgresql://localhost:5433/optiflow_production |

---

## Configuration

### Environment Variables

Create a `.env` file in the project root (see `.env.example`):

```bash
# Database
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_secure_password

# MQTT Broker
MQTT_BROKER_HOST=host.docker.internal
MQTT_BROKER_PORT=1883

# API
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/live
```

### Anchor Configuration

1. Open the dashboard at http://localhost:3000
2. Click "Setup Mode" in the header
3. Click on the map to place anchors at physical locations
4. Minimum 2 anchors required, 4 recommended for optimal accuracy
5. Click "Finish Setup" when complete

---

## Usage

### Running the Simulation

**Via Admin Panel (Recommended)**

1. Navigate to Admin Panel
2. Ensure Mode is set to "SIMULATION"
3. Click "Clear Data" to remove any existing inventory
4. Set item count (50-5000) and click "Generate Items"
5. Click "Start Simulation"

**Via Command Line**

```bash
# Generate inventory
python3 -m simulation.generate_inventory --items 5000

# Run simulation
python3 -m simulation.main --analytics --speed 2.0
```

**Important:** "Generate Items" always ADDS to existing inventory. Always clear data first for a fresh start.

### Dashboard Features

**Store Map**
- Blue circle: Employee position (UWB triangulated)
- Dashed circle: RFID detection range (0.6m)
- Green dots: Present items (displays last known position)
- Red dots: Missing items (last position before becoming not present)
- Orange diamonds: UWB anchors

**Heatmap Mode**
- Toggle with "Heatmap" button
- Green: Full stock at location
- Yellow/Orange: Partial depletion
- Red: Significant missing items

**Admin Panel**
- Mode toggle: Switch between simulation and production hardware
- Item count: Configure number of items for simulation (50-5000)
- Start/Stop: Control simulation execution
- Clear Data: Completely removes all products and inventory items from database
- Generate Items: Creates new inventory (requires database to be empty first)

### Generating Historical Data

```bash
# Generate 30 days of analytics data
python3 -m simulation.backfill_history --days 30 --density normal

# Generate high-density data for testing
python3 -m simulation.backfill_history --days 7 --density dense
```

---

## API Reference

### WebSocket Connection

```
WS /ws/live
```

Real-time WebSocket endpoint for receiving live position and item updates. Clients connect to this endpoint to receive broadcasts of:
- `position_update`: Employee position changes with confidence scores
- `item_update`: Inventory item status and position changes
- `detection_update`: RFID detection events

Example WebSocket message:
```json
{
  "type": "position_update",
  "data": {
    "timestamp": "2025-12-09T10:00:00Z",
    "tag_id": "employee",
    "x": 423.5,
    "y": 287.2,
    "confidence": 0.87,
    "num_anchors": 4
  }
}
```

### Data Ingestion

```
POST /data
```

Receives detection and UWB measurement data from hardware or simulation. Each data packet includes a timestamp that is stored with all readings for historical tracking. After processing, broadcasts updates to all connected WebSocket clients.

Request body:
```json
{
  "timestamp": "2025-12-08T10:00:00Z",
  "detections": [
    {
      "product_id": "E200001234567890ABCD",
      "product_name": "Product Name",
      "x_position": 400,
      "y_position": 300
    }
  ],
  "uwb_measurements": [
    {
      "mac_address": "0x0001",
      "distance_cm": 245.5,
      "status": "0x01"
    }
  ]
}
```

Response:
```json
{
  "detections_stored": 1,
  "uwb_measurements_stored": 4,
  "position_calculated": true,
  "calculated_position": {
    "tag_id": "employee",
    "x": 423.5,
    "y": 287.2,
    "confidence": 0.87
  }
}
```

### Position Tracking

```
GET /positions/latest?limit=10
```

Returns latest calculated employee positions with timestamps.

### Inventory

```
GET /data/items          # All inventory items
GET /data/missing        # Only items marked as "not present"
DELETE /data/clear       # Clear all tracking data
GET /items/{rfid_tag}    # Specific item details
```

### Anchor Management

```
GET /anchors             # List all anchors
POST /anchors            # Create anchor
PUT /anchors/{id}        # Update anchor
DELETE /anchors/{id}     # Delete anchor
```

### Product Management

```
GET /products                    # List all products
GET /products/with-stock         # Products with stock level info
POST /products                   # Create product
PUT /products/{id}               # Update product
GET /products/{id}               # Get product details
GET /products/{id}/items         # Get all items for product
POST /products/{id}/adjust-stock # Adjust stock with timestamp
POST /products/populate-stock    # Initialize stock_levels table
```

### Analytics Endpoints

```
GET /analytics/overview                   # Summary metrics
GET /analytics/stock-heatmap              # Stock depletion by location
GET /analytics/purchase-heatmap           # Purchase locations
GET /analytics/top-products               # Best performing products
GET /analytics/category-performance       # Performance by category
GET /analytics/stock-trends/{product_id}  # Historical trends
GET /analytics/slow-movers                # Slow-moving inventory
GET /analytics/product-velocity           # Sales velocity metrics
GET /analytics/ai/demand-forecast         # ML-based demand prediction
GET /analytics/ai/abc-analysis            # ABC inventory classification
GET /analytics/ai/clustering              # Product clustering
GET /analytics/ai/product-affinity        # Products purchased together
POST /analytics/snapshot                  # Create stock snapshot
POST /analytics/purchase-event            # Record purchase
POST /analytics/stock-movement            # Record stock movement
```

### Simulation Control

```
GET /simulation/status              # Current simulation state
GET /simulation/connection-status   # MQTT connection status
POST /simulation/start              # Start simulation
POST /simulation/stop               # Stop simulation
POST /simulation/generate-inventory # Generate new inventory
PUT /simulation/params              # Update simulation parameters
GET /simulation/logs                # View simulation logs
POST /simulation/hardware/control   # Control hardware (START/STOP)
```

### Configuration

```
GET /config/mode             # Current mode (simulation/production)
POST /config/mode/switch     # Switch mode
GET /config/store            # Store dimensions
PUT /config/store            # Update store config
GET /config/layout           # Store layout info
GET /config/validate-anchors # Check anchor configuration
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
│   │   ├── websocket_manager.py # WebSocket manager
│   │   ├── config.py          # App settings
│   │   ├── routers/           # API route handlers
│   │   └── services/          # Business logic
│   ├── migrations/            # SQL migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                   # Next.js frontend
│   ├── app/
│   │   ├── page.tsx           # Main dashboard
│   │   ├── layout.tsx         # App layout
│   │   ├── analytics/         # Analytics page
│   │   ├── admin/             # Admin panel
│   │   ├── hooks/             # React hooks
│   │   └── components/        # UI components
│   ├── package.json
│   └── Dockerfile
├── mqtt_bridge/               # MQTT to HTTP bridge
│   ├── mqtt_to_api.py
│   ├── requirements.txt
│   └── Dockerfile
├── simulation/                # Python simulation
│   ├── main.py               # CLI entry point
│   ├── config.py             # Configuration
│   ├── inventory.py          # Item generation
│   ├── shopper.py            # Movement simulation
│   ├── scanner.py            # RFID/UWB simulation
│   ├── analytics_tracker.py  # Analytics collection
│   ├── generate_inventory.py # Inventory generator
│   └── backfill_history.py   # Historical data
├── firmware/                  # ESP32 firmware
│   └── code_esp32/
├── tests/                     # Test suite
├── docker-compose.yml
└── README.md
```

### Database Schema

**Core Tracking Tables:**
- `detections` - Timestamped RFID detection events (append-only log)
- `uwb_measurements` - Timestamped UWB distance readings (append-only log)
- `tag_positions` - Calculated employee positions with timestamps (append-only log)
- `anchors` - UWB anchor physical locations

**Inventory Tables:**
- `products` - Master product catalog
- `inventory_items` - Individual RFID-tagged items with status and last seen timestamp
- `stock_levels` - Aggregated stock counts per product

**Analytics Tables:**
- `purchase_events` - Sales events with timestamps
- `stock_snapshots` - Periodic stock level captures
- `stock_movements` - Individual movement events (sale, restock, loss)
- `product_location_history` - Location-based stock tracking for heatmap

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Run all tests
cd tests
python run_tests.py
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
docker compose restart postgres-simulation postgres-production
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

## Key Concepts

### Real-time Updates via WebSocket

Live position and item updates are broadcast to connected clients:

1. **WebSocket Connection:**
   - Frontend establishes connection to `ws://localhost:8000/ws/live`
   - Connection managed by `useWebSocket` React hook with auto-reconnect
   - Multiple clients can connect simultaneously

2. **Broadcast Flow:**
   - Backend processes incoming data (RFID + UWB)
   - Calculates employee position via triangulation
   - Updates inventory item status and positions
   - Broadcasts updates to all connected clients
   - Frontend re-renders map in real-time

3. **Message Types:**
   - `position_update`: Employee position with confidence and timestamp
   - `item_update`: Batch of inventory items with current status and positions
   - `detection_update`: Raw RFID detection events

### Timestamp Tracking

All readings are stored with precise timestamps for complete historical tracking:

1. **Data Ingestion Flow:**
   - MQTT bridge generates UTC timestamp
   - Timestamp stored with every detection, UWB measurement, and position

2. **Persistence Strategy:**
   - Core tables are append-only logs
   - Timestamp fields are indexed for efficient queries
   - `last_seen_at` updated only when item status is "present"

3. **Analytics Usage:**
   - Time-series queries for stock trends
   - Historical movement tracking
   - Purchase event analysis
   - Demand forecasting based on timestamped data

### Display Logic

Map displays last known positions:
- Items are shown at their last detected position
- All items display their most recent (x, y) coordinates from `inventory_items` table
- Missing items are identified by the missing detection algorithm, not by a status field

### Missing Item Detection

The system uses an intelligent inference algorithm to detect missing items with 5 safety checks to prevent false positives:

#### How It Works

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MISSING ITEM DETECTION FLOW                       │
└─────────────────────────────────────────────────────────────────────┘

    1. Hardware Packet Arrives (RFID + UWB Data)
                    │
                    ▼
    2. Calculate Employee Position (Triangulation)
                    │
                    ▼
    3. Query ALL Present Items with Known Positions
                    │
                    ▼
    4. For Each Item in Database:
       │
       ├─► Was it detected in packet? ──YES──► Reset miss counter
       │                                │
       │                               NO
       │                                │
       └─► Calculate Distance to Employee Position
           │
           ├─► Distance > 50cm? ──YES──► Reset miss counter (too far)
           │                      
           NO (within 50cm)
           │
           ▼
       ┌─────────────────────────────────────────────────────┐
       │          5 SAFETY CHECKS APPLIED                     │
       ├─────────────────────────────────────────────────────┤
       │ ✓ CHECK 1: Only items within 50cm range            │
       │ ✓ CHECK 2: Increment consecutive miss counter       │
       │ ✓ CHECK 3: Mark missing only after threshold met   │
       │ ✓ CHECK 4: Max 2 items marked missing per scan     │
       └─────────────────────────────────────────────────────┘
                    │
                    ▼
           Item Marked as "not present"
           Miss counter reset
```

#### Key Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `CLOSE_RANGE_CM` | 50 cm | Maximum distance to consider for inference |
| `MIN_CONSECUTIVE_MISSES` | 4 | Minimum misses before marking missing |
| `MAX_INFERENCES_PER_PASS` | 2 | Maximum items marked missing per scan |

#### Example Timeline

```
Packet #1 arrives (Employee at x=400, y=300)
├─ Item A (RFID: E200...001) at (405, 295) - Distance: 7cm
│  └─ NOT detected → Miss count: 1/4 → Still in inventory
├─ Item B (RFID: E200...002) at (420, 310) - Distance: 24cm
│  └─ Detected ✓ → Miss count: 0/4 → Still in inventory
└─ Item C (RFID: E200...003) at (380, 290) - Distance: 22cm
   └─ NOT detected → Miss count: 1/5 → Still in inventory

Packet #2 arrives (Employee at x=402, y=298)
├─ Item A at (405, 295) - Distance: 5cm
│  └─ NOT detected → Miss count: 2/4 → Still in inventory
├─ Item B at (420, 310) - Distance: 26cm
│  └─ Detected ✓ → Miss count: 0/4 → Still in inventory
└─ Item C at (380, 290) - Distance: 24cm
   └─ NOT detected → Miss count: 2/4 → Still in inventory

Packet #3 arrives (Employee at x=398, y=302)
├─ Item A at (405, 295) - Distance: 11cm
│  └─ NOT detected → Miss count: 3/4 → Still in inventory
├─ Item B at (420, 310) - Distance: 24cm
│  └─ NOT detected → Miss count: 1/4 → Still in inventory
└─ Item C at (380, 290) - Distance: 22cm
   └─ NOT detected → Miss count: 3/4 → Still in inventory

Packet #4 arrives (Employee at x=400, y=300)
├─ Item A at (405, 295) - Distance: 7cm
│  └─ NOT detected → Miss count: 4/4 ❌ THRESHOLD MET
│     └─ Marked as missing (removed from inventory)
├─ Item B at (420, 310) - Distance: 24cm
│  └─ NOT detected → Miss count: 2/4 → Still in inventory
└─ Item C at (380, 290) - Distance: 22cm
   └─ NOT detected → Miss count: 4/4 ❌ THRESHOLD MET
      └─ Marked as missing (removed from inventory)
```

#### Important Notes

- **Database Query Scope**: Every packet triggers a query of ALL present items with known positions (potentially thousands of items)
- **Persistent Counters**: Miss counters persist across packets using function-level attributes (`receive_data._detection_misses`)
- **Randomized Thresholds**: Each item gets a random threshold (3-5 misses) to add variability and prevent synchronized mass disappearance
- **Distance-Based**: Only items within 50cm of employee position are considered for inference
- **Rate Limiting**: Maximum 2 items can be marked missing per scan to prevent mass false positives
- **Counter Reset**: Miss counter resets to 0 when item is detected OR when employee moves too far away (>50cm)

#### Why This Approach?

The multi-layered safety system balances sensitivity and reliability:
- **High Sensitivity**: Detects items within 50cm that aren't scanned (theft, removal)
- **Low False Positives**: Multiple consecutive misses required before marking missing
- **Adaptive**: Randomized thresholds prevent edge cases where all items disappear simultaneously
- **Scalable**: Works with large inventories (1000+ items) by filtering on proximity first

### Mode Switching

The system supports two operational modes:
- **SIMULATION**: Uses internal Python simulator via MQTT (database: port 5432)
- **PRODUCTION**: Connects to real ESP32 hardware via MQTT (database: port 5433)

Switch modes via Admin Panel or `POST /config/mode/switch` endpoint.

---

## License

MIT License

---

## Support

- Repository: https://github.com/oscardef/optiflow
- Documentation: See `/docs` directory
- API Reference: http://localhost:8000/docs (when running)
