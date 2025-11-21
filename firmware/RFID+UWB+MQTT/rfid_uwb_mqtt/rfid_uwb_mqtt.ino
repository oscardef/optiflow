/*
 * ESP32-S3 Integrated RFID + UWB Reader with MQTT
 * FreeRTOS Multi-tasking Implementation
 * 
 * This code combines:
 * - UHF RFID reader (JRD-100 module) - continuous polling
 * - UWB positioning (DWM3001CDK with CLI firmware) - real-time tracking
 * - MQTT publishing - sends JSON data to server
 * 
 * Wiring:
 * RFID Module:
 *   - ESP32 GPIO7 (TX) -> RFID RX (white)
 *   - ESP32 GPIO6 (RX) -> RFID TX (blue)
 *   - GND -> GND (black)
 *   - 5V -> VCC (red)
 * 
 * DWM3001CDK:
 *   - ESP32 GPIO17 (TX) -> DWM P0.15 (RX)
 *   - ESP32 GPIO18 (RX) -> DWM P0.19 (TX)
 *   - GND -> GND
 * 
 * MQTT Configuration:
 * - Update WiFi SSID/password below
 * - Update MQTT broker IP (your MacBook IP)
 * - Publishes to: store/aisle1
 * - Subscribes to: store/control (START/STOP)
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <HardwareSerial.h>
#include <vector>
#include <map>
#include "UNIT_UHF_RFID.h"

// ============================================
// CONFIGURATION
// ============================================

// WiFi Configuration - UPDATE THESE
const char* WIFI_SSID = "Oscar";              // Your WiFi name
const char* WIFI_PASSWORD = "password";        // Your WiFi password
const char* MQTT_SERVER = "172.20.10.3";       // Your MacBook IP
const int MQTT_PORT = 1883;

// MQTT Topics
const char* TOPIC_DATA = "store/aisle1";       // Main data topic
const char* TOPIC_CONTROL = "store/control";   // Control signals (START/STOP)
const char* TOPIC_STATUS = "store/status";     // Status updates

// RFID Configuration
#define RFID_RX_PIN         6
#define RFID_TX_PIN         7
#define RFID_BAUD           115200
#define RFID_MAX_TX_POWER   3000        // 26.00dB
#define RFID_POLLING_COUNT  30
#define RFID_MAX_TAGS       200         // Maximum tags per polling cycle

// UWB Configuration
#define UWB_RX_PIN          18
#define UWB_TX_PIN          17
#define UWB_BAUD            115200
#define UWB_BUFFER_SIZE     2048

// Region Codes for RFID
#define REGION_CHINA1       0x01        // 920–925 MHz
#define REGION_USA          0x02        // 902–928 MHz
#define REGION_EUROPE       0x03        // 865–868 MHz
#define REGION_KOREA        0x04        // 917–923.5 MHz
#define CURRENT_REGION      REGION_CHINA1

// ============================================
// DATA STRUCTURES
// ============================================

struct UWBMeasurement {
    String macAddress;
    String status;
    int distanceCm;
};

struct UWBSession {
    unsigned long timestamp;
    uint32_t sessionCount;
    uint32_t sessionHandle;
    uint32_t sequenceNumber;
    uint32_t blockIndex;
    uint8_t nMeasurements;
    UWBMeasurement measurements[10];
    bool valid;
};

struct RFIDTagData {
    String epc;
    int8_t rssi;
    String pc;
    unsigned long timestamp;
};

struct AnchorStats {
    String macAddress;
    float totalDistance;
    uint32_t successCount;
    uint32_t totalCount;
};

// ============================================
// GLOBAL OBJECTS & VARIABLES
// ============================================

// WiFi and MQTT
WiFiClient espClient;
PubSubClient mqttClient(espClient);
bool startSignal = false;  // Control flag for publishing

// RFID
HardwareSerial rfidSerial(2);
Unit_UHF_RFID rfid;
RFIDTagData currentRfidTags[RFID_MAX_TAGS];
uint8_t currentRfidTagCount = 0;
SemaphoreHandle_t rfidMutex;

// UWB
HardwareSerial uwbSerial(1);
String uwbRxBuffer = "";
String uwbSessionBuffer = "";
bool inUwbSession = false;
uint32_t uwbSessionCount = 0;
UWBSession latestUwbSession;
SemaphoreHandle_t uwbMutex;

// UWB Statistics per anchor (accumulated during polling cycle)
std::map<String, AnchorStats> anchorStatsMap;
SemaphoreHandle_t anchorStatsMutex;

// Cycle synchronization
volatile uint32_t lastPrintedCycle = 0;
volatile uint32_t currentCycle = 0;
SemaphoreHandle_t cycleMutex;

// Task Handles
TaskHandle_t rfidTaskHandle;
TaskHandle_t uwbTaskHandle;
TaskHandle_t outputTaskHandle;

// ============================================
// SETUP
// ============================================

void setup() {
    Serial.begin(115200);
    delay(1000);
    
    printWelcomeBanner();
    
    // Initialize WiFi and MQTT
    setupWiFi();
    mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
    mqttClient.setBufferSize(4096);  // Large buffer for JSON
    mqttClient.setCallback(mqttCallback);
    reconnectMQTT();
    
    // Create mutexes
    rfidMutex = xSemaphoreCreateMutex();
    uwbMutex = xSemaphoreCreateMutex();
    anchorStatsMutex = xSemaphoreCreateMutex();
    cycleMutex = xSemaphoreCreateMutex();
    
    // Initialize modules
    initializeRFID();
    initializeUWB();
    
    // Initialize UWB session
    latestUwbSession.valid = false;
    
    Serial.println("\n=================================");
    Serial.println("✓ System Ready - Starting Tasks");
    Serial.println("=================================\n");
    Serial.println("Send START signal with:");
    Serial.printf("  mosquitto_pub -h %s -t %s -m 'START'\n\n", MQTT_SERVER, TOPIC_CONTROL);
    
    Serial.print("Heap before tasks: ");
    Serial.println(ESP.getFreeHeap());
    // Create FreeRTOS tasks
    xTaskCreatePinnedToCore(
        rfidTask,           // Task function
        "RFID_Task",        // Task name
        16384,              // Stack size
        NULL,               // Parameters
        2,                  // Priority
        &rfidTaskHandle,    // Task handle
        1                   // Core 1 - Data Collection
    );
    
    xTaskCreatePinnedToCore(
        uwbTask,
        "UWB_Task",
        16384,
        NULL,
        2,
        &uwbTaskHandle,
        1                   // Core 1 - Data Collection
    );
    
    xTaskCreatePinnedToCore(
        outputTask,
        "Output_Task",
        16384,
        NULL,
        1,
        &outputTaskHandle,
        0                   // Core 0 - WiFi/Network & MQTT
    );
    
    Serial.print("Heap after tasks: ");
    Serial.println(ESP.getFreeHeap());
}

// ============================================
// MAIN LOOP (minimal - tasks do the work)
// ============================================

void loop() {
    // Handle serial commands for UWB debugging
    if (Serial.available()) {
        String cmd = Serial.readStringUntil('\n');
        cmd.trim();
        if (cmd.length() > 0) {
            uwbSerial.println(cmd);
            Serial.printf("[UWB CMD] %s\n", cmd.c_str());
        }
    }
    vTaskDelay(pdMS_TO_TICKS(100));  // Minimal work - loop() runs on Core 1 by default
}

// ============================================
// FREERTOS TASKS
// ============================================

/**
 * RFID Task - Continuously polls for tags
 * This is the MASTER CLOCK - signals output task when cycle completes
 */
