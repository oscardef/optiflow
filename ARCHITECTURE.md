# 🔄 System Architecture & Data Flow

## Complete Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                         ESP32-S3 Device                          │
│  ┌──────────────┐              ┌─────────────────┐             │
│  │ RFID Reader  │              │  DWM3001CDK UWB │             │
│  │ (Future)     │              │  (CLI Firmware) │             │
│  └──────┬───────┘              └────────┬────────┘             │
│         │                               │                       │
│         └───────────┬──────────────────┘                       │
│                     │                                           │
│              ┌──────▼──────┐                                    │
│              │   ESP32-S3  │                                    │
│              │   Firmware  │                                    │
│              └──────┬──────┘                                    │
│                     │                                           │
│                     │ WiFi                                      │
└─────────────────────┼───────────────────────────────────────────┘
                      │
                      ▼
         ┌────────────────────────┐
         │   Mosquitto Broker     │
         │   (MacBook)            │
         │   172.20.10.3:1883     │
         │                        │
         │   Topic: store/aisle1  │
         └────────────┬───────────┘
                      │
                      ▼
         ┌────────────────────────┐
         │   MQTT Bridge          │
         │   (Python)             │
         │   - Subscribes         │
         │   - Forwards to API    │
         └────────────┬───────────┘
                      │ HTTP POST
                      ▼
         ┌────────────────────────┐
         │   FastAPI Backend      │
         │   localhost:8000       │
         │   - Validates data     │
         │   - Stores in DB       │
         └────────────┬───────────┘
                      │
                      ▼
         ┌────────────────────────┐
         │   PostgreSQL           │
         │   localhost:5432       │
         │   - detections         │
         │   - uwb_measurements   │
         └────────────┬───────────┘
                      │
                      ▼
         ┌────────────────────────┐
         │   Next.js Frontend     │
         │   localhost:3000       │
         │   - Dashboard          │
         │   - Real-time view     │
         └────────────────────────┘
```

## 📡 MQTT Topics

| Topic | Direction | Purpose | Message Format |
|-------|-----------|---------|----------------|
| `store/aisle1` | ESP32 → Backend | UWB + RFID data | JSON with `detections` + `uwb_measurements` |
| `store/control` | Backend → ESP32 | Control signals | `"START"` string |
| `store/status` | ESP32 → Backend | Device status | `"ESP32_READY"` string |

## 📦 Message Format

### From ESP32 to Backend

```json
{
  "timestamp": "2024-11-12T15:30:45",
  "detections": [
    {
      "product_id": "RFID_12345",
      "product_name": "Running Shoes"
    }
  ],
  "uwb_measurements": [
    {
      "mac_address": "0x1234",
      "distance_cm": 150.5,
      "status": "SUCCESS"
    },
    {
      "mac_address": "0x5678",
      "distance_cm": 230.8,
      "status": "SUCCESS"
    }
  ]
}
```

**Notes:**
- `detections` is currently empty (RFID not implemented yet)
- `uwb_measurements` contains distance to each anchor
- `distance_cm` is only present when `status` = "SUCCESS"

## 🗄️ Database Schema

### Table: `detections`
```sql
CREATE TABLE detections (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    product_id VARCHAR NOT NULL,
    product_name VARCHAR NOT NULL
);
```

### Table: `uwb_measurements`
```sql
CREATE TABLE uwb_measurements (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    mac_address VARCHAR NOT NULL,
    distance_cm FLOAT NOT NULL,
    status VARCHAR
);
```

## 🔌 Port Mapping

| Service | Host Port | Container Port | Access |
|---------|-----------|----------------|--------|
| PostgreSQL | 5432 | 5432 | `localhost:5432` |
| FastAPI Backend | 8000 | 8000 | `http://localhost:8000` |
| Next.js Frontend | 3000 | 3000 | `http://localhost:3000` |
| Mosquitto MQTT | 1883 | - | `172.20.10.3:1883` |

## 📝 API Endpoints

### `GET /`
Health check
```bash
curl http://localhost:8000/
```
Response:
```json
{"status": "online", "service": "OptiFlow Backend"}
```

### `POST /data`
Receive data packet (used by MQTT bridge)
```bash
curl -X POST http://localhost:8000/data \
  -H "Content-Type: application/json" \
  -d '{"timestamp":"2024-11-12T15:30:00","detections":[],"uwb_measurements":[...]}'
```

### `GET /data/latest?limit=50`
Get recent detections and UWB measurements
```bash
curl http://localhost:8000/data/latest?limit=10
```
Response:
```json
{
  "detections": [...],
  "uwb_measurements": [...]
}
```

### `GET /stats`
Get system statistics
```bash
curl http://localhost:8000/stats
```
Response:
```json
{
  "total_detections": 0,
  "total_uwb_measurements": 42,
  "latest_detection_time": null,
  "latest_uwb_time": "2024-11-12T15:35:00"
}
```

## 🔐 Configuration

### Environment Variables

All configured in `.env` file:

```bash
# Database
POSTGRES_USER=optiflow
POSTGRES_PASSWORD=optiflow_dev
POSTGRES_DB=optiflow

# MQTT Broker (your MacBook IP)
MQTT_BROKER_HOST=172.20.10.3
MQTT_BROKER_PORT=1883
MQTT_TOPIC=store/aisle1

# API
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### ESP32 Configuration

Hardcoded in firmware (`esp32_uwb_simple_mqtt.ino`):

```cpp
const char* ssid = "Oscar";
const char* password = "password";
const char* mqtt_server = "172.20.10.3";

const char* TOPIC_DATA = "store/aisle1";
const char* TOPIC_CONTROL = "store/control";
const char* TOPIC_STATUS = "store/status";
```

## 🚀 Startup Sequence

1. **Start Backend Stack**
   ```bash
   docker compose up -d
   ```
   - PostgreSQL starts and initializes
   - Backend connects to PostgreSQL
   - MQTT bridge connects to Mosquitto
   - Frontend starts

2. **Power On ESP32**
   - Connects to WiFi "Oscar"
   - Gets IP (e.g., 172.20.10.4)
   - Connects to MQTT broker
   - Publishes "ESP32_READY" to `store/status`
   - Waits for START signal

3. **Send START Signal**
   ```bash
   mosquitto_pub -h 172.20.10.3 -t store/control -m 'START'
   ```
   - ESP32 begins publishing UWB data
   - MQTT bridge forwards to backend
   - Backend stores in database
   - Frontend displays data

## 📊 Data Flow Timing

- **UWB Session Rate:** Every 200ms (5Hz)
- **Frontend Refresh:** Every 2 seconds
- **MQTT QoS:** 0 (fire and forget)
- **Database Writes:** Immediate on receive

## 🔮 Future Enhancements

### Phase 1: Core Functionality ✅
- [x] MQTT → Database pipeline
- [x] Basic frontend dashboard
- [x] UWB data collection

### Phase 2: Real-time Features
- [ ] WebSocket for live updates (no polling)
- [ ] Real-time position triangulation
- [ ] Live anchor status monitoring

### Phase 3: RFID Integration
- [ ] Connect RFID reader to ESP32
- [ ] Parse RFID tags
- [ ] Associate items with positions

### Phase 4: Analytics
- [ ] Heatmap visualization
- [ ] Item movement tracking
- [ ] Restock predictions
- [ ] Anomaly detection

### Phase 5: Production
- [ ] Authentication & authorization
- [ ] Multi-store support
- [ ] Mobile app
- [ ] Alert notifications
- [ ] Integration with Decathlon systems
