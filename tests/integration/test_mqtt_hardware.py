#!/usr/bin/env python3
"""
MQTT Data Validator for OptiFlow ESP32 Hardware
================================================
Subscribe to MQTT topics and validate incoming data from ESP32-S3 RFID+UWB hardware.

Validates data format from: rfid_uwb_mqtt.ino
- RFID: JRD-100 UHF RFID reader (EPC, RSSI, PC fields)
- UWB: DWM3001CDK positioning (MAC address, average distance, measurement counts)

Test Type: Integration + Hardware
Requires: MQTT broker running, ESP32 hardware (optional)

Usage:
    python tests/integration/test_mqtt_hardware.py [--broker BROKER] [--port PORT] [--topic TOPIC]

Examples:
    python tests/integration/test_mqtt_hardware.py                          # Use defaults (172.20.10.4)
    python tests/integration/test_mqtt_hardware.py --broker 192.168.1.100   # Custom broker
    python tests/integration/test_mqtt_hardware.py --topic "store/aisle1"   # Specific aisle
    
To start ESP32 publishing, send:
    mosquitto_pub -h 172.20.10.4 -t store/control -m 'START'
"""

import argparse
import json
import sys
from datetime import datetime
from typing import Dict, List, Tuple

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    # Only exit if running as standalone script, not during pytest collection
    if __name__ == "__main__":
        print("❌ paho-mqtt not installed. Run: pip install paho-mqtt")
        sys.exit(1)


# Expected hardware data format from ESP32 rfid_uwb_mqtt.ino
EXPECTED_HARDWARE_FORMAT = """
╔══════════════════════════════════════════════════════════════╗
║  ESP32-S3 RFID + UWB JSON Format (rfid_uwb_mqtt.ino)        ║
╚══════════════════════════════════════════════════════════════╝

{
  "polling_cycle": 1,                    // uint32_t - cycle counter
  "timestamp": 123456,                   // unsigned long - millis() since boot
  "uwb": {
    "n_anchors": 2,                      // Count of valid anchors (with readings)
    "anchors": [
      {
        "mac_address": "0x0001",         // String "0x" + 4 hex chars
        "average_distance_cm": 150.5,    // float - averaged distance
        "measurements": 3,               // uint32_t - successful readings
        "total_sessions": 5              // uint32_t - total attempts
      }
    ]
  },
  "rfid": {
    "tag_count": 2,                      // uint8_t - number of tags
    "tags": [
      {
        "epc": "30396062c38d79c000287fa1",   // String - 24 hex chars (EPC-96)
        "rssi_dbm": -45,                 // int8_t - signal strength
        "pc": "3000"                     // String - Protocol Control word
      }
    ]
  }
}
"""


