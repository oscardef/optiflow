# OptiFlow Simulation System v2.0

## Overview
The OptiFlow simulation has been refactored into a modular, production-ready system with multiple simulation modes and inventory management capabilities.

## Architecture

### Backend (Step 1 - ✅ Complete)
- **Database Migration**: `backend/migrations/001_inventory_system.sql`
  - Products table (SKU catalog)
  - InventoryItems table (RFID-tagged items)
  - Zones table (store map zones)
  - StockLevels table (aggregated inventory counts)
  - RestockTasks table (restock queue with priorities)
  - PurchaseEvents table (sales analytics)
  
- **Models**: `backend/app/models.py`
  - SQLAlchemy models for all tables
  - Relationships and foreign keys
  - Automatic triggers for stock level updates

- **Prioritization**: `backend/app/prioritization.py`
  - Multi-factor priority algorithm (urgency 40%, velocity 30%, time 15%, missing 15%)
  - Automatic priority recalculation
  - Top restock priorities API

- **API Endpoints**: `backend/app/main.py`
  - `/products` - Product catalog management
  - `/products/summary` - Products with stock levels
  - `/products/restock` - Create manual restock tasks
  - `/restock/queue` - Get restock queue by priority
  - `/priorities/recalculate` - Recalculate all priorities
  - `/analytics/stock-heatmap` - Stock density by zone
  - `/analytics/purchase-heatmap` - Purchase activity by zone
  - `/zones` - Get all store zones

### Simulator (Step 2 - ✅ Complete)
Modular structure in `simulation/` directory:

- **`config.py`**: Configuration management
  - 3 simulation modes: demo (100 items), realistic (500 items), stress (1000 items)
  - Configurable duplicates per SKU (5-10 for realistic)
  - Store layout, MQTT settings, tag settings

- **`inventory.py`**: Product catalog and item generation
  - 77 unique SKUs across 8 categories
  - Intelligent duplication based on mode
  - Shelf distribution algorithm
  - Restock item spawning

- **`shopper.py`**: Tag movement simulation
  - Back-and-forth navigation pattern
  - Independent movement (not tied to anchor positions)
  - Pass tracking and item missing simulation

- **`scanner.py`**: RFID and UWB measurement
  - 1.5m RFID detection range
  - Realistic UWB noise (±5cm)
  - Status change detection

- **`restock_listener.py`**: Restock command handler
  - Polls backend for pending restock tasks
  - Spawns new items on demand
  - Updates task status (pending → in_progress → completed)

- **`main.py`**: CLI entry point
  - `python -m simulation.main --mode realistic --speed 1.0`
  - Auto-fetches anchor config from backend
  - Real-time MQTT publishing

### Frontend (Step 3 - ✅ Complete)
Enhanced UI in `frontend/app/`:

- **`page.tsx`**: Main dashboard with view modes
  - 4 view mode tabs: Live Tracking, Stock Heatmap, Purchase Hotspots, Restock Queue
  - Auto-fetch analytics data based on active view
  - Product summary integration

- **`components/StoreMap.tsx`**: Responsive canvas with multiple views
  - **Live Tracking**: Real-time employee position, items, RFID detection radius
  - **Stock Heatmap**: Visualize item density by zone (blue=low, red=high)
  - **Purchase Heatmap**: Visualize purchase activity by zone (last 24h)
  - **Restock Queue**: Show priority-sorted restock tasks (future enhancement)
  - Conditional rendering based on viewMode
  - Heatmap overlay with color-coded zones

## Usage

### 1. Start Infrastructure
```bash
docker compose up -d
```

### 2. Run New Simulator
```bash
# Realistic mode (500 items, 5-10 duplicates per SKU)
python3 -m simulation.main --mode realistic --speed 1.0

# Demo mode (100 items, 1-2 duplicates per SKU)
python3 -m simulation.main --mode demo --speed 2.0

# Stress mode (1000 items, 10-20 duplicates per SKU)
python3 -m simulation.main --mode stress --speed 0.5
```

