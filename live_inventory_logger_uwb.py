import paho.mqtt.client as mqtt
import json, time, csv, os
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import math

BROKER = "172.20.10.3"
TOPIC_UWB_RAW = "store/uwb_raw"
TOPIC_CONTROL = "store/control"
TOPIC_STATUS = "store/status"
LOG_FILE = "rfid_data_log.csv"

# Reset CSV with new headers
with open(LOG_FILE, "w", newline="") as f:
    csv.writer(f).writerow(["timestamp", "session_count", "x", "y", "uwb_data", "detections"])
print("[INFO] Log file cleared — waiting for ESP32...")

# Simulated Inventory Items (same as ESP32 had before)
NUM_ITEMS = 50
item_x = []
item_y = []
stock_levels = []
item_map = {}

# Scanner Movement Simulation (moved from ESP32 to Python)
y_fixed = 3.8
x_pos = 2.1
forward = True
x_min, x_max = 2.1, 2.6
step_size = 0.025
initialized = False

uwb_history = []
scanner_position = (2.35, 3.8)
esp_ready = False
FADE_TIME = 8  # seconds to fade to gray

# UWB Anchor positions (TODO: configure these based on actual anchor placement)
ANCHOR_POSITIONS = {
    # Format: "mac_address": (x, y)
    # These will need to be calibrated to your actual setup
}

def initialize_items():
    """Initialize simulated inventory items on two shelves"""
    global item_x, item_y, stock_levels
    import random
    random.seed(42)  # Consistent placement
    
    for i in range(NUM_ITEMS):
        x = x_min + (x_max - x_min) * i / (NUM_ITEMS - 1)
        item_x.append(x)
        
        # Alternate between top shelf (3.85m) and bottom shelf (3.75m)
        if i % 2 == 0:
            y = 3.85 + random.uniform(-0.005, 0.005)  # ±0.5cm variance
        else:
            y = 3.75 + random.uniform(-0.005, 0.005)
        item_y.append(y)
        
        stock_levels.append(2)  # Initial stock count
    
    print(f"[INIT] Initialized {NUM_ITEMS} inventory items on two shelves")

def simulate_movement():
    """Simulate scanner walking along the aisle"""
    global x_pos, forward, initialized, scanner_position
    
    if forward:
        x_pos += step_size
    else:
        x_pos -= step_size
    
    if x_pos >= x_max:
        forward = False
        initialized = True
        print("[SIM] ▶ Reached end of aisle, turning around")
    
    if x_pos <= x_min:
        forward = True
        print("[SIM] ◀ Reached start of aisle, turning around")
    
    scanner_position = (x_pos, y_fixed)
    return scanner_position

def detect_items(scanner_x, scanner_y):
    """Simulate RFID detection based on scanner position"""
    detections = []
    detection_radius = 0.05  # 5cm tight detection
    
    for i in range(NUM_ITEMS):
        dx = item_x[i] - scanner_x
        dy = item_y[i] - scanner_y
        dist = math.sqrt(dx*dx + dy*dy)
        
        if dist < detection_radius:
            item_id = f"EPC{i+1}"
            detections.append({
                "id": item_id,
                "name": f"Item_{i+1}",
                "count": stock_levels[i]
            })
            
            # Occasional depletion
            import random
            if initialized and random.random() < 0.04 and stock_levels[i] > 0:
                stock_levels[i] -= 1
    
    return detections

def triangulate_position(uwb_measurements):
    """
    Calculate position using UWB distance measurements.
    For now, returns simulated position.
    TODO: Implement actual triangulation when anchor positions are known.
    """
    # Placeholder: Use simulated movement
    # In production, this would use trilateration with ANCHOR_POSITIONS
    return simulate_movement()