class MQTTValidator:
    def __init__(self, broker: str, port: int, topics: list):
        self.broker = broker
        self.port = port
        self.topics = topics
        self.message_count = 0
        self.valid_count = 0
        self.invalid_count = 0
        self.total_tags_seen = 0
        self.total_anchors_seen = 0
        self.unique_epcs = set()
        self.unique_anchors = set()
        
    def get_signal_quality(self, rssi: int) -> str:
        """Match ESP32 firmware getSignalQuality() function"""
        if rssi >= -50:
            return "🟢 Excellent"
        elif rssi >= -60:
            return "🟢 Good"
        elif rssi >= -70:
            return "🟡 Fair"
        elif rssi >= -80:
            return "🟠 Weak"
        else:
            return "🔴 Very Weak"
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"✅ Connected to MQTT broker at {self.broker}:{self.port}")
            for topic in self.topics:
                client.subscribe(topic)
                print(f"📡 Subscribed to: {topic}")
            print("\n" + "="*60)
            print("👂 Listening for ESP32 data... (Press Ctrl+C to stop)")
            print("="*60)
            print("\n💡 To start ESP32 publishing, run:")
            print(f"   mosquitto_pub -h {self.broker} -t store/control -m 'START'\n")
        else:
            print(f"❌ Connection failed with code: {rc}")
            
    def on_message(self, client, userdata, msg):
        self.message_count += 1
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        print(f"\n{'='*60}")
        print(f"📨 Message #{self.message_count} at {timestamp}")
        print(f"   Topic: {msg.topic}")
        print(f"   Size: {len(msg.payload)} bytes")
        print("-"*60)
        
        # Try to parse as JSON
        try:
            data = json.loads(msg.payload.decode('utf-8'))
            print("✅ Valid JSON")
            self.validate_hardware_format(data)
            self.valid_count += 1
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON: {e}")
            print(f"   Raw payload: {msg.payload[:200]}...")
            self.invalid_count += 1
        except UnicodeDecodeError:
            print(f"❌ Cannot decode payload as UTF-8")
            print(f"   Raw bytes: {msg.payload[:50]}...")
            self.invalid_count += 1
            
    def validate_hardware_format(self, data: dict):
        """Validate hardware data structure and display contents"""
        
        issues = []
        
        # Check polling_cycle
        if "polling_cycle" in data:
            print(f"\n🔄 Polling Cycle: {data['polling_cycle']}")
        else:
            issues.append("Missing 'polling_cycle' field")
            
        # Check timestamp
        if "timestamp" in data:
            print(f"⏰ Timestamp: {data['timestamp']} ms")
        else:
            issues.append("Missing 'timestamp' field")
        
        # Check RFID section
        print(f"\n{'─'*40}")
        print("🏷️  RFID Section:")
        if "rfid" in data:
            rfid = data["rfid"]
            tag_count = rfid.get("tag_count", 0)
            tags = rfid.get("tags", [])
            
            print(f"   Tag count: {tag_count}")
            
            if len(tags) != tag_count:
                issues.append(f"tag_count ({tag_count}) doesn't match actual tags ({len(tags)})")
            
            if tags:
                print(f"   Tags detected:")
                for i, tag in enumerate(tags[:10]):  # Show first 10
                    epc = tag.get("epc", "❓ MISSING")
                    rssi = tag.get("rssi_dbm", 0)
                    pc = tag.get("pc", "❓")
                    
                    # Track unique EPCs
                    if isinstance(epc, str):
                        self.unique_epcs.add(epc)
                    
                    # Validate EPC format (should be hex string, typically 24 chars for EPC-96)
                    epc_valid = "✅" if isinstance(epc, str) and len(epc) >= 8 else "⚠️"
                    signal_quality = self.get_signal_quality(rssi) if isinstance(rssi, int) else "❓"
                    
                    print(f"      [{i+1}] {epc_valid} EPC: {epc}")
                    print(f"          RSSI: {rssi} dBm {signal_quality}, PC: {pc}")
                    
                    # Check for required fields
                    if "epc" not in tag:
                        issues.append(f"Tag {i+1}: Missing 'epc' field")
                        
                if len(tags) > 10:
                    print(f"      ... and {len(tags) - 10} more tags")
                    
                self.total_tags_seen += len(tags)
            else:
                print("   ⚠️  No tags detected (polling cycle with no RFID reads)")
        else:
            issues.append("Missing 'rfid' section")
            print("   ❌ MISSING")
            
        # Check UWB section
        print(f"\n{'─'*40}")
        print("📏 UWB Section:")
        if "uwb" in data:
            uwb = data["uwb"]
            
            # Check if UWB is available
            if uwb.get("available") is False:
                print("   ⚠️  UWB not available")
            else:
                n_anchors = uwb.get("n_anchors", 0)
                anchors = uwb.get("anchors", [])
                
                print(f"   Anchor count: {n_anchors}")
                
                if len(anchors) != n_anchors:
                    issues.append(f"n_anchors ({n_anchors}) doesn't match actual anchors ({len(anchors)})")
                
                if anchors:
                    print(f"   Anchors detected:")
                    for i, anchor in enumerate(anchors):
                        mac = anchor.get("mac_address", "❓")
                        avg_dist = anchor.get("average_distance_cm")
                        measurements = anchor.get("measurements", 0)
                        total_sessions = anchor.get("total_sessions", 0)
                        
                        # Track unique anchors
                        if isinstance(mac, str):
                            self.unique_anchors.add(mac)
                        
                        dist_str = f"{avg_dist:.1f} cm" if avg_dist is not None else "null"
                        success_rate = f"{(measurements/total_sessions*100):.0f}%" if total_sessions > 0 else "N/A"
                        
                        # Distance quality indicator
                        if avg_dist is not None:
                            if avg_dist < 100:
                                dist_quality = "🟢 Close"
                            elif avg_dist < 300:
                                dist_quality = "🟡 Medium"
                            else:
                                dist_quality = "🟠 Far"
                        else:
                            dist_quality = "❓"
                        
                        print(f"      [{i+1}] Anchor {mac}")
                        print(f"          Distance: {dist_str} {dist_quality}")
                        print(f"          Success: {measurements}/{total_sessions} ({success_rate})")
                        
                        # Check for required fields
                        if "mac_address" not in anchor:
                            issues.append(f"Anchor {i+1}: Missing 'mac_address' field")
                            
                    self.total_anchors_seen += len(anchors)
                else:
                    print("   ⚠️  No anchors with valid readings this cycle")
        else:
            issues.append("Missing 'uwb' section")
            print("   ❌ MISSING")
            
        # Show full JSON for debugging
        print(f"\n{'─'*40}")
        print("📋 Full JSON:")
        json_str = json.dumps(data, indent=2)
        if len(json_str) > 800:
            print(json_str[:800])
            print("   ... (truncated)")
        else:
            print(json_str)
            
        # Validation summary
        print(f"\n{'─'*40}")
        if issues:
            print("⚠️  Validation Issues:")
            for issue in issues:
                print(f"   • {issue}")
        else:
            print("✅ Data structure is valid!")
            print("   Ready for OptiFlow backend processing")
            
    def on_disconnect(self, client, userdata, rc):
        print(f"\n⚠️  Disconnected from broker (code: {rc})")
        
    def run(self):
        client = mqtt.Client()
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        client.on_disconnect = self.on_disconnect
        
        print(f"\n🔌 Connecting to MQTT broker at {self.broker}:{self.port}...")
        
        try:
            client.connect(self.broker, self.port, 60)
            client.loop_forever()
        except ConnectionRefusedError:
            print(f"❌ Connection refused. Is the broker running at {self.broker}:{self.port}?")
        except KeyboardInterrupt:
            print(f"\n\n{'='*60}")
            print("📊 Session Summary")
            print("="*60)
            print(f"   Total messages received: {self.message_count}")
            print(f"   Valid JSON: {self.valid_count}")
            print(f"   Invalid: {self.invalid_count}")
            print(f"\n   Total RFID tag readings: {self.total_tags_seen}")
            print(f"   Unique EPCs seen: {len(self.unique_epcs)}")
            print(f"\n   Total UWB anchor readings: {self.total_anchors_seen}")
            print(f"   Unique anchors seen: {len(self.unique_anchors)}")
            if self.unique_anchors:
                print(f"   Anchor MACs: {', '.join(sorted(self.unique_anchors))}")
            print("\n👋 Goodbye!")
        finally:
            client.disconnect()