void rfidTask(void *parameter) {
    while (true) {
        // Perform RFID polling (blocking - takes time)
        uint8_t tagCount = rfid.pollingMultiple(RFID_POLLING_COUNT);
        
        // Increment cycle counter
        if (xSemaphoreTake(cycleMutex, portMAX_DELAY)) {
            currentCycle++;
            xSemaphoreGive(cycleMutex);
        }
        
        // Store tag data quickly
        if (xSemaphoreTake(rfidMutex, portMAX_DELAY)) {
            currentRfidTagCount = tagCount;
            
            for (uint8_t i = 0; i < tagCount && i < RFID_MAX_TAGS; i++) {
                currentRfidTags[i].epc = rfid.cards[i].epc_str;
                currentRfidTags[i].rssi = (int8_t)rfid.cards[i].rssi;
                currentRfidTags[i].pc = rfid.cards[i].pc_str;
                currentRfidTags[i].timestamp = millis();
            }
            
            xSemaphoreGive(rfidMutex);
        }
        
        // IMMEDIATELY start next cycle - output task handles printing
        vTaskDelay(pdMS_TO_TICKS(1)); // Minimal delay
    }
}

/**
 * UWB Task - Processes UWB data continuously
 */
void uwbTask(void *parameter) {
    while (true) {
        while (uwbSerial.available()) {
            char c = uwbSerial.read();
            
            if (c == '\n' || c == '\r') {
                if (uwbRxBuffer.length() > 0) {
                    processUWBLine(uwbRxBuffer);
                    uwbRxBuffer = "";
                }
            } else {
                uwbRxBuffer += c;
                if (uwbRxBuffer.length() > UWB_BUFFER_SIZE) {
                    uwbRxBuffer = "";
                }
            }
        }
        vTaskDelay(pdMS_TO_TICKS(1)); // Minimal delay for responsiveness
    }
}

