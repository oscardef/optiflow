# OptiFlow Analytics API Integration Guide

**Version**: 1.0.0  
**Last Updated**: November 30, 2025

## Overview

The OptiFlow Analytics API provides comprehensive inventory analytics including real-time metrics, historical trends, and AI-powered insights. This guide covers integration patterns, example requests, and best practices.

## Quick Start

### Base URL
```
http://localhost:8000
```

### Interactive Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Authentication
Currently no authentication required (add JWT/API keys for production).

---

## Core Analytics Endpoints

### 1. Analytics Overview

Get dashboard summary with key metrics.

**Endpoint**: `GET /analytics/overview`

**Response**:
```json
{
  "total_products": 133,
  "total_stock_value": 45280.50,
  "items_needing_restock": 12,
  "sales_today": 8,
  "sales_last_7_days": 118,
  "sales_last_30_days": 1153,
  "low_stock_products": [
    {
      "product_id": 42,
      "sku": "FOT-015",
      "name": "Tennis Shoes - Size 10",
      "current_stock": 2,
      "reorder_threshold": 5,
      "priority_score": 0.85
    }
  ],
  "timestamp": "2025-11-30T10:30:00.000Z"
}
```

**Use Cases**:
- Dashboard homepage
- Executive reports
- Alert systems

**Example (cURL)**:
```bash
curl http://localhost:8000/analytics/overview | jq
```

**Example (Python)**:
```python
import requests

response = requests.get('http://localhost:8000/analytics/overview')
data = response.json()

print(f"Total Stock Value: ${data['total_stock_value']}")
print(f"Items Needing Restock: {data['items_needing_restock']}")
```

**Example (JavaScript/TypeScript)**:
```typescript
const response = await fetch('http://localhost:8000/analytics/overview');
const data = await response.json();

console.log(`Sales Today: ${data.sales_today}`);
console.log(`7-Day Sales: ${data.sales_last_7_days}`);
```

---

### 2. Product Velocity

Calculate product turnover rates.

**Endpoint**: `GET /analytics/product-velocity?days=7`

**Parameters**:
- `days` (optional): Analysis period (default: 7)

**Response**:
```json
[
  {
    "product_id": 15,
    "sku": "SPT-003",
    "name": "Tennis Ball",
    "category": "Sports",
    "velocity_daily": 2.5,
    "total_sold": 18,
    "days_active": 7
  }
]
```

**Use Cases**:
- Identify fast/slow movers
- Inventory optimization
- Reorder planning

**Example**:
```bash
# Get 30-day velocity
curl "http://localhost:8000/analytics/product-velocity?days=30" | jq
```

---

### 3. Top Products

Get best performing products ranked by multiple metrics.

**Endpoint**: `GET /analytics/top-products?days=30&limit=10`

**Parameters**:
- `days` (optional): Analysis period (default: 30)
- `limit` (optional): Number of results (default: 10)

**Response**:
```json
[
  {
    "product_id": 15,
    "sku": "SPT-003",
    "name": "Tennis Ball",
    "category": "Sports",
    "velocity_daily": 2.5,
    "total_sold": 75,
    "revenue": 1875.00,
    "turnover_rate": 0.82,
    "days_until_stockout": 6
  }
]
```

**Metrics Explained**:
- `velocity_daily`: Average units sold per day
- `turnover_rate`: Sales velocity relative to stock (higher = faster)
- `days_until_stockout`: Estimated days until out of stock

---

## AI Analytics Endpoints

### 1. Product Clustering

Group products by similarity using K-means clustering.

**Endpoint**: `GET /analytics/ai/clusters?n_clusters=4`

**Parameters**:
- `n_clusters` (optional): Number of clusters (default: 4)

**Response**:
```json
{
  "clusters": [
    {
      "cluster_id": 0,
      "centroid": [0.75, 0.60, 1.2],
      "size": 32,
      "products": [
        {
          "product_id": 15,
          "sku": "SPT-003",
          "name": "Tennis Ball",
          "category": "Sports"
        }
      ]
    }
  ],
  "n_clusters": 4
}
```

**Use Cases**:
- Inventory segmentation (A/B/C analysis)
- Merchandising strategy
- Price optimization groups

---

### 2. Demand Forecasting

Predict future demand using exponential smoothing.

**Endpoint**: `GET /analytics/ai/forecast/{product_id}?days_ahead=7`

**Parameters**:
- `product_id` (path): Product ID to forecast
- `days_ahead` (optional): Forecast horizon (default: 7)

**Response**:
```json
{
  "product_id": 15,
  "sku": "SPT-003",
  "name": "Tennis Ball",
  "forecast": [
    {"day": 1, "predicted_stock": 14.2},
    {"day": 2, "predicted_stock": 13.8},
    {"day": 3, "predicted_stock": 13.5}
  ]
}
```

**Requirements**:
- Minimum 30 days of historical data recommended
- More data = better accuracy

**Example**:
```python
import requests
import pandas as pd

# Get forecast for product ID 15
response = requests.get('http://localhost:8000/analytics/ai/forecast/15?days_ahead=14')
forecast = response.json()

# Convert to DataFrame for analysis
df = pd.DataFrame(forecast['forecast'])
print(df)
```

---

### 3. Anomaly Detection

Detect unusual stock patterns using Z-score analysis.

**Endpoint**: `GET /analytics/ai/anomalies?lookback_days=7`

**Parameters**:
- `lookback_days` (optional): Analysis period (default: 7)

**Response**:
```json
{
  "anomalies": [
    {
      "product_id": 42,
      "sku": "FOT-015",
      "name": "Tennis Shoes - Size 10",
      "current_stock": 2,
      "z_score": -2.5,
      "severity": "high",
      "message": "Stock level unusually low"
    }
  ],
  "total_anomalies": 5
}
```