# MQTT callbacks
def on_message(client, userdata, msg):
    global esp_ready, scanner_position
    topic = msg.topic
    payload = msg.payload.decode()

    if topic == TOPIC_STATUS and payload == "ESP32_READY":
        esp_ready = True
        print("[INFO] ESP32 is ready.")
        return

    if topic == TOPIC_UWB_RAW:
        try:
            payload = json.loads(payload)
            
            # Extract UWB data
            timestamp_ms = payload.get("timestamp", 0)
            session_count = payload.get("session_count", 0)
            uwb_measurements = payload.get("uwb_measurements", [])
            
            # Log UWB measurements
            if uwb_measurements:
                print(f"\n[UWB] Session {session_count}: {len(uwb_measurements)} measurements")
                for uwb in uwb_measurements:
                    mac = uwb.get("mac_address", "unknown")
                    status = uwb.get("status", "unknown")
                    dist = uwb.get("distance_cm", -1)
                    print(f"  - Anchor {mac}: {status} @ {dist}cm")
            
            # Calculate position (triangulation or simulation)
            scanner_x, scanner_y = triangulate_position(uwb_measurements)
            
            # Detect items at current position
            detections = detect_items(scanner_x, scanner_y)
            
            # Store UWB history
            uwb_history.append({
                "time": time.time(),
                "measurements": uwb_measurements,
                "position": (scanner_x, scanner_y)
            })
            
            # Log to CSV
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            uwb_str = "; ".join([f"{u['mac_address']}:{u['distance_cm']}cm" for u in uwb_measurements])
            det_str = "; ".join([f"{d['name']}({d['count']})" for d in detections])
            with open(LOG_FILE, "a", newline="") as f:
                csv.writer(f).writerow([ts, session_count, scanner_x, scanner_y, uwb_str, det_str])
            
            # Update item map with detections
            now = time.time()
            for d in detections:
                iid, name, count = d["id"], d["name"], d["count"]
                
                if iid not in item_map:
                    # Get item's actual position
                    item_idx = int(iid.replace("EPC", "")) - 1
                    item_map[iid] = {
                        "name": name,
                        "x": item_x[item_idx],
                        "y": item_y[item_idx],
                        "status": "present",
                        "last_count": count,
                        "last_seen": now,
                    }
                    print(f"[DETECT] New item: {name} at ({item_map[iid]['x']:.2f}, {item_map[iid]['y']:.2f})")
                else:
                    item = item_map[iid]
                    item["last_seen"] = now
                    
                    if count == 0 and item["status"] != "missing":
                        item["status"] = "missing"
                        print(f"[ALERT] Item missing: {name}")
                    elif count > 0 and item["status"] == "missing":
                        item["status"] = "present"
                        print(f"[DETECT] Item restocked: {name}")
                    
                    item["last_count"] = count
            
            if detections:
                print(f"[DETECT] {len(detections)} items scanned at position ({scanner_x:.2f}, {scanner_y:.2f})")
            
        except Exception as e:
            print(f"[ERROR] Parse failed: {e}")
            import traceback
            traceback.print_exc()

# Initialize items
initialize_items()

# MQTT setup
print("[MQTT] Connecting to broker...")
client = mqtt.Client()
client.on_message = on_message
client.connect(BROKER, 1883, 60)
client.subscribe([(TOPIC_UWB_RAW, 0), (TOPIC_STATUS, 0)])
client.loop_start()
print("[MQTT] Connected and subscribed")

# Wait for ESP32 to be ready
print("[WAIT] Waiting for ESP32 to connect...")
while not esp_ready:
    time.sleep(0.5)
    
print("[CONTROL] ESP32 ready, sending START signal...")
client.publish(TOPIC_CONTROL, "START")
print("[SYSTEM] Simulation running!\n")

# Matplotlib setup
fig, ax = plt.subplots(figsize=(10, 6))

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
    ax.set_xlim(2.0, 2.7)
    ax.set_ylim(3.6, 4.0)
    ax.set_title("UWB + RFID Inventory Tracking System", fontsize=14, fontweight='bold')
    ax.set_xlabel("X Position (m)")
    ax.set_ylabel("Y Position (m)")
    ax.grid(True, alpha=0.3)
    
    # Draw scanner position
    x_user, y_user = scanner_position
    ax.scatter(x_user, y_user, c="lime", s=200, marker="o", 
               edgecolors="darkgreen", linewidths=2, label="Scanner", zorder=5)
    
    # Draw shelf reference lines
    ax.axhline(y=3.75, color='gray', linestyle='--', linewidth=1, alpha=0.3, label='Shelves')
    ax.axhline(y=3.85, color='gray', linestyle='--', linewidth=1, alpha=0.3)
    
    now = time.time()
    present, missing = 0, 0
    
    # Draw items
    for iid, item in list(item_map.items()):
        age = now - item["last_seen"]
        
        if item["status"] == "missing":
            ax.scatter(item["x"], item["y"], c="red", s=80, marker="x", 
                      linewidths=2.5, label="Missing" if missing == 0 else "", zorder=3)
            missing += 1
        else:
            color = fade_color("blue", age, FADE_TIME)
            ax.scatter(item["x"], item["y"], c=[color], s=60, marker="s", 
                      edgecolors="darkblue", linewidths=0.5,
                      label="Detected" if present == 0 else "", zorder=2)
            
            # Glow effect for recently scanned items
            if age < 1.0:
                glow_alpha = 0.4 * (1.0 - age)
                ax.scatter(item["x"], item["y"], c="cyan", s=150, 
                          alpha=glow_alpha, marker="o", linewidths=0, zorder=1)
            
            present += 1
    
    # Status text
    status_text = f"Present: {present} | Missing: {missing}"
    if uwb_history:
        last_uwb = uwb_history[-1]
        uwb_count = len(last_uwb['measurements'])
        status_text += f" | UWB Anchors: {uwb_count}"
    
    ax.text(0.02, 0.98, status_text, transform=ax.transAxes, 
            fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    # Legend
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc="upper right")

ani = FuncAnimation(fig, update, interval=500, cache_frame_data=False)
plt.tight_layout()
plt.show()