/**
 * Output Task - Handles all heavy processing and MQTT (Core 0)
 */
void outputTask(void *parameter) {
    // Print task info at startup
    Serial.println("\n=== OUTPUT TASK STARTUP ===");
    UBaseType_t stackSize = uxTaskGetStackHighWaterMark(NULL);
    Serial.printf("Initial stack available: %u bytes\n", stackSize * sizeof(StackType_t));
    Serial.println("===========================\n");
    
    while (true) {
        // MQTT keepalive (runs on Core 0 with WiFi/network stack)
        if (!mqttClient.connected()) {
            reconnectMQTT();
        }
        mqttClient.loop();
        
        uint32_t cycleToProcess = 0;
        bool shouldProcess = false;
        
        // Check if there's a new cycle to process
        if (xSemaphoreTake(cycleMutex, pdMS_TO_TICKS(10))) {
            if (currentCycle > lastPrintedCycle) {
                cycleToProcess = currentCycle;
                lastPrintedCycle = currentCycle;
                shouldProcess = true;
            }
            xSemaphoreGive(cycleMutex);
        }
        
        if (shouldProcess) {
            // Do all the heavy work here (JSON building + MQTT publishing)
            combineDataFromPollingAndSend(cycleToProcess);
            
            // Clear anchor statistics for next cycle
            if (xSemaphoreTake(anchorStatsMutex, portMAX_DELAY)) {
                anchorStatsMap.clear();
                xSemaphoreGive(anchorStatsMutex);
            }
        }
        
        vTaskDelay(pdMS_TO_TICKS(10)); // Check every 10ms
    }
}

// ============================================
// RFID FUNCTIONS
// ============================================

void initializeRFID() {
    Serial.println("\n--- Initializing RFID Module ---");
    
    rfid.begin(&rfidSerial, RFID_BAUD, RFID_RX_PIN, RFID_TX_PIN, false);
    rfid.waitModuleInitialization();
    rfid.setRegion(CURRENT_REGION);
    rfid.verifyRegion();
    
    // Set receiver gain to maximum for better sensitivity
    rfid.setReceiverParams(0x06, 0x07, 0x01B0); // Mixer Gain: 16dB, IF Gain: 40dB
    
    // Set maximum transmission power
    if (rfid.setTxPower(RFID_MAX_TX_POWER)) {
        Serial.println("✓ TX Power set successfully");
        Serial.printf("✓ TX Power: %.2f dB\n", RFID_MAX_TX_POWER / 100.0);
    } else {
        Serial.println("✗ TX Power setting failed!");
    }
    
    Serial.println("✓ RFID Module initialized successfully");
}

// ============================================
// OUTPUT FUNCTIONS
// ============================================

/**
 * Print combined RFID + UWB data triggered by RFID polling cycle
 * Also publishes to MQTT if START signal received
 */
