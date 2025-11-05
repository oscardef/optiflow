import paho.mqtt.client as mqtt
import sqlite3
import time

DB_FILE = "esp32_data.db"

# Setup SQLite
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    topic TEXT,
    payload TEXT
)
""")
conn.commit()

def on_message(client, userdata, msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    payload = msg.payload.decode()
    print(f"[{ts}] {msg.topic}: {payload}")
    cursor.execute("INSERT INTO messages (timestamp, topic, payload) VALUES (?, ?, ?)",
                   (ts, msg.topic, payload))
    conn.commit()

client = mqtt.Client()
client.on_message = on_message
client.connect("localhost", 1883)
client.subscribe("esp32/test")

print("📡 Listening for ESP32 messages...")
client.loop_forever()
