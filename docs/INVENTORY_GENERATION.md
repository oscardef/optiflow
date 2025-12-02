# Inventory Generation Guide

## Overview

OptiFlow now uses a **centralized inventory system** where all products and items are generated once and stored in the database. Both the simulation and analytics backfill use the same inventory, ensuring data consistency.

## Quick Start

### 1. Generate Inventory (First Time Setup)

```bash
# Generate 3000 items with realistic variants
python -m simulation.generate_inventory --items 3000

# Or with custom settings
python -m simulation.generate_inventory --items 5000 --api http://localhost:8000
```

This creates:
- **Hundreds of unique product variants** (sizes, colors, styles)
- **Thousands of RFID-tagged items** distributed across the store
- **Realistic product categories**: Footwear, Apparel, Sports Equipment, Fitness, Accessories, Electronics, Nutrition

### 2. Run Simulation

```bash
# Simulation now uses database inventory
python -m simulation.main --analytics --mode realistic
```

The simulation will:
- Load products and items from the database
- Track shoppers interacting with real inventory
- Generate real-time analytics as items are purchased

### 3. Generate Historical Analytics Data

```bash
# Via command line
python -m simulation.backfill_history --days 30 --density normal

# Or via frontend UI
# Go to Analytics → Generate Data button
```

The backfill will:
- Use the same products from the database
- Generate historical purchase events
- Create stock snapshots for time-series analysis

## Product Generation Details

### Product Templates

The system includes 20+ product templates with realistic variants:

#### Footwear
- Running Shoes: 13 sizes × 7 colors × 5 styles = **455 variants**
- Training Shoes: 7 sizes × 4 colors × 3 styles = **84 variants**
- Basketball Shoes: 7 sizes × 4 colors × 3 styles = **84 variants**

#### Apparel
- Athletic T-Shirts: 6 sizes × 8 colors × 3 styles = **144 variants**
- Athletic Shorts: 6 sizes × 5 colors × 3 styles = **90 variants**
- Hoodies: 5 sizes × 4 colors × 2 styles = **40 variants**
- Yoga Pants: 5 sizes × 5 colors × 3 styles = **75 variants**
- Sports Bras: 5 sizes × 5 colors × 3 styles = **75 variants**

#### Sports Equipment
- Basketballs: 3 sizes × 2 colors × 3 styles = **18 variants**
- Soccer Balls: 3 sizes × 2 colors × 3 styles = **18 variants**

#### Fitness
- Yoga Mats: 3 sizes × 6 colors × 3 styles = **54 variants**
- Dumbbells: 10 weights × 2 colors × 3 styles = **60 variants**
- Resistance Bands: 4 resistance levels × 5 colors × 3 styles = **60 variants**

#### Accessories
- Water Bottles: 4 sizes × 7 colors × 3 styles = **84 variants**
- Gym Bags: 3 sizes × 4 colors × 3 styles = **36 variants**

#### Electronics
- Fitness Trackers: 3 sizes × 4 colors × 3 styles = **36 variants**

#### Nutrition
- Protein Powder: 3 sizes × 4 flavors × 3 types = **36 variants**
- Energy Bars: 3 pack sizes × 4 flavors × 3 types = **36 variants**

### RFID Item Distribution

Each product variant gets multiple physical items:
- **High-demand items** (apparel, basic equipment): 5-15 items each
- **Medium-demand items** (specialized equipment): 3-10 items each
- **Low-demand items** (high-end electronics): 2-6 items each

Items are distributed across realistic store zones:
- Left/Right/Back wall shelves
- Center island displays
- Checkout area (small accessories)

## Command Reference

### generate_inventory.py

```bash
# Basic usage
python -m simulation.generate_inventory --items 3000

# Advanced options
python -m simulation.generate_inventory \
  --items 5000 \
  --api http://localhost:8000 \
  --templates "Running Shoes" "Athletic T-Shirt" \
  --dry-run  # Preview without creating
```

