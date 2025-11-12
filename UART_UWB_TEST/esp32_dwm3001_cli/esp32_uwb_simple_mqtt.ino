/*
 * ESP32-S3 + DWM3001CDK (CLI Firmware) + MQTT
 * Simple version based on working code
 * 
 * Wiring:
 * - ESP32 GPIO17 (TX) -> DWM3001CDK P0.08 (RX)
 * - ESP32 GPIO18 (RX) -> DWM3001CDK P0.06 (TX)
 * - GND -> GND
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <HardwareSerial.h>

// WiFi Configuration
const char* ssid = "Oscar";
const char* password = "password";
const char* mqtt_server = "172.20.10.3";

// MQTT Topics
const char* TOPIC_UWB_RAW = "store/uwb_raw";
const char* TOPIC_CONTROL = "store/control";
const char* TOPIC_STATUS = "store/status";

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
  Serial.begin(115200);
  delay(500);
  
  Serial.println("\n=== ESP32-S3 + DWM3001CDK + MQTT ===");
  Serial.println("Simple version\n");
  
  // Initialize DWM3001CDK UART
  DWM_Serial.begin(DWM_BAUD, SERIAL_8N1, DWM_RX_PIN, DWM_TX_PIN);
  delay(500);
  Serial.println("[UART] DWM3001CDK Ready\n");
  
  // Initialize WiFi and MQTT
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setBufferSize(2048);
  client.setCallback(mqtt_callback);
  reconnect();
  
  Serial.println("[READY] Waiting for START signal...\n");
}

void loop() {
  // Maintain MQTT connection
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  
  // Read from DWM3001CDK
  while (DWM_Serial.available()) {
    char c = DWM_Serial.read();
    
    if (c == '\n' || c == '\r') {
      if (rxBuffer.length() > 0) {
        processLine(rxBuffer);
        rxBuffer = "";
      }
    } else {
      rxBuffer += c;
      if (rxBuffer.length() > 2048) {
        rxBuffer = "";  // Overflow protection
      }
    }
  }
  
  // Forward commands from Serial Monitor to DWM
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
      printSessionJSON();
      sessionBuffer = "";
    }
  }
}

void printSessionJSON() {
  sessionCount++;
  
  // Get timestamp
  unsigned long timestamp = millis();
  
  // Build JSON document
  StaticJsonDocument<2048> doc;
  doc["timestamp"] = timestamp;
  doc["session_count"] = sessionCount;
  
  // Extract session_handle
  int handleIdx = sessionBuffer.indexOf("session_handle=");
  if (handleIdx != -1) {
    int handleEnd = sessionBuffer.indexOf(",", handleIdx);
    String handle = sessionBuffer.substring(handleIdx + 15, handleEnd);
    doc["session_handle"] = handle.toInt();
  }
  
  // Extract sequence_number
  int seqIdx = sessionBuffer.indexOf("sequence_number=");
  if (seqIdx != -1) {
    int seqEnd = sessionBuffer.indexOf(",", seqIdx);
    String seq = sessionBuffer.substring(seqIdx + 16, seqEnd);
    doc["sequence_number"] = seq.toInt();
  }
  
  // Parse measurements array
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
    int distance = -1;
    if (status == "SUCCESS") {
      int distIdx = measurement.indexOf("distance[cm]=");
      if (distIdx != -1) {
        distIdx += 13;
        int distEnd = distIdx;
        while (distEnd < measurement.length() && isDigit(measurement.charAt(distEnd))) {
          distEnd++;
        }
        String distStr = measurement.substring(distIdx, distEnd);
        distance = distStr.toInt();
      }
    }
    
    // Add to JSON array
    JsonObject meas = measurements.createNestedObject();
    meas["mac_address"] = mac;
    meas["status"] = status;
    meas["distance_cm"] = distance;
    
    searchStart = measEnd + 1;
  }
  
  // Print to Serial (like original code)
  Serial.println("\n{");
  Serial.print("  \"timestamp\": ");
  Serial.print(timestamp);
  Serial.println(",");
  Serial.print("  \"session_count\": ");
  Serial.print(sessionCount);
  Serial.println(",");
  Serial.print("  \"measurements\": ");
  Serial.print(measurements.size());
  Serial.println();
  
  for (JsonObject m : measurements) {
    Serial.print("    ");
    Serial.print(m["mac_address"].as<String>());
    Serial.print(": ");
    Serial.print(m["status"].as<String>());
    if (m["distance_cm"].as<int>() > 0) {
      Serial.print(" @ ");
      Serial.print(m["distance_cm"].as<int>());
      Serial.println("cm");
    } else {
      Serial.println();
    }
  }
  Serial.println("}\n");
  
  // Publish to MQTT if START received
  if (start_signal && measurements.size() > 0) {
    String payload;
    serializeJson(doc, payload);
    
    bool success = client.publish(TOPIC_UWB_RAW, payload.c_str());
    if (success) {
      Serial.print("[MQTT] ✓ Published session ");
      Serial.print(sessionCount);
      Serial.print(" (");
      Serial.print(measurements.size());
      Serial.println(" measurements)");
    } else {
      Serial.println("[MQTT] ✗ Publish failed!");
    }
  }
}