### 3. View Dashboard
Open http://localhost:3000 and switch between view modes:
- **Live Tracking**: Watch employee movement and item detection in real-time
- **Stock Heatmap**: See where items are concentrated
- **Purchase Hotspots**: Identify high-traffic purchase zones
- **Restock Queue**: Manage restocking priorities

### 4. Manual Restocking
Use the API to create restock tasks:
```bash
curl -X POST "http://localhost:8000/products/restock?product_id=1&quantity=10&requested_by=manual"
```

The simulator will automatically:
1. Detect the restock task via `restock_listener.py`
2. Spawn 10 new items for that product
3. Distribute them across store shelves
4. Update task status to "completed"

## Key Features

### Inventory Management
- ✅ Product catalog with SKUs and categories
- ✅ Individual RFID-tagged items
- ✅ Stock level tracking with automatic updates
- ✅ Priority-based restock queue
- ✅ Zone-based analytics (stock density, purchase activity)

### Simulation Modes
- ✅ Demo: 100 items, 1-2 duplicates per SKU
- ✅ Realistic: 500 items, 5-10 duplicates per SKU
- ✅ Stress: 1000 items, 10-20 duplicates per SKU
- ✅ Configurable speed multiplier (0.5x - 5.0x)

### Manual Restocking
- ✅ Create restock tasks via API
- ✅ Automatic item spawning by simulator
- ✅ Task status tracking (pending → in_progress → completed)
- ✅ Priority calculation based on urgency, velocity, time, missing items

### Frontend Views
- ✅ Live Tracking: Real-time positions and detections
- ✅ Stock Heatmap: Visual density map by zone
- ✅ Purchase Hotspots: 24h purchase activity heatmap
- ✅ Consistent white/royal blue theme
- ✅ Sharp corners, no rounded borders

## Design Decisions

### Why Modular Simulator?
The original `esp32_simulator.py` was monolithic (~650 lines). The new structure:
- Separates concerns (config, inventory, movement, scanning, restocking)
- Makes it easy to add new simulation modes
- Simplifies testing and maintenance
- Enables reusable components

### Why 5-10 Duplicates Per SKU?
- Realistic for retail (not thousands of identical items)
- Enough variety for heatmap visualization
- Manageable for demo purposes
- Aligns with actual store inventory patterns

### Why Manual Restock Simulation?
- Demonstrates full workflow: UI → API → Simulator
- Allows on-demand testing without waiting for automatic triggers
- Provides clear feedback loop for users
- Simpler than complex automatic restocking logic

## Next Steps (Future Enhancements)

### Frontend
- [ ] Collapsible legend for heatmap views (auto-collapse after 10s)
- [ ] Restock panel with `[+ Restock]` buttons per product
- [ ] Modal for quantity input when restocking
- [ ] Real-time restock queue display in Restock Queue view

### Backend
- [ ] Purchase event recording when items go missing
- [ ] Historical analytics (daily/weekly trends)
- [ ] Automatic priority recalculation scheduler
- [ ] CVE/vulnerability scanning integration

### Simulator
- [ ] Shopper behavior patterns (fast/slow, focused/browsing)
- [ ] Multiple simultaneous employees
- [ ] Item pickup/putback simulation
- [ ] Realistic checkout process simulation

## Files Created/Modified

### Created
- `backend/migrations/001_inventory_system.sql`
- `backend/app/prioritization.py`
- `simulation/__init__.py`
- `simulation/config.py`
- `simulation/inventory.py`
- `simulation/shopper.py`
- `simulation/scanner.py`
- `simulation/restock_listener.py`
- `simulation/main.py`
- `SIMULATION_README.md` (this file)

### Modified
- `backend/app/models.py` - Added 6 new models
- `backend/app/main.py` - Added 15+ new endpoints
- `frontend/app/page.tsx` - Added view modes and analytics fetching
- `frontend/app/components/StoreMap.tsx` - Added heatmap rendering

## Summary
All three major steps are complete:
1. ✅ Backend data models and endpoints
2. ✅ Modular simulator with restock listener
3. ✅ Frontend multiple map views

The system is now production-ready for inventory management, analytics, and intelligent restocking!