void combineDataFromPollingAndSend(uint32_t cycleCount) {
    unsigned long timestamp = millis();
    
    // Get RFID data
    uint8_t tagCount = 0;
    RFIDTagData tags[RFID_MAX_TAGS];
    
    if (xSemaphoreTake(rfidMutex, pdMS_TO_TICKS(10))) {
        tagCount = currentRfidTagCount;
        for (uint8_t i = 0; i < tagCount && i < RFID_MAX_TAGS; i++) {
            tags[i] = currentRfidTags[i];
        }
        xSemaphoreGive(rfidMutex);
    }
    
    // Get anchor statistics (accumulated during polling) - dynamic map
    std::map<String, AnchorStats> statsMap;
    
    if (xSemaphoreTake(anchorStatsMutex, pdMS_TO_TICKS(10))) {
        statsMap = anchorStatsMap;
        xSemaphoreGive(anchorStatsMutex);
    }
    
    // Build JSON document for MQTT
    StaticJsonDocument<4096> doc;
    
    // Create ISO-like timestamp
    char timeStr[32];
    sprintf(timeStr, "2024-11-21T%02lu:%02lu:%02lu", 
            (timestamp / 3600000) % 24,
            (timestamp / 60000) % 60, 
            (timestamp / 1000) % 60);
    doc["timestamp"] = timeStr;
    
    // RFID detections array (matches backend schema)
    JsonArray detections = doc.createNestedArray("detections");
    for (uint8_t i = 0; i < tagCount; i++) {
        JsonObject tag = detections.createNestedObject();
        tag["epc"] = tags[i].epc;
        tag["rssi"] = tags[i].rssi;
        tag["pc"] = tags[i].pc;
    }
    
    // UWB measurements array (matches backend schema)
    JsonArray measurements = doc.createNestedArray("uwb_measurements");
    for (auto& pair : statsMap) {
        const AnchorStats& stats = pair.second;
        if (stats.successCount > 0) {
            JsonObject meas = measurements.createNestedObject();
            meas["mac_address"] = "0x" + stats.macAddress;
            float avgDistance = stats.totalDistance / stats.successCount;
            meas["distance_cm"] = avgDistance;
            meas["status"] = "SUCCESS";
        }
    }
    
    // Print to Serial Monitor
    Serial.println("{");
    Serial.printf("  \"polling_cycle\": %u,\n", cycleCount);
    Serial.printf("  \"timestamp\": \"%s\",\n", timeStr);
    Serial.printf("  \"rfid_tags\": %u,\n", tagCount);
    Serial.printf("  \"uwb_anchors\": %u\n", measurements.size());
    Serial.println("}\n");
    
    // Publish to MQTT if START signal received and we have data
    if (startSignal && (tagCount > 0 || measurements.size() > 0)) {
        String payload;
        serializeJson(doc, payload);
        
        bool success = mqttClient.publish(TOPIC_DATA, payload.c_str());
        if (success) {
            Serial.printf("[MQTT] ✓ Published - Cycle #%u (%u tags, %u UWB)\n", 
                         cycleCount, tagCount, measurements.size());
        } else {
            Serial.println("[MQTT] ✗ Publish failed!");
        }
    } else if (startSignal) {
        Serial.println("[MQTT] ⊘ No data to publish");
    }
}

/**
 * Print combined RFID + UWB data (legacy function, kept for compatibility)
 */
void printCombinedData(UWBSession &uwbSession) {
    Serial.println("\n╔════════════════════════════════════════╗");
    Serial.printf("║  Session #%-4u | Time: %-12lu ║\n", 
                  uwbSession.sessionCount, uwbSession.timestamp);
    Serial.println("╚════════════════════════════════════════╝");
    
    // Print UWB data with average distance
    printUWBData(uwbSession);
    
    // Print RFID tags detected during this period
    printRFIDData();
    
    Serial.println("════════════════════════════════════════\n");
}

void printUWBData(UWBSession &session) {
    Serial.println("\n[UWB POSITIONING]");
    
    // Calculate average distance from successful measurements
    float totalDistance = 0;
    uint8_t successCount = 0;
    
    for (uint8_t i = 0; i < session.nMeasurements; i++) {
        if (session.measurements[i].status == "SUCCESS" && 
            session.measurements[i].distanceCm > 0) {
            totalDistance += session.measurements[i].distanceCm;
            successCount++;
        }
    }
    
    if (successCount > 0) {
        float avgDistance = totalDistance / successCount;
        Serial.printf("  Average Distance: %.1f cm (%d anchors)\n\n", 
                      avgDistance, successCount);
    } else {
        Serial.println("  Average Distance: N/A (no successful measurements)\n");
    }
    
    // Print individual anchor distances
    Serial.println("  Anchor Distances:");
    for (uint8_t i = 0; i < session.nMeasurements; i++) {
        Serial.printf("    • 0x%s: ", session.measurements[i].macAddress.c_str());
        
        if (session.measurements[i].status == "SUCCESS") {
            Serial.printf("%d cm\n", session.measurements[i].distanceCm);
        } else {
            Serial.printf("%s\n", session.measurements[i].status.c_str());
        }
    }
}

