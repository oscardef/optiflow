# OptiFlow Analytics API - Quick Reference

## Base URL
```
http://localhost:8000
```

## Interactive Docs
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Quick Commands

### View API Documentation
```bash
open http://localhost:8000/docs
```

### Generate Test Data
```bash
# 7 days, normal density (default)
python -m simulation.backfill_history

# 30 days, high traffic
python -m simulation.backfill_history --days 30 --density dense

# Custom configuration
python -m simulation.backfill_history --days 14 --density sparse
```

### Run Simulation with Analytics
```bash
# Enable real-time analytics tracking
python -m simulation.main --analytics

# Custom snapshot interval (10 minutes)
python -m simulation.main --analytics --snapshot-interval 600
```

---

## Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analytics/overview` | GET | Dashboard summary with key metrics |
| `/analytics/product-velocity` | GET | Product turnover rates |
| `/analytics/top-products` | GET | Best performing products |
| `/analytics/category-performance` | GET | Sales by category |
| `/analytics/ai/clusters` | GET | K-means product clustering |
| `/analytics/ai/forecast/{id}` | GET | Demand forecasting |
| `/analytics/ai/anomalies` | GET | Anomaly detection |
| `/analytics/bulk/purchases` | POST | Bulk upload purchase events |
| `/analytics/bulk/snapshots` | POST | Bulk upload stock snapshots |

---

## Quick Examples

### Get Overview (cURL)
```bash
curl http://localhost:8000/analytics/overview | jq
```

### Get Top Products (Python)
```python
import requests
r = requests.get('http://localhost:8000/analytics/top-products?limit=5')
print(r.json())
```

### Get Forecast (JavaScript)
```javascript
const res = await fetch('http://localhost:8000/analytics/ai/forecast/15?days_ahead=7');
const forecast = await res.json();
console.log(forecast);
```

### Bulk Upload (cURL)
```bash
curl -X POST http://localhost:8000/analytics/bulk/purchases \
  -H "Content-Type: application/json" \
  -d '[{"product_id": 1, "purchased_at": "2025-11-30T10:00:00Z"}]'
```

---

## Common Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | int | 7 | Analysis period in days |
| `limit` | int | 10 | Max results to return |
| `n_clusters` | int | 4 | Number of clusters |
| `days_ahead` | int | 7 | Forecast horizon |
| `lookback_days` | int | 7 | Anomaly detection period |

---

## Response Format

### Success
```json
{
  "data": {...},
  "timestamp": "2025-11-30T10:30:00Z"
}
```

### Error
```json
{
  "status": "error",
  "message": "Product not found",
  "code": 404
}
```

---

## Data Generation Presets

| Preset | Purchases/Day | Snapshots/Day | Use Case |
|--------|---------------|---------------|----------|
| `sparse` | 20 | 4 | Quick testing |
| `normal` | 50 | 8 | Typical usage |
| `dense` | 100 | 24 | Heavy traffic |
| `extreme` | 200 | 24 | Stress testing |

---

## Testing Checklist

- [ ] Generate test data: `python -m simulation.backfill_history --days 7`
- [ ] Verify data: Check `/analytics/overview`
- [ ] View docs: Open http://localhost:8000/docs
- [ ] Test AI endpoints: `/analytics/ai/clusters`
- [ ] Run simulation: `python -m simulation.main --analytics`
- [ ] Check analytics page: http://localhost:3000/analytics

---

## Database Queries

### Check Purchase Count
```sql
SELECT COUNT(*) FROM purchase_events;
```

### Check Snapshot Count
```sql
SELECT COUNT(*) FROM stock_snapshots;
```

### Recent Purchases
```sql
SELECT * FROM purchase_events 
ORDER BY purchased_at DESC 
LIMIT 10;
```

Run via:
```bash
docker compose exec postgres-simulation psql -U optiflow -d optiflow_simulation -c "YOUR_QUERY"
```

---

## Performance Tips

1. **Cache results** (30-60 seconds TTL)
2. **Use parallel requests** for independent data
3. **Limit result sets** with `limit` parameter
4. **Batch operations** for bulk uploads
5. **Monitor response times** in production

---

## Support Resources

- **Full Guide**: `/docs/API_INTEGRATION_GUIDE.md`
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **GitHub**: https://github.com/oscardef/optiflow
