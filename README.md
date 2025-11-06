# OptiFlow: ESP32-Powered Shelf Inventory Simulation (v1.0)

This project simulates a real-time RFID shelf inventory system using an ESP32-S3 microcontroller communicating over MQTT with a Python visualization and logging tool on macOS.

The ESP32 moves along a virtual aisle, scanning nearby items on two shelves. Python receives MQTT messages, logs data to a CSV, and visualizes detected and missing items in real time.

---

## Overview

**Components**

* ESP32-S3: Simulated moving RFID scanner publishing detections via MQTT
* Mosquitto: Local MQTT broker on macOS (port 1883)
* Python (`live_inventory_logger.py`): Receives, logs, and visualizes shelf data
* CSV Log (`rfid_data_log.csv`): Stores all scans with timestamps and detections

**Features**

* Real-time data stream from ESP32 via MQTT
* Live matplotlib visualization of scanner and items
* Items fade to gray if not detected recently
* Missing items shown in red
* Auto logging to CSV per session
* Two shelves at y = 3.75 and y = 3.85; scanner path at y = 3.8

---

## Project Structure

```
.
├── live_inventory_logger.py   # Main Python visualization and logger
├── mqtt_receiver.py           # Basic MQTT receiver
├── esp32_data.db              # Optional SQLite database (future use)
├── rfid_data_log.csv          # CSV log file
├── dashboard.py               # Planned dashboard interface
├── README.md                  # Documentation
└── esp32_inventory.ino        # ESP32 firmware
```

---

## Setup

### MQTT Broker (macOS)

Install Mosquitto:

```bash
brew install mosquitto
```

Configure:

```bash
sudo nano /opt/homebrew/etc/mosquitto/mosquitto.conf
```

Add at the end:

```
listener 1883 0.0.0.0
allow_anonymous true
```

Restart service:

```bash
brew services restart mosquitto
```

---

### ESP32 Firmware

1. Open `esp32_inventory.ino` in Arduino IDE.
2. Select **ESP32S3 Dev Module**.
3. Update credentials:

```cpp
const char* ssid = "Oscar";
const char* password = "password";
const char* mqtt_server = "172.20.10.3";
```

4. Upload and open Serial Monitor at 115200 baud.

Expected output:

```
Connecting to WiFi...
Connected to WiFi!
ESP32 IP: 172.20.10.2
Connecting to MQTT...connected!
Received START signal from server!
{"timestamp":12345,"location":{"x":2.15,"y":3.8},"detections":[...]}
```

---

### Python Visualization

Install dependencies:

```bash
pip install paho-mqtt matplotlib
```

Run:

```bash
python3 live_inventory_logger.py
```

Behavior:

* Waits for ESP32 readiness.
* Sends START message.
* Displays moving scanner and shelf items.

Legend:

* Green circle: Scanner
* Blue square: Recently seen item
* Gray square: Stale item
* Red cross: Missing item

---

## Technical Details

**Movement:** ESP32 moves from x = 2.1 → 2.6 at y = 3.8.

**Shelves:** Items alternate between y = 3.75 and y = 3.85 with ±0.005m noise.

**Detection:** Items within 0.05m of scanner are detected (2D Euclidean distance).

**Logging:** Each detection is written to `rfid_data_log.csv` with timestamp, position, and item data.

**Visualization:** Updated every 0.4s, items fade to gray if unseen for 8s.

---

## Parameters

| Parameter     | Location     | Default | Description              |
| ------------- | ------------ | ------- | ------------------------ |
| `step_size`   | ESP32 sketch | 0.025   | Movement step size       |
| `dist < 0.05` | ESP32 sketch | 0.05    | Detection range          |
| `FADE_TIME`   | Python       | 8       | Fade duration in seconds |
| `delay(300)`  | ESP32 sketch | 300 ms  | Delay per step           |

---

## Troubleshooting

| Issue                               | Fix                                   |
| ----------------------------------- | ------------------------------------- |
| No data in Python                   | Check MQTT broker config and IP       |
| Python stuck on "Waiting for ESP32" | Reboot ESP32 or check MQTT topics     |
| Items not visible                   | Increase detection radius slightly    |
| Mosquitto connection refused        | Add `listener 1883 0.0.0.0` to config |
