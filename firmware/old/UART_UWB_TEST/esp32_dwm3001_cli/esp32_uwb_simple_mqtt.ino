/*
 * ========================================================================
 * OptiFlow - ESP32-S3 + DWM3001CDK UWB Tag Firmware
 * ========================================================================
 * 
 * PURPOSE:
 * Reads UWB distance measurements from DWM3001CDK tag and publishes
 * them to an MQTT broker for processing by the OptiFlow backend.
 * 
 * HARDWARE WIRING:
 * ┌─────────────┐              ┌──────────────┐
 * │  ESP32-S3   │              │ DWM3001CDK   │
 * │             │              │   (Tag)      │
 * │ GPIO17 (TX) │─────────────▶│ P0.08 (RX)   │
 * │ GPIO18 (RX) │◀─────────────│ P0.06 (TX)   │
 * │ GND         │──────────────│ GND          │
 * │ 3.3V/5V     │──────────────│ VCC          │
 * └─────────────┘              └──────────────┘
 * 
 * BEFORE UPLOADING:
 * 1. Update WiFi credentials below (lines 44-46)
 * 2. Update MQTT broker IP (line 47) - use your MacBook's IP
 * 3. Select Board: "ESP32S3 Dev Module" in Arduino IDE
 * 4. Set Upload Speed: 921600
 * 
 * AFTER UPLOADING:
 * 1. Open Serial Monitor (115200 baud)
 * 2. Wait for "READY" message
 * 3. Send START signal: mosquitto_pub -h YOUR_IP -t store/control -m 'START'
 * 4. Watch UWB measurements appear every 200ms
 * 
 * MQTT TOPICS:
 * - Publishes to: store/aisle1 (UWB measurement data)
 * - Subscribes to: store/control (receives START/STOP commands)
 * - Publishes to: store/status (sends ESP32_READY on boot)
 * 
 * JSON OUTPUT FORMAT (sent to store/aisle1):
 * {
 *   "timestamp": "2024-11-12T15:30:45",
 *   "detections": [],  // Empty for now (RFID not implemented)
 *   "uwb_measurements": [
 *     {
 *       "mac_address": "0x0001",
 *       "distance_cm": 62.5,
 *       "status": "SUCCESS"
 *     }
 *   ]
 * }
 * 
 * TROUBLESHOOTING:
 * - If no WiFi: Check SSID/password and hotspot is active
 * - If no MQTT: Check mqtt_server IP matches your MacBook
 * - If measurements = 0: Power on anchor boards and configure as RESPF
 * - If no data published: Send START signal via MQTT
 * 
 * VERSION: 1.0
 * LAST UPDATED: November 2024
 * ========================================================================
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <HardwareSerial.h>

// ========== CONFIGURATION - UPDATE THESE VALUES ==========
// WiFi Configuration (your iPhone/MacBook hotspot)
const char* ssid = "Oscar";              // ⚠️ Change to your WiFi name
const char* password = "password";        // ⚠️ Change to your WiFi password
const char* mqtt_server = "172.20.10.3"; // ⚠️ Change to your MacBook IP
                                         // Find IP: ipconfig getifaddr en0

// MQTT Topics
const char* TOPIC_DATA = "store/aisle1";       // Main data topic (matches backend)
const char* TOPIC_CONTROL = "store/control";   // Control signals
const char* TOPIC_STATUS = "store/status";     // Status updates

// MQTT Clients
WiFiClient espClient;
PubSubClient client(espClient);

// UART for DWM3001CDK
HardwareSerial DWM_Serial(2);  // UART2
#define DWM_TX_PIN 17
#define DWM_RX_PIN 18
#define DWM_BAUD 115200

// Parser state
String rxBuffer = "";
String sessionBuffer = "";
bool inSession = false;
uint32_t sessionCount = 0;

// Control
bool start_signal = false;

void setup() {
  // Start Serial Monitor for debugging (115200 baud)
  Serial.begin(115200);
  delay(500);
  
  Serial.println("\n=== ESP32-S3 + DWM3001CDK + MQTT ===");
  Serial.println("Simple version\n");
  
  // Initialize UART connection to DWM3001CDK UWB module
  // GPIO17 (TX) -> DWM P0.08 (RX), GPIO18 (RX) -> DWM P0.06 (TX)
  DWM_Serial.begin(DWM_BAUD, SERIAL_8N1, DWM_RX_PIN, DWM_TX_PIN);
  delay(500);
  Serial.println("[UART] DWM3001CDK Ready\n");
  
  // Connect to WiFi and MQTT broker
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setBufferSize(2048);  // Large buffer for JSON payloads
  client.setCallback(mqtt_callback);  // Handle incoming MQTT messages
  reconnect();
  
  Serial.println("[READY] Waiting for START signal...\n");
  Serial.println("Send START signal with:");
  Serial.println("  mosquitto_pub -h 172.20.10.3 -t store/control -m 'START'\n");
}

void loop() {
  // Keep MQTT connection alive
  if (!client.connected()) {
    reconnect();
  }
  client.loop();  // Process incoming MQTT messages
  
  // Read UWB session data from DWM3001CDK via UART
  // The DWM sends SESSION_INFO_NTF messages every 200ms
  while (DWM_Serial.available()) {
    char c = DWM_Serial.read();
    
    // Build lines character by character
    if (c == '\n' || c == '\r') {
      if (rxBuffer.length() > 0) {
        processLine(rxBuffer);  // Parse complete line
        rxBuffer = "";
      }
    } else {
      rxBuffer += c;
      if (rxBuffer.length() > 2048) {
        rxBuffer = "";  // Prevent buffer overflow
      }
    }
  }
  
  // Optional: Forward commands from Serial Monitor to DWM3001CDK
  // Useful for debugging (type STAT, INITF, etc.)
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.length() > 0) {
      DWM_Serial.println(cmd);
      Serial.print("[Sent] ");
      Serial.println(cmd);
    }
  }
}

void setup_wifi() {
  Serial.println("[WiFi] Connecting...");
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WiFi] Connected!");
    Serial.print("[WiFi] IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n[WiFi] Failed!");
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("[MQTT] Connecting...");
    if (client.connect("ESP32_UWB_Simple")) {
      Serial.println("connected!");
      client.subscribe(TOPIC_CONTROL);
      client.publish(TOPIC_STATUS, "ESP32_READY");
      Serial.println("[MQTT] Published ESP32_READY");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" retrying...");
      delay(2000);
    }
  }
}

void mqtt_callback(char* topic, byte* payload, unsigned int length) {
  String msg;
  for (unsigned int i = 0; i < length; i++) {
    msg += (char)payload[i];
  }
  
  if (String(topic) == TOPIC_CONTROL && msg == "START") {
    start_signal = true;
    Serial.println("\n[CONTROL] START received!");
    Serial.println("[SYSTEM] Now publishing UWB data\n");
  }
}

void processLine(String line) {
  // Detect start of SESSION_INFO_NTF
  if (line.indexOf("SESSION_INFO_NTF:") != -1) {
    inSession = true;
    sessionBuffer = line + "\n";
    Serial.println("\n[UWB] >>> SESSION START <<<");
    return;
  }
  
  // If we're in a session, accumulate lines
  if (inSession) {
    sessionBuffer += " " + line + "\n";
    
    // Detect end of session (closing brace)
    if (line.indexOf("}") != -1) {
      inSession = false;
      Serial.println("[UWB] >>> SESSION END <<<");
      
      // Debug: Print raw session data
      Serial.println("\n[DEBUG] Raw session buffer:");
      Serial.println(sessionBuffer);
      Serial.println("[DEBUG] End of raw data\n");
      
      printSessionJSON();
      sessionBuffer = "";
    }
  }
}

void printSessionJSON() {
  sessionCount++;
  
  // Get timestamp in ISO format
  unsigned long timestamp = millis();
  
  // Build JSON document matching backend schema
  StaticJsonDocument<2048> doc;
  
  // Create ISO timestamp (simplified - using millis for now)
  char timeStr[32];
  sprintf(timeStr, "2024-11-12T%02lu:%02lu:%02lu", 
          (timestamp / 3600000) % 24,
          (timestamp / 60000) % 60, 
          (timestamp / 1000) % 60);
  doc["timestamp"] = timeStr;
  
  // Empty detections array (no RFID yet)
  JsonArray detections = doc.createNestedArray("detections");
  
  // Parse UWB measurements array
  JsonArray measurements = doc.createNestedArray("uwb_measurements");
  
  int searchStart = 0;
  while (true) {
    int macIdx = sessionBuffer.indexOf("[mac_address=0x", searchStart);
    if (macIdx == -1) break;
    
    // Find end of this measurement
    int measEnd = sessionBuffer.indexOf("];", macIdx);
    if (measEnd == -1) measEnd = sessionBuffer.indexOf("]}", macIdx);
    if (measEnd == -1) break;
    
    String measurement = sessionBuffer.substring(macIdx, measEnd + 1);
    
    // Extract MAC
    int macStart = measurement.indexOf("0x") + 2;
    String mac = "0x" + measurement.substring(macStart, macStart + 4);
    
    // Extract status
    int statusIdx = measurement.indexOf("status=\"");
    int statusEnd = measurement.indexOf("\"", statusIdx + 8);
    String status = measurement.substring(statusIdx + 8, statusEnd);
    
    // Extract distance if SUCCESS
    float distance = 0.0;
    if (status == "SUCCESS") {
      int distIdx = measurement.indexOf("distance[cm]=");
      if (distIdx != -1) {
        distIdx += 13;
        int distEnd = distIdx;
        while (distEnd < measurement.length() && isDigit(measurement.charAt(distEnd))) {
          distEnd++;
        }
        String distStr = measurement.substring(distIdx, distEnd);
        distance = distStr.toFloat();
      }
    }
    
    // Add to JSON array (only include if we have a valid distance)
    if (distance > 0) {
      JsonObject meas = measurements.createNestedObject();
      meas["mac_address"] = mac;
      meas["distance_cm"] = distance;
      meas["status"] = status;
    }
    
    searchStart = measEnd + 1;
  }
  
  // Print to Serial Monitor
  Serial.println("\n=== UWB Session #" + String(sessionCount) + " ===");
  Serial.print("Timestamp: ");
  Serial.println(doc["timestamp"].as<String>());
  Serial.print("Measurements: ");
  Serial.println(measurements.size());
  
  for (JsonObject m : measurements) {
    Serial.print("  - ");
    Serial.print(m["mac_address"].as<String>());
    Serial.print(" @ ");
    Serial.print(m["distance_cm"].as<float>(), 1);
    Serial.print("cm (");
    Serial.print(m["status"].as<String>());
    Serial.println(")");
  }
  Serial.println();
  
  // Publish to MQTT if START received and we have measurements
  if (start_signal && measurements.size() > 0) {
    String payload;
    serializeJson(doc, payload);
    
    bool success = client.publish(TOPIC_DATA, payload.c_str());
    if (success) {
      Serial.print("[MQTT] ✓ Published to ");
      Serial.print(TOPIC_DATA);
      Serial.print(" - Session #");
      Serial.print(sessionCount);
      Serial.print(" (");
      Serial.print(measurements.size());
      Serial.println(" measurements)");
    } else {
      Serial.println("[MQTT] ✗ Publish failed! Check buffer size.");
    }
  } else if (start_signal && measurements.size() == 0) {
    Serial.println("[MQTT] ⊘ No valid measurements to publish");
  }
}
