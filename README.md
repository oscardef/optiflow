# ESP32 → macOS MQTT Test Bridge

This project establishes a real-time communication bridge between an **ESP32-S3** microcontroller and a **MacBook** running an MQTT broker.
The ESP32 sends test data over Wi-Fi to the broker, which can then be consumed by Python applications for analysis, storage, or visualization.

---

## Project Overview

**Current Stage (v0.1):**

* ESP32-S3 connects to Wi-Fi (mobile hotspot).
* Sends periodic test messages to a local MQTT broker (Mosquitto) running on macOS.
* MacBook receives these messages either via:

  * Terminal (`mosquitto_sub`)
  * Python subscriber (`mqtt_receiver.py`)

**Next stages:**

* Store incoming data in a local/remote database.
* Implement anomaly detection and rule-based logic.
* Add staff notification (Apprise / Firebase).
* Develop a real-time dashboard (Dash / Streamlit).

---

## Prerequisites

* **Hardware:**

  * Waveshare N8R8 ESP32-S3 board
  * USB-C cable
  * Smartphone hotspot (for shared Wi-Fi network)

* **Software:**

  * [Arduino IDE](https://www.arduino.cc/en/software)
  * [Mosquitto MQTT](https://mosquitto.org/)
  * Python 3.9+ with `paho-mqtt` and `sqlite3` (installed by default on macOS)

---

## Part 1 — Running the ESP32 Code

### 1. Plug in the board

Connect the **ESP32-S3** to your Mac via **USB-C**.

### 2. Configure Arduino IDE

* Go to **Tools → Board → ESP32 → ESP32S3 Dev Module**
    * Specifically select:

  ```
  /dev/cu.usbmodem5AB0184...
  ```
* Paste the ESP32 code (from `esp32_mqtt_test.ino`) into a new Arduino sketch.

### 3. Update Wi-Fi credentials

In the sketch:

```cpp
const char* ssid = "YOUR_HOTSPOT_NAME";
const char* password = "YOUR_HOTSPOT_PASSWORD";
const char* mqtt_server = "172.20.10.1"; // Your Mac’s IP on the hotspot network
```

### 4. Upload and open Serial Monitor

* Click **Upload**
* Open **Tools → Serial Monitor**
* Set **baud rate** to `115200`

You should see:

```
Connecting to WiFi...
Connected! IP: 172.20.10.2
Connecting to MQTT...connected!
Sent: Test message #0
Sent: Test message #1
...
```

---

## Part 2 — MQTT Broker (Mosquitto on macOS)

### Installation

```bash
brew install mosquitto
```

### Configuration (one-time)

Open the config file:

```bash
sudo nano /opt/homebrew/etc/mosquitto/mosquitto.conf
```

Append the following lines at the bottom:

```
# Allow ESP32 to connect externally
listener 1883 0.0.0.0
allow_anonymous true
```

Save and restart the service:

```bash
brew services restart mosquitto
```

### Verify broker is running

```bash
netstat -an | grep 1883
```

Expected output:

```
tcp4       0      0  *.1883                 *.*                    LISTEN
```

### Test MQTT manually

In one terminal:

```bash
mosquitto_sub -h localhost -t esp32/test
```

In another:

```bash
mosquitto_pub -h localhost -t esp32/test -m "Hello from Mac!"
```

You should see the message echoed in the subscriber terminal.

### Stop / Restart / Remove

* Stop:

  ```bash
  brew services stop mosquitto
  ```
* Restart:

  ```bash
  brew services restart mosquitto
  ```
* Uninstall (if ever needed):

  ```bash
  brew uninstall mosquitto
  ```

---

## Part 3 — Python MQTT Receiver

### Install dependencies

```bash
pip install paho-mqtt
```

### Run the receiver

```bash
python3 mqtt_receiver.py
```

Expected output:

```
Listening for ESP32 messages...
[2025-11-06 15:14:32] esp32/test: Test message #0
[2025-11-06 15:14:34] esp32/test: Test message #1
...
```

All incoming messages are automatically logged into `esp32_data.db` (SQLite database).

---

## Project Structure

```
.
├── esp32_mqtt_test.ino        # Arduino sketch for ESP32-S3
├── mqtt_receiver.py           # Python MQTT subscriber and logger
├── esp32_data.db              # Auto-created local database
├── README.md                  # Project documentation
└── (future)
    ├── anomaly_engine.py
    ├── notifier.py
    ├── dashboard/
    │   ├── app.py
    │   └── components/
    └── requirements.txt
```

---

## Future Extensions

| Stage             | Module                 | Description                  |
| ----------------- | ---------------------- | ---------------------------- |
| Data Ingestion    | ESP32 + MQTT           | Real-time streaming complete |
| Data Storage      | SQLite / Supabase      | Store messages persistently  |
| Anomaly Detection | PyOD / River           | Detect stock irregularities  |
| Notifications     | Apprise / Firebase FCM | Staff alerts                 |
| Visualization     | Streamlit / Dash       | Interactive dashboard        |

---

## Troubleshooting

| Issue                         | Possible Fix                                                             |
| ----------------------------- | ------------------------------------------------------------------------ |
| `rc=-2` in Serial Monitor     | Check Mosquitto config (`listener 1883 0.0.0.0`), ensure firewall is off |
| ESP32 not connecting to Wi-Fi | Verify hotspot name/password and 2.4GHz band                             |
| No messages in Python         | Confirm same topic (`esp32/test`) and port `1883`                        |
| Mosquitto won’t start         | Check path: `/opt/homebrew/etc/mosquitto/mosquitto.conf`                 |

---

## Notes

* Ensure both **ESP32** and **Mac** are connected to the same **mobile hotspot** network.
* Mac’s IP (for `mqtt_server`) can be found using:

  ```bash
  ifconfig | grep inet
  ```
* When adding new modules (like AI or dashboards), follow the structure above to keep the project modular.
