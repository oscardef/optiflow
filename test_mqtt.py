#!/usr/bin/env python3
"""
MQTT Data Validator for OptiFlow
=================================
Subscribe to MQTT topics and validate incoming data from real hardware.

Usage:
    python test_mqtt.py [--broker BROKER] [--port PORT] [--topic TOPIC]

Examples:
    python test_mqtt.py                          # Use defaults
    python test_mqtt.py --broker 192.168.1.100   # Custom broker
    python test_mqtt.py --topic "store/#"        # Subscribe to all store topics
"""

import argparse
import json
import sys
from datetime import datetime

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("❌ paho-mqtt not installed. Run: pip install paho-mqtt")
    sys.exit(1)


# Expected hardware data format
EXPECTED_HARDWARE_FORMAT = """
Expected Hardware JSON Format:
{
  "polling_cycle": 1,
  "timestamp": 123456,
  "uwb": {
    "n_anchors": 2,
    "anchors": [
      {
        "mac_address": "0xABCD",
        "average_distance_cm": 150.5,
        "measurements": 3,
        "total_sessions": 5
      }
    ]
  },
  "rfid": {
    "tag_count": 2,
    "tags": [
      {
        "epc": "E200001234567890ABCD",
        "rssi_dbm": -45,
        "pc": "3000"
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
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"✅ Connected to MQTT broker at {self.broker}:{self.port}")
            for topic in self.topics:
                client.subscribe(topic)
                print(f"📡 Subscribed to: {topic}")
            print("\n" + "="*60)
            print("👂 Listening for messages... (Press Ctrl+C to stop)")
            print("="*60 + "\n")
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
                    rssi = tag.get("rssi_dbm", "❓")
                    pc = tag.get("pc", "❓")
                    
                    # Validate EPC format (should be hex string)
                    epc_valid = "✅" if isinstance(epc, str) and len(epc) >= 8 else "⚠️"
                    
                    print(f"      [{i+1}] {epc_valid} EPC: {epc}")
                    print(f"          RSSI: {rssi} dBm, PC: {pc}")
                    
                    # Check for required fields
                    if "epc" not in tag:
                        issues.append(f"Tag {i+1}: Missing 'epc' field")
                        
                if len(tags) > 10:
                    print(f"      ... and {len(tags) - 10} more tags")
            else:
                print("   ⚠️  No tags detected")
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
                        
                        dist_str = f"{avg_dist:.1f} cm" if avg_dist is not None else "null"
                        success_rate = f"{(measurements/total_sessions*100):.0f}%" if total_sessions > 0 else "N/A"
                        
                        print(f"      [{i+1}] Anchor {mac}")
                        print(f"          Distance: {dist_str}")
                        print(f"          Measurements: {measurements}/{total_sessions} ({success_rate})")
                        
                        # Check for required fields
                        if "mac_address" not in anchor:
                            issues.append(f"Anchor {i+1}: Missing 'mac_address' field")
                else:
                    print("   ⚠️  No anchors detected")
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
            print(f"   Total messages: {self.message_count}")
            print(f"   Valid JSON: {self.valid_count}")
            print(f"   Invalid: {self.invalid_count}")
            print("\n👋 Goodbye!")
        finally:
            client.disconnect()


def main():
    parser = argparse.ArgumentParser(
        description="MQTT Data Validator for OptiFlow Hardware",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EXPECTED_HARDWARE_FORMAT
    )
    parser.add_argument("--broker", default="172.20.10.3", 
                       help="MQTT broker address (default: 172.20.10.3)")
    parser.add_argument("--port", type=int, default=1883,
                       help="MQTT broker port (default: 1883)")
    parser.add_argument("--topic", default="store/#",
                       help="MQTT topic to subscribe to (default: store/#)")
    
    args = parser.parse_args()
    
    # Split topics if comma-separated
    topics = [t.strip() for t in args.topic.split(",")]
    
    print("\n" + "="*60)
    print("🔍 OptiFlow MQTT Hardware Validator")
    print("="*60)
    print(f"\nBroker: {args.broker}:{args.port}")
    print(f"Topics: {', '.join(topics)}")
    print(EXPECTED_HARDWARE_FORMAT)
    
    validator = MQTTValidator(args.broker, args.port, topics)
    validator.run()


if __name__ == "__main__":
    main()
