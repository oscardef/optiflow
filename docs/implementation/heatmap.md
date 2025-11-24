# Stock Depletion Heatmap - Implementation Summary

## Overview
Implemented a robust percentage-based stock depletion heatmap as the core visualization feature of the OptiFlow inventory management system. The heatmap provides intuitive visual feedback about stock levels using a smooth gradient from green (fully stocked) to red (critically depleted).

## Key Features

### 1. Historical Maximum Tracking
- **Database Model**: Added `max_items_seen` field to `StockLevel` model
- **Location History**: Created `ProductLocationHistory` model to track per-product, per-location inventory maximums
- **Automatic Updates**: Backend automatically updates historical maximums when new items are detected

### 2. Depletion Percentage Calculation
- **Formula**: `depletion_percentage = (max_items_seen - current_count) / max_items_seen * 100`
- **0% Depletion**: All items present (fully stocked)
- **100% Depletion**: All items missing (critical)

### 3. Color Gradient System
Intuitive color scale with smooth transitions:
- **0-15%**: Green (#22C55E) - Fully stocked, excellent condition
- **15-40%**: Yellow (#EAB300) - Slightly depleted, monitor
- **40-70%**: Orange (#FB923C) - Moderately depleted, restock soon
- **70-100%**: Red (#EF4444) - Critically depleted, urgent attention

### 4. Visual Enhancements
- **Gaussian Falloff**: Smooth gradients with `exp(-distance²/(radius*0.4)²)` formula
- **Canvas Blur**: 20px blur filter for seamless transitions
- **Increased Radius**: 1.3x radius for highly depleted areas (>75%) for emphasis
- **Alpha Blending**: Higher opacity for critical depletion areas
- **No Legend**: Self-explanatory visualization requiring no explanation

## Backend Changes

### Modified Files

#### `backend/app/models.py`
```python
# Added to StockLevel model
max_items_seen = Column(Integer, default=0)

# New model for location-based tracking
class ProductLocationHistory(Base):
    __tablename__ = "product_location_history"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    zone_id = Column(Integer, ForeignKey("zones.id"))
    x_center = Column(Float)  # Average X position
    y_center = Column(Float)  # Average Y position
    max_items_seen = Column(Integer, default=0)
    current_count = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "product_id": self.product_id,
            "zone_id": self.zone_id,
            "x_center": self.x_center,
            "y_center": self.y_center,
            "current_count": self.current_count,
            "max_items_seen": self.max_items_seen,
            "items_missing": self.max_items_seen - self.current_count,
            "depletion_percentage": round(
                ((self.max_items_seen - self.current_count) / self.max_items_seen * 100), 
                1
            ) if self.max_items_seen > 0 else 0
        }
```

#### `backend/app/main.py`
Completely rewrote `/analytics/stock-heatmap` endpoint:
- Groups items by product and zone
- Calculates center positions (average x/y)
- Updates or creates `ProductLocationHistory` records
- Automatically updates `max_items_seen` when current total exceeds historical max
- Returns per-location data with depletion percentages

**Response Format**:
```json
[
  {
    "product_id": 6,
    "product_name": "Fish Oil",
    "product_category": "General",
    "zone_id": 3,
    "zone_name": "Aisle 2",
    "x": 425.17,
    "y": 343.08,
    "current_count": 6,
    "max_items_seen": 7,
    "items_missing": 1,
    "depletion_percentage": 14.3
  }
]
```

## Frontend Changes

### Modified Files

#### `frontend/app/components/StoreMap.tsx`

**New `drawSmoothHeatmap()` Function**:
- Takes heatmap data array instead of raw items
- Processes per-location depletion percentages
- Creates intensity map with Gaussian falloff
- Applies color gradient based on depletion percentage
- Uses canvas ImageData for pixel-level manipulation
- Applies blur filter for smooth transitions

**Key Parameters**:
- `baseRadius = 50px`: Base influence radius for each location
- `blur = 20px`: Blur filter strength
- `1.3x radius`: Applied to critically depleted areas (>75%)

**Algorithm Steps**:
1. Create intensity map with Gaussian falloff per location
2. Store depletion percentage (0-1) in red channel
3. Apply canvas blur filter
4. Map depletion percentage to color gradient
5. Adjust alpha for visibility and emphasis
6. Render final colored heatmap

**Removed**:
- Stock Level legend (no longer needed - self-explanatory)
- Legacy zone-based rendering

## Database Schema

### New Table: `product_location_history`
```sql
CREATE TABLE product_location_history (
    id INTEGER PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    zone_id INTEGER REFERENCES zones(id),
    x_center FLOAT,
    y_center FLOAT,
    max_items_seen INTEGER DEFAULT 0,
    current_count INTEGER DEFAULT 0,
    last_updated TIMESTAMP
);
```

### Modified Table: `stock_levels`
```sql
ALTER TABLE stock_levels ADD COLUMN max_items_seen INTEGER DEFAULT 0;
```

## Testing

### Test Heatmap Endpoint
```bash
curl http://localhost:8000/analytics/stock-heatmap | jq '.[0:3]'
```

### Expected Behavior
1. **Fully Stocked Areas**: Show as vibrant green
2. **Partially Depleted**: Smooth gradient through yellow/orange
3. **Critically Depleted**: Bright red with increased visibility
4. **No Items**: Area not rendered on heatmap

### Verification Steps
1. ✅ Backend starts without errors
2. ✅ Database initializes with new schema
3. ✅ `/analytics/stock-heatmap` returns proper data structure
4. ✅ Frontend compiles successfully
5. ✅ Heatmap renders with smooth gradients
6. ✅ Legend removed from UI

## Performance Considerations

### Backend Optimization
- Efficient SQL grouping with `GROUP BY`
- Single database query per request
- Automatic history pruning can be added later

### Frontend Optimization
- Canvas rendering for hardware acceleration
- Pixel manipulation for efficient gradients
- Gaussian calculations limited to radius bounds
- Blur applied once via native canvas filter

## Future Enhancements (Not Yet Implemented)

### 1. Pulsing Animation
Add subtle pulsing effect to areas with >90% depletion:
```typescript
const pulseOpacity = 0.8 + 0.2 * Math.sin(Date.now() / 500);
```

### 2. Max Value Smoothing
Gradual decrease of `max_items_seen` over time:
- Immediate increase when new maximum detected
- Slow decay (e.g., 1 item per week) to adapt to seasonal changes

### 3. Clustering Algorithm
Group nearby items more intelligently:
- Use spatial clustering (e.g., DBSCAN)
- Separate hotspots for same product in different areas

### 4. Historical Trends
Track depletion over time:
- Add `depletion_history` table
- Show trend arrows on heatmap
- Predict future stock issues

### 5. Critical Alerts
Automatic notifications for critical depletion:
- Webhook when depletion > 80%
- Email digest of critical areas
- Integration with restock workflows

## Conclusion

The stock depletion heatmap is now the core visualization feature of OptiFlow. It provides:
- **Intuitive**: No legend needed - colors are self-explanatory
- **Accurate**: Based on historical maximum inventory levels
- **Smooth**: Beautiful gradients with no harsh boundaries
- **Performant**: Efficient rendering with canvas pixel manipulation
- **Actionable**: Clear visual indicators of where attention is needed

The system automatically tracks historical maximums and updates the heatmap in real-time as inventory changes, making it easy to identify stock depletion hotspots at a glance.