**Use Cases**:
- Theft detection
- Data quality monitoring
- Urgent restock alerts

---

## Historical Data Endpoints

### 1. Bulk Insert Purchases

Upload historical purchase events for testing/backfill.

**Endpoint**: `POST /analytics/bulk/purchases`

**Request Body**:
```json
[
  {
    "product_id": 42,
    "purchased_at": "2025-11-29T15:30:00Z"
  },
  {
    "product_id": 15,
    "purchased_at": "2025-11-29T16:45:00Z"
  }
]
```

**Response**:
```json
{
  "status": "success",
  "inserted": 500
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/analytics/bulk/purchases \
  -H "Content-Type: application/json" \
  -d '[
    {"product_id": 1, "purchased_at": "2025-11-29T10:00:00Z"},
    {"product_id": 2, "purchased_at": "2025-11-29T11:00:00Z"}
  ]'
```

---

### 2. Bulk Insert Snapshots

Upload stock snapshots for time-series analytics.

**Endpoint**: `POST /analytics/bulk/snapshots`

**Request Body**:
```json
[
  {
    "product_id": 42,
    "timestamp": "2025-11-29T12:00:00Z",
    "present_count": 15,
    "missing_count": 2
  }
]
```

**Response**:
```json
{
  "status": "success",
  "inserted": 7448
}
```

**Notes**:
- Processes in batches of 1000
- Timestamps must be ISO 8601 format
- Zone_id is optional

---

## Integration Patterns

### Pattern 1: Dashboard Initialization

```javascript
async function initializeDashboard() {
  // Parallel requests for performance
  const [overview, velocity, topProducts] = await Promise.all([
    fetch('/analytics/overview').then(r => r.json()),
    fetch('/analytics/product-velocity?days=7').then(r => r.json()),
    fetch('/analytics/top-products?limit=10').then(r => r.json())
  ]);
  
  updateDashboard({ overview, velocity, topProducts });
}
```

### Pattern 2: Real-Time Monitoring

```python
import time
import requests

def monitor_stock_anomalies():
    """Check for anomalies every 5 minutes"""
    while True:
        response = requests.get('http://localhost:8000/analytics/ai/anomalies')
        anomalies = response.json()['anomalies']
        
        if anomalies:
            for anomaly in anomalies:
                if anomaly['severity'] == 'high':
                    send_alert(anomaly)
        
        time.sleep(300)  # 5 minutes
```

### Pattern 3: Historical Data Generation

```bash
# Generate 30 days of test data with high density
python -m simulation.backfill_history \
  --days 30 \
  --density dense \
  --api http://localhost:8000
```

---

## Error Handling

### Standard Error Response

```json
{
  "status": "error",
  "message": "Product not found",
  "code": 404
}
```

### Common Status Codes

- `200`: Success
- `400`: Bad request (invalid parameters)
- `404`: Resource not found
- `500`: Internal server error

### Best Practices

```python
import requests

def safe_api_call(url):
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        print("Request timed out")
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error: {e.response.status_code}")
    except Exception as e:
        print(f"Error: {e}")
    return None
```

---

## Rate Limiting & Performance

### Current Limits
- No rate limiting (development mode)
- Add rate limiting for production

### Performance Tips

1. **Use Parallel Requests**: Fetch independent data simultaneously
2. **Cache Results**: Cache analytics data for 30-60 seconds
3. **Pagination**: Use `limit` parameter for large datasets
4. **Batch Operations**: Use bulk endpoints for historical data

### Caching Example

```typescript
class AnalyticsCache {
  private cache = new Map<string, {data: any, expiry: number}>();
  
  async get(endpoint: string, ttl: number = 30000): Promise<any> {
    const cached = this.cache.get(endpoint);
    if (cached && Date.now() < cached.expiry) {
      return cached.data;
    }
    
    const response = await fetch(endpoint);
    const data = await response.json();
    
    this.cache.set(endpoint, {
      data,
      expiry: Date.now() + ttl
    });
    
    return data;
  }
}
```

---

## Testing

### Test Data Generation

```bash
# Generate 7 days of normal density data
python -m simulation.backfill_history --days 7 --density normal

# Generate 30 days of sparse data quickly
python -m simulation.backfill_history --days 30 --density sparse

# Generate 90 days of extreme density
python -m simulation.backfill_history --days 90 --density extreme
```

### Verify Data

```bash
# Check database
docker compose exec postgres-simulation psql -U optiflow -d optiflow_simulation -c \
  "SELECT COUNT(*) FROM purchase_events;"

docker compose exec postgres-simulation psql -U optiflow -d optiflow_simulation -c \
  "SELECT COUNT(*) FROM stock_snapshots;"
```

---

## Production Considerations

### Security

- [ ] Add API key authentication
- [ ] Implement rate limiting
- [ ] Enable HTTPS only
- [ ] Add input validation
- [ ] Sanitize error messages

### Monitoring

- [ ] Add logging for all endpoints
- [ ] Track response times
- [ ] Monitor error rates
- [ ] Set up alerts for anomalies

### Optimization

- [ ] Add database indexes
- [ ] Implement query caching
- [ ] Use connection pooling
- [ ] Add CDN for static assets

---

## Support

- **Documentation**: http://localhost:8000/docs
- **GitHub**: https://github.com/oscardef/optiflow
- **Issues**: https://github.com/oscardef/optiflow/issues

---

## Changelog

### v1.0.0 (2025-11-30)
- Initial release with comprehensive OpenAPI documentation
- Added AI analytics endpoints (clustering, forecasting, anomalies)
- Bulk data upload endpoints for testing
- Real-time analytics tracking during simulation
