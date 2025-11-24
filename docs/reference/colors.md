# Stock Depletion Heatmap - Color Reference Guide

## Color Gradient Scale

The heatmap uses an intuitive color gradient that transitions smoothly based on depletion percentage:

### Green Zone (0-15% Depleted) - Fully Stocked ✅
**RGB(34, 197, 94)** - Vibrant Green
- **Meaning**: All or nearly all items present
- **Action**: No action needed
- **Example**: 7/7 items present = 0% depleted

### Yellow Zone (15-40% Depleted) - Slight Depletion ⚠️
**RGB(234, 179, 0)** - Bright Yellow
- **Meaning**: Some items missing but not critical
- **Action**: Monitor situation
- **Example**: 6/8 items present = 25% depleted

### Orange Zone (40-70% Depleted) - Moderate Depletion 🔶
**RGB(251, 146, 60)** - Orange
- **Meaning**: Significant depletion, restock soon
- **Action**: Schedule restock
- **Example**: 3/8 items present = 62.5% depleted

### Red Zone (70-100% Depleted) - Critical 🚨
**RGB(239, 68, 68)** - Bright Red
- **Meaning**: Most or all items missing
- **Action**: Urgent restock needed
- **Example**: 1/10 items present = 90% depleted

## Visual Characteristics

### Smooth Transitions
- No hard boundaries between colors
- Gaussian falloff creates natural-looking gradients
- 20px blur filter ensures seamless blending

### Emphasis for Critical Areas
- Areas with >75% depletion get 1.3x larger radius
- Higher opacity for critical zones
- More saturated colors for urgent attention

### Real-World Interpretation

| Current Stock | Depletion % | Color | Visual Appearance |
|---------------|-------------|-------|-------------------|
| 10/10 items | 0% | Green | Solid vibrant green |
| 9/10 items | 10% | Green | Bright green |
| 7/10 items | 30% | Yellow | Greenish-yellow |
| 5/10 items | 50% | Orange | Yellow-orange |
| 3/10 items | 70% | Red-Orange | Orange-red |
| 1/10 items | 90% | Red | Bright red |
| 0/10 items | 100% | Red | Intense red |

## Current System Status (Example Data)

Based on live data from the system:

### Least Depleted Items
- Fish Oil: 14.3% depleted (6/7) - **Green**
- Sports Drink: 20% depleted (8/10) - **Yellow**
- Badminton Set: 25% depleted (6/8) - **Yellow**

### Most Depleted Items
- Track Pants: 62.5% depleted (3/8) - **Orange**
- Resistance Band: 60% depleted (2/5) - **Orange**
- Hiking Boots: 60% depleted (4/10) - **Orange**

### What Store Managers See
- **Green areas**: Well-stocked sections, no action needed
- **Yellow patches**: Moderately busy areas, monitor regularly
- **Orange zones**: High-traffic areas needing restock
- **Red hotspots**: Critical depletion, immediate attention required

## Design Principles

### 1. Self-Explanatory
No legend needed - colors follow universal conventions:
- Green = Good
- Yellow = Caution
- Orange = Warning
- Red = Urgent

### 2. Gradient Over Discrete Zones
- Smooth transitions show gradual change
- No confusion about threshold boundaries
- Natural appearance like heat/signal maps

### 3. Emphasis on Critical Areas
- Larger visual footprint for urgent issues
- Draws attention where it's needed most
- Prevents critical issues from being overlooked

### 4. Context Through Intensity
- Stronger colors = higher concentration
- Lighter shades = lower concentration
- Transparency shows relative importance

## Technical Implementation

### Color Interpolation
```typescript
// Example: 30% depleted (green-yellow transition)
const depletionPct = 0.30;
const t = (depletionPct - 0.15) / 0.25; // 0.6 through transition

r = 34 + t * (234 - 34)   = 154  // Green → Yellow red channel
g = 197 + t * (179 - 197) = 186  // Green → Yellow green channel  
b = 94 + t * (0 - 94)     = 38   // Green → Yellow blue channel

// Result: RGB(154, 186, 38) - Yellowish-green
```

### Gaussian Falloff
```typescript
const distance = sqrt((x - center_x)² + (y - center_y)²);
const intensity = exp(-distance² / (radius * 0.4)²);
// Creates smooth circular gradients around each location
```

### Blur Application
```typescript
ctx.filter = 'blur(20px)';
// Native canvas blur for hardware-accelerated smoothing
```

## Usage Guidelines

### For Store Managers
1. **Green zones**: Continue normal operations
2. **Yellow zones**: Check stock during next round
3. **Orange zones**: Schedule restock within 24 hours
4. **Red zones**: Immediate investigation and restocking

### For System Operators
1. Monitor overall color distribution
2. Look for expanding red/orange areas
3. Track depletion trends over time
4. Set up alerts for persistent red zones

### For Inventory Planners
1. Identify chronically depleted areas
2. Adjust par levels based on historical maximums
3. Optimize product placement
4. Forecast demand patterns

## Comparison with Previous System

### Before (Zone-Based)
- ❌ Discrete boxes with text
- ❌ Hard to see at a glance
- ❌ Required legend to understand
- ❌ No smooth transitions
- ❌ Binary present/missing view

### After (Gradient Heatmap)
- ✅ Smooth gradients
- ✅ Self-explanatory colors
- ✅ No legend needed
- ✅ Percentage-based accuracy
- ✅ Emphasis on critical areas
- ✅ Beautiful and intuitive

The new heatmap transforms the stock management experience from "reading numbers" to "seeing problems" - making it the core functionality of the entire system.