**Parameters:**
- `--items`: Target number of RFID-tagged items (default: 3000)
- `--api`: Backend API URL (default: http://localhost:8000)
- `--templates`: Specific product templates to use (default: all)
- `--dry-run`: Show what would be generated without creating database records

**Output:**
```
🏪 OptiFlow Inventory Generator
===================================================================

📋 Configuration:
   Target items: 3000
   Product templates: 20
   API: http://localhost:8000

🔧 Generating product variants...
   ✅ Generated 1543 unique product variants

📊 Average 1.9 items per product variant

🏷️  Generating RFID-tagged items...
   ✅ Generated 3000 RFID-tagged items

📊 Generation Summary:
   Products: 1543
   Items: 3000
   
   Categories:
     • Footwear: 623 products
     • Apparel: 424 products
     • Sports Equipment: 36 products
     • Fitness: 174 products
     • Accessories: 120 products
     • Electronics: 36 products
     • Nutrition: 72 products
     • Recovery: 58 products

💾 Creating inventory in database...
📦 Creating 1543 products...
   Progress: 1543/1543 (100%)
✅ Created 1543 products

🏷️  Creating 3000 RFID-tagged items...
   Progress: 3000/3000 (100%)

===================================================================
✅ Inventory Generation Complete!
===================================================================
   Products created: 1543
   Items created: 3000

💡 You can now:
   • Run simulation with: python -m simulation.main --analytics
   • Generate analytics data: Visit Analytics → Generate Data
===================================================================
```

### Simulation (main.py)

```bash
# Run with database inventory
python -m simulation.main --analytics --mode realistic

# Custom settings
python -m simulation.main \
  --analytics \
  --mode realistic \
  --speed 2.0 \
  --disappearance 0.02 \
  --snapshot-interval 1800
```

**Parameters:**
- `--analytics`: Enable real-time analytics tracking
- `--mode`: Simulation mode (demo/realistic/stress) - now just affects shopper behavior
- `--speed`: Speed multiplier (0.5-5.0)
- `--disappearance`: Item disappearance rate (default: 0.015 = 1.5%)
- `--snapshot-interval`: Seconds between snapshots (default: 3600)
- `--api`: Backend API URL (default: http://localhost:8000)

### Backfill (backfill_history.py)

```bash
# Generate 30 days of normal density data
python -m simulation.backfill_history --days 30 --density normal

# High traffic store (100 purchases/day)
python -m simulation.backfill_history --days 60 --density dense

# Low traffic store (20 purchases/day)
python -m simulation.backfill_history --days 90 --density sparse

# Maximum data (200 purchases/day)
python -m simulation.backfill_history --days 30 --density extreme
```

**Density Presets:**
- `sparse`: 20 purchases/day, 4 snapshots/day (low traffic)
- `normal`: 50 purchases/day, 8 snapshots/day (default)
- `dense`: 100 purchases/day, 24 snapshots/day (high traffic)
- `extreme`: 200 purchases/day, 24 snapshots/day (very high traffic)

## Architecture

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                   Inventory Generation                       │
│  (generate_inventory.py - Run once)                         │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   │ Creates products & items
                   ▼
         ┌─────────────────────┐
         │  PostgreSQL Database │
         │  - products table     │
         │  - inventory_items    │
         └──────────┬───────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
┌───────────────┐       ┌──────────────────┐
│  Simulation   │       │  Backfill Script │
│  (main.py)    │       │  (backfill.py)   │
├───────────────┤       ├──────────────────┤
│ - Loads items │       │ - Loads products │
│ - Tracks      │       │ - Generates      │
│   shoppers    │       │   historical     │
│ - Real-time   │       │   purchases      │
│   updates     │       │ - Creates        │
│               │       │   snapshots      │
└───────┬───────┘       └────────┬─────────┘
        │                        │
        │ Creates                │ Creates
        ▼                        ▼
┌───────────────────────────────────────────┐
│         Analytics Tables                   │
│  - purchase_events                        │
│  - stock_snapshots                        │
│  - stock_movements                        │
└───────────────────────────────────────────┘
                   │
                   │ Queries
                   ▼
         ┌─────────────────────┐
         │  Analytics Dashboard │
         │  (frontend)          │
         └─────────────────────┘
```

## Database Schema

### Products Table
```sql
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    unit_price NUMERIC(10, 2),
    reorder_threshold INTEGER,
    optimal_stock_level INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

Example:
```json
{
  "id": 1,
  "sku": "RUN-0042",
  "name": "Running Shoes - Pro Black 9",
  "category": "Footwear",
  "unit_price": 92.45,
  "reorder_threshold": 2,
  "optimal_stock_level": 6
}
```

### Inventory Items Table
```sql
CREATE TABLE inventory_items (
    id SERIAL PRIMARY KEY,
    rfid_tag VARCHAR(50) UNIQUE NOT NULL,
    product_id INTEGER REFERENCES products(id),
    status VARCHAR(20) DEFAULT 'present',
    x_position FLOAT,
    y_position FLOAT,
    zone_id INTEGER,
    last_seen_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

Example:
```json
{
  "id": 1,
  "rfid_tag": "RFID-00000042",
  "product_id": 1,
  "status": "present",
  "x_position": 654.32,
  "y_position": 892.15,
  "zone_id": null
}
```

## Best Practices

### 1. Initial Setup
```bash
# 1. Start services
docker compose up -d

# 2. Generate inventory (do this once)
python -m simulation.generate_inventory --items 3000

# 3. Generate historical data
python -m simulation.backfill_history --days 30 --density normal

# 4. Start simulation
python -m simulation.main --analytics
```

### 2. Resetting Inventory

To completely reset and regenerate inventory:

```bash
# 1. Stop simulation
# (Ctrl+C in simulation terminal)

# 2. Clear database (CAUTION: This deletes all data)
docker compose exec postgres-simulation psql -U optiflow -d optiflow_simulation -c "
  TRUNCATE TABLE inventory_items CASCADE;
  TRUNCATE TABLE products CASCADE;
  TRUNCATE TABLE purchase_events CASCADE;
  TRUNCATE TABLE stock_snapshots CASCADE;
"

# 3. Regenerate inventory
python -m simulation.generate_inventory --items 3000

# 4. Regenerate analytics
python -m simulation.backfill_history --days 30 --density normal

# 5. Restart simulation
python -m simulation.main --analytics
```

### 3. Scaling Up

For larger stores:

```bash
# Large store (5000+ items)
python -m simulation.generate_inventory --items 5000

# Department store (10000+ items)
python -m simulation.generate_inventory --items 10000
```

### 4. Custom Product Mix

Generate only specific product types:

```bash
# Footwear store
python -m simulation.generate_inventory --items 2000 \
  --templates "Running Shoes" "Training Shoes" "Basketball Shoes"

# Gym equipment store
python -m simulation.generate_inventory --items 1500 \
  --templates "Dumbbells" "Yoga Mat" "Resistance Bands" "Foam Roller"

# Apparel store
python -m simulation.generate_inventory --items 3000 \
  --templates "Athletic T-Shirt" "Athletic Shorts" "Hoodie" "Yoga Pants"
```

## Troubleshooting

### "No products found in database"

**Cause:** Inventory not generated
**Solution:**
```bash
python -m simulation.generate_inventory --items 3000
```

### "No inventory items found in database"

**Cause:** Items table not populated
**Solution:**
```bash
# Check if products exist
curl http://localhost:8000/products | jq 'length'

# If products exist but items don't, regenerate
python -m simulation.generate_inventory --items 3000
```

### Simulation uses old/different products

**Cause:** Cached product catalog
**Solution:** Simulation now always fetches from database on startup. Restart simulation.

### Backfill generates data for wrong products

**Cause:** Product mismatch (old issue - now fixed)
**Solution:** Backfill now uses same database products. Regenerate:
```bash
python -m simulation.backfill_history --days 30 --density normal
```

### Analytics shows no data

**Possible causes:**
1. No historical data generated
   ```bash
   python -m simulation.backfill_history --days 7 --density normal
   ```

2. Simulation not running with --analytics flag
   ```bash
   python -m simulation.main --analytics
   ```

3. Database connection issue
   ```bash
   docker compose ps  # Check if postgres is running
   docker compose logs postgres-simulation
   ```

## FAQ

**Q: How many products should I generate?**
A: For realistic testing, aim for 1500-3000 products (resulting from template variations). Use `--items 3000` for a medium-sized store.

**Q: Can I add custom product templates?**
A: Yes! Edit `simulation/generate_inventory.py` and add to the `PRODUCT_TEMPLATES` dictionary.

**Q: Does the simulation consume items?**
A: Yes, items transition from "present" to "not present" based on the disappearance rate. This simulates purchases.

**Q: How do I see what the simulation is doing?**
A: Watch the console output or check the Analytics dashboard at http://localhost:3000/analytics

**Q: Can I run multiple simulations?**
A: No, only one simulation should run at a time. Multiple simulations would conflict over item status updates.

**Q: How long does inventory generation take?**
A: For 3000 items with 1500 products: ~2-3 minutes depending on API response time.

**Q: What happens if I generate inventory twice?**
A: The script attempts to create products. Duplicate SKUs will be rejected by the database (unique constraint), so it's safe to run multiple times - only new products will be added.

## Performance Tips

1. **Batch Size**: The generation script creates items in batches of 100 for optimal performance

2. **Database Indexes**: Ensure indexes exist on:
   - `products.sku`
   - `inventory_items.rfid_tag`
   - `inventory_items.product_id`

3. **API Timeout**: If generation fails with timeout errors, increase the timeout in the script or check database performance

4. **Docker Resources**: Ensure Docker has adequate memory (4GB+ recommended for large inventories)

## Next Steps

After generating inventory:
1. Start the simulation: `python -m simulation.main --analytics`
2. Generate historical data via the Analytics UI
3. Monitor real-time updates in the Analytics dashboard
4. Experiment with different density presets to see how data visualization changes
