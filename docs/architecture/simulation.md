# OptiFlow Simulation System - Architecture

## Overview
The OptiFlow simulation is a modular system that simulates employee movement, RFID detection, and UWB positioning in a retail store environment. This document details the technical architecture and design decisions.

> **Note**: For basic usage instructions, see the [main README](../../README.md). This document focuses on architectural details.

## System Architecture

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

## Simulation Modes

The system supports three modes optimized for different use cases:

| Mode | Items | Duplicates per SKU | Use Case |
|------|-------|-------------------|----------|
| **demo** | 100 | 1-2 | Quick testing, demos |
| **realistic** | 500 | 5-10 | Development, realistic simulation |
| **stress** | 1000 | 10-20 | Load testing, performance validation |

### Speed Multiplier
Configurable from 0.5x (slow motion) to 5.0x (fast forward) for testing different scenarios.

## Design Decisions

### Why Modular Simulator?
The original monolithic simulator (~650 lines) was refactored into a modular structure:
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

## Component Overview

### Backend Components
- `backend/migrations/001_inventory_system.sql` - Database schema
- `backend/app/prioritization.py` - Priority calculation algorithm
- `backend/app/models.py` - SQLAlchemy models (Products, InventoryItems, StockLevels, etc.)
- `backend/app/main.py` - API endpoints for inventory and analytics

### Simulation Components
- `simulation/main.py` - CLI entry point and orchestrator
- `simulation/config.py` - Configuration management (modes, settings)
- `simulation/inventory.py` - Product catalog and item generation
- `simulation/shopper.py` - Employee movement simulation
- `simulation/scanner.py` - RFID/UWB measurement simulation
- `simulation/restock_listener.py` - Restock task handler

### Frontend Components
- `frontend/app/page.tsx` - Main dashboard with view mode switching
- `frontend/app/components/StoreMap.tsx` - Interactive store map canvas