void printRFIDData() {
    Serial.println("\n[RFID TAGS]");
    
    uint8_t tagCount = 0;
    RFIDTagData tags[RFID_MAX_TAGS];
    
    // Get RFID data safely
    if (xSemaphoreTake(rfidMutex, pdMS_TO_TICKS(100))) {
        tagCount = currentRfidTagCount;
        for (uint8_t i = 0; i < tagCount && i < RFID_MAX_TAGS; i++) {
            tags[i] = currentRfidTags[i];
        }
        xSemaphoreGive(rfidMutex);
    }
    
    if (tagCount > 0) {
        Serial.printf("  Tags Detected: %d\n\n", tagCount);
        
        for (uint8_t i = 0; i < tagCount; i++) {
            Serial.printf("  Tag #%d:\n", i + 1);
            Serial.printf("    EPC:  %s\n", tags[i].epc.c_str());
            Serial.printf("    RSSI: %d dBm %s\n", 
                          tags[i].rssi, rfid.getSignalQuality(tags[i].rssi).c_str());
        }
    } else {
        Serial.println("  No tags detected");
    }
}

// ============================================
// UWB FUNCTIONS
// ============================================

void initializeUWB() {
    Serial.println("\n--- Initializing UWB Module ---");
    
    uwbSerial.begin(UWB_BAUD, SERIAL_8N1, UWB_RX_PIN, UWB_TX_PIN);
    delay(500);
    
    Serial.println("✓ DWM3001CDK UART Ready");
}

void processUWBLine(String line) {
    // Detect start of SESSION_INFO_NTF
    if (line.indexOf("SESSION_INFO_NTF:") != -1) {
        inUwbSession = true;
        uwbSessionBuffer = line + "\n";
        return;
    }
    
    // Accumulate session lines
    if (inUwbSession) {
        uwbSessionBuffer += " " + line + "\n";

        if (uwbSessionBuffer.length() > UWB_BUFFER_SIZE) {
            Serial.println("[UWB] Session buffer overflow!");
            inUwbSession = false;
            uwbSessionBuffer = "";
            return;
        }
        
        // Detect end of session
        if (line.indexOf("}") != -1) {
            inUwbSession = false;
            parseUWBSession();
            uwbSessionBuffer = "";
        }
    }
}

void parseUWBSession() {
    if (xSemaphoreTake(uwbMutex, pdMS_TO_TICKS(100))) {
        uwbSessionCount++;
        
        latestUwbSession.timestamp = millis();
        latestUwbSession.sessionCount = uwbSessionCount;
        latestUwbSession.valid = true;
        
        // Extract session metadata
        latestUwbSession.sessionHandle = extractUWBValue("session_handle");
        latestUwbSession.sequenceNumber = extractUWBValue("sequence_number");
        latestUwbSession.blockIndex = extractUWBValue("block_index");
        latestUwbSession.nMeasurements = extractUWBValue("n_measurements");
        
        // Parse measurements
        parseUWBMeasurements();
        
        xSemaphoreGive(uwbMutex);
    }
    
    // Update anchor statistics
    updateAnchorStatistics();
}

uint32_t extractUWBValue(const char* fieldName) {
    String searchStr = String(fieldName) + "=";
    int idx = uwbSessionBuffer.indexOf(searchStr);
    
    if (idx != -1) {
        int endIdx = uwbSessionBuffer.indexOf(",", idx);
        if (endIdx == -1) endIdx = uwbSessionBuffer.indexOf("\n", idx);
        
        String value = uwbSessionBuffer.substring(idx + searchStr.length(), endIdx);
        value.trim();
        return value.toInt();
    }
    return 0;
}

