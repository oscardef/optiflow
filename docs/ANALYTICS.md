# OptiFlow Analytics System

Comprehensive analytics dashboard with AI-powered insights for inventory optimization and business intelligence.

## Features

### 📊 Standard Analytics
- **Overview Dashboard**: Real-time KPIs (total products, stock value, restock alerts, sales metrics)
- **Product Velocity**: Calculate turnover rates and days until stockout
- **Category Performance**: Sales and revenue breakdown by product category
- **Top Products**: Rankings by sales, revenue, or velocity
- **Stock Trends**: Historical time-series data visualization

### 🤖 AI-Powered Insights
- **K-Means Clustering**: Groups products by velocity, stock level, and pricing patterns
- **Demand Forecasting**: 7-day predictions using exponential smoothing
- **Anomaly Detection**: Z-score analysis to identify unusual sales patterns
- **ABC Analysis**: Product classification by revenue contribution
- **Product Affinity**: Association rule mining for frequently purchased together items

## Architecture

### Backend
- **Models** (`backend/app/models.py`):
  - `StockSnapshot`: Periodic inventory state captures
  - `StockMovement`: Individual stock change events
  
- **AI Service** (`backend/app/services/ai_analytics.py`):
  - Machine learning algorithms (scikit-learn)
  - Statistical analysis (numpy, pandas)
  - No external API dependencies
  
- **Analytics Router** (`backend/app/routers/analytics.py`):
  - 12+ REST endpoints
  - Query parameter configuration
  - Efficient database queries with indexes

### Frontend
- **Components** (`frontend/app/components/`):
  - `AnalyticsOverview`: KPI metric cards
  - `ProductVelocityChart`: Line chart (recharts)
  - `TopProductsTable`: Sortable data table
  - `CategoryDonut`: Pie chart visualization
  - `AIClusterView`: Scatter plot for clustering
  - `DemandForecastChart`: Area chart with confidence bands
  - `AnomalyAlerts`: Alert cards with severity levels

## API Endpoints

### Standard Analytics
```
GET /analytics/overview                    # Dashboard metrics
GET /analytics/product-velocity?days=7     # Velocity calculations
GET /analytics/top-products?metric=sales   # Top performers
GET /analytics/category-performance        # Category aggregations
GET /analytics/stock-trends/{product_id}   # Time-series data
GET /analytics/slow-movers                 # Low velocity products
```

### AI Analytics
```
GET /analytics/ai/clusters?n_clusters=4         # K-means clustering
GET /analytics/ai/forecast/{product_id}         # Demand prediction
GET /analytics/ai/anomalies?lookback_days=7     # Anomaly detection
GET /analytics/ai/abc-analysis                  # Revenue classification
GET /analytics/ai/product-affinity              # Association rules
```

## Setup Instructions

### 1. Database Migration
Run the analytics tables migration:
```bash
# Using psql
psql -U postgres -d optiflow -f backend/migrations/006_analytics_tables.sql

# Or via your migration tool
```

### 2. Install Dependencies
Backend:
```bash
cd backend
pip install -r requirements.txt
```

Frontend (already done):
```bash
cd frontend
npm install recharts
```

### 3. Generate Historical Data (Optional)
For testing with realistic data:
```bash
python -m simulation.backfill_history --days 30 --api http://localhost:8000
```

### 4. Start Services
```bash
# Backend
cd backend
uvicorn app.main:app --reload

# Frontend
cd frontend
npm run dev
```

### 5. Access Analytics
Navigate to: `http://localhost:3000/admin` → Click "Analytics" tab

## Data Refresh

### Automatic
- Frontend auto-refreshes every 30 seconds when analytics tab is active
- Overview KPIs update in real-time

### Manual
- Click "🔄 Refresh Data" button in analytics dashboard
- Periodic snapshots generated on-demand

### Background (Future)
- Add cron jobs or background workers for:
  - Hourly stock snapshots
  - Daily aggregations
  - Model retraining

## Configuration

### Velocity Calculation
Default: 7-day rolling average
Configurable via `days` query parameter:
```bash
/analytics/product-velocity?days=30  # 30-day average
```

### AI Model Parameters
- **Clustering**: `n_clusters=4` (adjustable 2-8)
- **Forecasting**: `days_ahead=7` (1-30 days)
- **Anomalies**: `lookback_days=7` (1-30 days)
- **Affinity**: `min_support=0.05` (0.01-0.5)

## Performance Tips

1. **Database Indexes**: Already created in migration for timestamp queries
2. **Caching**: Consider Redis for expensive queries (>1s)
3. **Pagination**: Top products limited to 20 by default
4. **Aggregations**: Pre-calculate daily summaries for faster queries

## Troubleshooting

### No Data Showing
- Check if products exist: `GET /products`
- Verify purchase events: `SELECT COUNT(*) FROM purchase_events;`
- Run backfill script to generate historical data

### AI Features Not Working
- Install scikit-learn: `pip install scikit-learn`
- Verify import: `python -c "import sklearn; print(sklearn.__version__)"`
- Check logs for model errors

### Slow Queries
- Run `ANALYZE` on tables: `ANALYZE stock_snapshots;`
- Check query plans: `EXPLAIN ANALYZE SELECT ...`
- Add missing indexes if needed

## Future Enhancements

- [ ] Export charts as PNG/PDF
- [ ] Scheduled email reports
- [ ] Custom date range filters
- [ ] Real-time streaming updates (WebSocket)
- [ ] Advanced ML models (LSTM, Prophet)
- [ ] Multi-location aggregations
- [ ] Cost analysis and profitability metrics
- [ ] Seasonal pattern detection

## Technical Details

### Velocity Formula
```
velocity_daily = total_sales / time_period_days
turnover_rate = sales / current_stock
days_until_stockout = current_stock / velocity_daily
```

### Anomaly Detection
Uses Z-score: `z = (x - μ) / σ`
- High severity: |z| > 3
- Medium severity: |z| > 2

### Clustering Features
- Velocity (sales per day)
- Current stock level
- Unit price
- Category encoding (hash)

Normalized with StandardScaler before K-means.

### Forecasting Method
Exponential smoothing: `Ft+1 = α * At + (1-α) * Ft`
- Alpha = 0.3 (weight for recent observations)
- Confidence based on historical variance

## License
Part of OptiFlow RFID/UWB Inventory Management System