def main():
    if not MQTT_AVAILABLE:
        print("❌ paho-mqtt not installed. Run: pip install paho-mqtt")
        sys.exit(1)
    
    parser = argparse.ArgumentParser(
        description="MQTT Data Validator for OptiFlow ESP32 Hardware",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EXPECTED_HARDWARE_FORMAT
    )
    parser.add_argument("--broker", default="172.20.10.4", 
                       help="MQTT broker address (default: 172.20.10.4)")
    parser.add_argument("--port", type=int, default=1883,
                       help="MQTT broker port (default: 1883)")
    parser.add_argument("--topic", default="store/#",
                       help="MQTT topic to subscribe to (default: store/#)")
    parser.add_argument("--start", action="store_true",
                       help="Send START signal to ESP32 before listening")
    
    args = parser.parse_args()
    
    # Split topics if comma-separated
    topics = [t.strip() for t in args.topic.split(",")]
    
    print("\n" + "="*60)
    print("🔍 OptiFlow ESP32 Hardware Validator")
    print("="*60)
    print(f"\nTarget: ESP32-S3 RFID+UWB (rfid_uwb_mqtt.ino)")
    print(f"Broker: {args.broker}:{args.port}")
    print(f"Topics: {', '.join(topics)}")
    
    # Optionally send START signal
    if args.start:
        try:
            start_client = mqtt.Client()
            start_client.connect(args.broker, args.port, 5)
            start_client.publish("store/control", "START")
            start_client.disconnect()
            print("\n✅ Sent START signal to ESP32")
        except Exception as e:
            print(f"\n⚠️  Could not send START signal: {e}")
    
    print(EXPECTED_HARDWARE_FORMAT)
    
    validator = MQTTValidator(args.broker, args.port, topics)
    validator.run()


if __name__ == "__main__":
    main()
