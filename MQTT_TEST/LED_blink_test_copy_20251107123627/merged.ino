/*
 * ESP32-S3 + DWM3001CDK (CLI Firmware) + MQTT Integration
 * Reads UWB distance measurements and forwards to server via MQTT
 * 
 * Hardware Connections:
 * - ESP32 GPIO17 (TX) -> DWM3001CDK P0.19 (RX)
 * - ESP32 GPIO18 (RX) -> DWM3001CDK P0.15 (TX)
 * - GND -> GND
 * 
 * MQTT Topics:
 * - store/status: ESP32 publishes "ESP32_READY" when connected
 * - store/control: Server sends "START" to begin sending data
 * - store/uwb_raw: ESP32 publishes raw UWB measurements
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

// UART Configuration for DWM3001CDK
HardwareSerial DWM_Serial(2);
#define DWM_TX_PIN 17
#define DWM_RX_PIN 18
#define DWM_BAUD 115200

// MQTT Clients
WiFiClient espClient;
PubSubClient client(espClient);

// UWB Parser State
String rxBuffer = "";
String sessionBuffer = "";
bool inSession = false;
uint32_t sessionCount = 0;

// UWB Measurement Storage
struct UWBMeasurement {
  String mac_address;
  String status;
  int distance_cm;
  bool valid;
};

#define MAX_UWB_MEASUREMENTS 10
UWBMeasurement latestUWBData[MAX_UWB_MEASUREMENTS];
int uwbMeasurementCount = 0;

// Control Flags
bool start_signal = false;

void setup() {
  Serial.begin(115200);
  delay(500);
  
  Serial.println("\n=== ESP32-S3 UWB Data Forwarder ===");
  Serial.println("Initializing...\n");
  
  // Initialize DWM3001CDK UART
  DWM_Serial.begin(DWM_BAUD, SERIAL_8N1, DWM_RX_PIN, DWM_TX_PIN);
  Serial.println("[UART] DWM3001CDK connection ready");
  
  // Initialize WiFi and MQTT
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setBufferSize(2048);
  client.setCallback(mqtt_callback);
  reconnect();
  
  Serial.println("\n[READY] Waiting for START signal from server...");
}

void loop() {
  // Maintain MQTT connection
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  
  // Always read and parse UWB data from DWM3001CDK
  readUWBData();
  
  // Only publish if START signal received
  if (!start_signal) {
    delay(50);
    return;
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
    Serial.print("[WiFi] IP Address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n[WiFi] Connection failed!");
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("[MQTT] Connecting to broker...");
    if (client.connect("ESP32_UWB_RFID_System")) {
      Serial.println("connected!");
      client.subscribe(TOPIC_CONTROL);
      client.publish(TOPIC_STATUS, "ESP32_READY");
      Serial.println("[MQTT] Published ESP32_READY status");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" retrying in 2s...");
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
    Serial.println("\n[CONTROL] Received START signal!");
    Serial.println("[SYSTEM] Now forwarding UWB data...\n");
  }
}

void readUWBData() {
  while (DWM_Serial.available()) {
    char c = DWM_Serial.read();
    
    if (c == '\n' || c == '\r') {
      if (rxBuffer.length() > 0) {
        processUWBLine(rxBuffer);
        rxBuffer = "";
      }
    } else {
      rxBuffer += c;
      if (rxBuffer.length() > 2048) {
        rxBuffer = ""; // Overflow protection
      }
    }
  }
}

void processUWBLine(String line) {
  // Detect start of SESSION_INFO_NTF
  if (line.indexOf("SESSION_INFO_NTF:") != -1) {
    inSession = true;
    sessionBuffer = line + "\n";
    return;
  }
  
  // If we're in a session, accumulate lines
  if (inSession) {
    sessionBuffer += " " + line + "\n";
    
    // Detect end of session (closing brace)
    if (line.indexOf("}") != -1) {
      inSession = false;
      parseUWBSession();
      sessionBuffer = "";
    }
  }
}

void parseUWBSession() {
  sessionCount++;
  uwbMeasurementCount = 0;
  
  Serial.println("\n[UWB] New session detected, parsing...");
  
  // Parse measurements from session buffer
  int searchStart = 0;
  
  while (uwbMeasurementCount < MAX_UWB_MEASUREMENTS) {
    int macIdx = sessionBuffer.indexOf("[mac_address=0x", searchStart);
    if (macIdx == -1) break;
    
    // Find end of this measurement
    int measEnd = sessionBuffer.indexOf("];", macIdx);
    if (measEnd == -1) measEnd = sessionBuffer.indexOf("]}", macIdx);
    if (measEnd == -1) break;
    
    String measurement = sessionBuffer.substring(macIdx, measEnd + 1);
    
    // Extract MAC address
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
    
    // Store measurement
    UWBMeasurement &m = latestUWBData[uwbMeasurementCount];
    m.mac_address = mac;
    m.status = status;
    m.distance_cm = distance;
    m.valid = true;
    
    Serial.print("  Anchor ");
    Serial.print(mac);
    Serial.print(": ");
    Serial.print(status);
    if (distance > 0) {
      Serial.print(" @ ");
      Serial.print(distance);
      Serial.println("cm");
    } else {
      Serial.println();
    }
    
    uwbMeasurementCount++;
    searchStart = measEnd + 1;
  }
  
  // Publish immediately when we have UWB data
  if (start_signal && uwbMeasurementCount > 0) {
    publishUWBData();
  }
}

void publishUWBData() {
  StaticJsonDocument<2048> doc;
  
  // Timestamp
  doc["timestamp"] = millis();
  
  // Session count
  doc["session_count"] = sessionCount;
  
  // UWB Measurements Array
  JsonArray uwb_array = doc.createNestedArray("uwb_measurements");
  for (int i = 0; i < uwbMeasurementCount; i++) {
    if (latestUWBData[i].valid) {
      JsonObject uwb = uwb_array.createNestedObject();
      uwb["mac_address"] = latestUWBData[i].mac_address;
      uwb["status"] = latestUWBData[i].status;
      uwb["distance_cm"] = latestUWBData[i].distance_cm;
    }
  }
  
  // Serialize and publish
  String payload;
  serializeJson(doc, payload);
  
  bool success = client.publish(TOPIC_UWB_RAW, payload.c_str());
  if (success) {
    Serial.print("[MQTT] ✓ Published session ");
    Serial.print(sessionCount);
    Serial.print(" with ");
    Serial.print(uwbMeasurementCount);
    Serial.println(" measurements");
  } else {
    Serial.println("[MQTT] ✗ Publish failed!");
  }
  Serial.println();
}

