import paho.mqtt.client as mqtt
import json, time, csv, os
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

BROKER = "172.20.10.3"
TOPIC = "store/aisle1"
CONTROL_TOPIC = "store/control"
STATUS_TOPIC = "store/status"
LOG_FILE = "rfid_data_log.csv"

# reset CSV
with open(LOG_FILE, "w", newline="") as f:
    csv.writer(f).writerow(["timestamp", "x", "y", "detections"])
print("[INFO] Log file cleared — waiting for ESP32...")

item_map = {}
data = []
esp_ready = False
FADE_TIME = 8  # seconds to fade to gray

# MQTT callbacks
def on_message(client, userdata, msg):
    global esp_ready
    topic = msg.topic
    payload = msg.payload.decode()

    if topic == STATUS_TOPIC and payload == "ESP32_READY":
        esp_ready = True
        print("[INFO] ESP32 is ready.")
        return

    if topic == TOPIC:
        try:
            payload = json.loads(payload)
            x_user = payload["location"]["x"]
            y_user = payload["location"]["y"]
            detections = payload.get("detections", [])
            ts = time.strftime("%Y-%m-%d %H:%M:%S")

            det_str = "; ".join([f"{d['name']}({d['count']})" for d in detections])
            with open(LOG_FILE, "a", newline="") as f:
                csv.writer(f).writerow([ts, x_user, y_user, det_str])

            for d in detections:
                iid, name, count = d["id"], d["name"], d["count"]
                now = time.time()
                if iid not in item_map:
                    # keep ESP's y positions clean (from payload or shelf lines)
                    shelf_y = 3.85 if int(iid.replace("EPC", "")) % 2 == 0 else 3.75
                    item_map[iid] = {
                        "name": name,
                        "x": x_user + (0.02 * ((hash(iid) % 3) - 1)),  # small horizontal jitter for visualization
                        "y": shelf_y,
                        "status": "present",
                        "last_count": count,
                        "last_seen": time.time(),
                    }
                else:
                    item = item_map[iid]
                    item["last_seen"] = now
                    if count == 0:
                        item["status"] = "missing"
                    else:
                        item["status"] = "present"
                    item["last_count"] = count
            data.append((x_user, y_user))
        except Exception as e:
            print(f"[ERROR] Parse failed: {e}")

# MQTT setup
client = mqtt.Client()
client.on_message = on_message
client.connect(BROKER, 1883, 60)
client.subscribe([(TOPIC, 0), (STATUS_TOPIC, 0)])
client.loop_start()

# wait for ESP
while not esp_ready:
    time.sleep(1)
client.publish(CONTROL_TOPIC, "START")
print("[INFO] Sent START signal — simulation running.")

# Matplotlib setup
fig, ax = plt.subplots(figsize=(9, 5))
ax.set_xlim(2.05, 2.65)
ax.set_ylim(3.5, 4.1)
ax.set_title("Shelf Inventory Simulation")
ax.set_xlabel("X Position (m)")
ax.set_ylabel("Y Position (m)")

def fade_color(base_color, age, fade_time):
    """Return faded RGB tuple based on time since last detection."""
    if base_color == "red":  # missing stays red
        return (1.0, 0.2, 0.2)
    ratio = min(max(age / fade_time, 0.0), 1.0)
    # Fade from bright cyan (freshly seen) → gray (stale)
    r = 0.2 + 0.3 * ratio
    g = 1.0 - 0.5 * ratio
    b = 1.0 - 0.4 * ratio
    return (r, g, b)

def update(frame):
    ax.clear()
    ax.set_xlim(2.05, 2.65)
    ax.set_ylim(3.3, 4.3)  # expanded view to show shelves clearly
    ax.set_title("Shelf Inventory Simulation")
    ax.set_xlabel("X Position (m)")
    ax.set_ylabel("Y Position (m)")

    # draw scanner
    if data:
        x_user, y_user = data[-1]
        ax.scatter(x_user, y_user, c="green", s=100, marker="o", label="Scanner")

    now = time.time()
    present, missing = 0, 0

    for iid, item in list(item_map.items()):
        age = now - item["last_seen"]
        if item["status"] == "missing":
            ax.scatter(item["x"], item["y"], c="red", s=45, marker="x", linewidths=2)
            missing += 1
        else:
            color = fade_color("blue", age, FADE_TIME)
            ax.scatter(item["x"], item["y"], c=[color], s=50, marker="s")
            if age < 1.0:  # recently scanned: small glow ring
                ax.scatter(item["x"], item["y"], c="cyan", s=100, alpha=0.2, marker="o", linewidths=0)
            present += 1

    ax.legend([f"Scanner | Present: {present} | Missing: {missing}"], loc="upper right")

ani = FuncAnimation(fig, update, interval=400, cache_frame_data=False)
plt.show()