void parseUWBMeasurements() {
    int searchStart = 0;
    uint8_t measIdx = 0;
    
    while (measIdx < 10) {
        int macIdx = uwbSessionBuffer.indexOf("[mac_address=0x", searchStart);
        if (macIdx == -1) break;
        
        int measEnd = uwbSessionBuffer.indexOf("];", macIdx);
        if (measEnd == -1) measEnd = uwbSessionBuffer.indexOf("]}", macIdx);
        if (measEnd == -1) break;
        
        String measurement = uwbSessionBuffer.substring(macIdx, measEnd + 1);
        
        // Extract MAC address
        int macStart = measurement.indexOf("0x") + 2;
        latestUwbSession.measurements[measIdx].macAddress = 
            measurement.substring(macStart, macStart + 4);
        
        // Extract status
        int statusIdx = measurement.indexOf("status=\"");
        int statusEnd = measurement.indexOf("\"", statusIdx + 8);
        latestUwbSession.measurements[measIdx].status = 
            measurement.substring(statusIdx + 8, statusEnd);
        
        // Extract distance
        latestUwbSession.measurements[measIdx].distanceCm = -1;
        if (latestUwbSession.measurements[measIdx].status == "SUCCESS") {
            int distIdx = measurement.indexOf("distance[cm]=");
            if (distIdx != -1) {
                distIdx += 13;
                int distEnd = distIdx;
                while (distEnd < measurement.length() && 
                       isDigit(measurement.charAt(distEnd))) {
                    distEnd++;
                }
                latestUwbSession.measurements[measIdx].distanceCm = 
                    measurement.substring(distIdx, distEnd).toInt();
            }
        }
        
        measIdx++;
        searchStart = measEnd + 1;
    }
}

void updateAnchorStatistics() {
    UWBSession session;
    bool hasData = false;
    
    // Get current UWB session
    if (xSemaphoreTake(uwbMutex, pdMS_TO_TICKS(10))) {
        if (latestUwbSession.valid) {
            session = latestUwbSession;
            hasData = true;
        }
        xSemaphoreGive(uwbMutex);
    }
    
    if (!hasData) return;
    
    // Update anchor statistics using dynamic map
    if (xSemaphoreTake(anchorStatsMutex, pdMS_TO_TICKS(100))) {
        for (uint8_t i = 0; i < session.nMeasurements; i++) {
            String macAddr = session.measurements[i].macAddress;
            
            // Create or get anchor stats
            if (anchorStatsMap.find(macAddr) == anchorStatsMap.end()) {
                AnchorStats newStats;
                newStats.macAddress = macAddr;
                newStats.totalDistance = 0;
                newStats.successCount = 0;
                newStats.totalCount = 0;
                anchorStatsMap[macAddr] = newStats;
            }
            
            // Update statistics
            anchorStatsMap[macAddr].totalCount++;
            
            if (session.measurements[i].status == "SUCCESS" && 
                session.measurements[i].distanceCm > 0) {
                anchorStatsMap[macAddr].totalDistance += session.measurements[i].distanceCm;
                anchorStatsMap[macAddr].successCount++;
            }
        }
        xSemaphoreGive(anchorStatsMutex);
    }
}

// ============================================
// WIFI & MQTT FUNCTIONS
// ============================================

void setupWiFi() {
    Serial.println("\n[WiFi] Connecting...");
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 30) {
        delay(500);
        Serial.print(".");
        attempts++;
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n[WiFi] ✓ Connected!");
        Serial.print("[WiFi] IP: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println("\n[WiFi] ✗ Failed to connect!");
    }
}

void reconnectMQTT() {
    while (!mqttClient.connected()) {
        Serial.print("[MQTT] Connecting...");
        if (mqttClient.connect("ESP32_RFID_UWB")) {
            Serial.println(" ✓ Connected!");
            mqttClient.subscribe(TOPIC_CONTROL);
            mqttClient.publish(TOPIC_STATUS, "ESP32_READY");
            Serial.println("[MQTT] Subscribed to control topic");
        } else {
            Serial.print(" ✗ Failed, rc=");
            Serial.println(mqttClient.state());
            delay(2000);
        }
    }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
    String msg;
    for (unsigned int i = 0; i < length; i++) {
        msg += (char)payload[i];
    }
    
    if (String(topic) == TOPIC_CONTROL) {
        if (msg == "START") {
            startSignal = true;
            Serial.println("\n[CONTROL] ▶ START received - Publishing enabled");
        } else if (msg == "STOP") {
            startSignal = false;
            Serial.println("\n[CONTROL] ⏸ STOP received - Publishing paused");
        }
    }
}

// ============================================
// UTILITY FUNCTIONS
// ============================================

void printWelcomeBanner() {
    Serial.println("\n╔════════════════════════════════════════╗");
    Serial.println("║  ESP32-S3 RFID + UWB Reader + MQTT    ║");
    Serial.println("║  Integrated Positioning System         ║");
    Serial.println("╚════════════════════════════════════════╝");
}
