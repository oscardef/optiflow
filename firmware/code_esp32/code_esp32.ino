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
#include <ArduinoJson.h> // Install library by Bblanchon
#include <HardwareSerial.h>
#include <vector>
#include <map>
#include "UNIT_UHF_RFID.h"

// ============================================
// CONFIGURATION
// ============================================

#define DEBUG_MODE 1    // Set to 1 for debugging

#if DEBUG_MODE
#define DEBUG_PRINT(x) Serial.print(x)
#define DEBUG_PRINTLN(x) Serial.println(x)
#else
#define DEBUG_PRINT(x)
#define DEBUG_PRINTLN(x)
#endif

// WiFi Configuration - UPDATE THESE
const char* WIFI_SSID = "Oscar";              // Your WiFi name
const char* WIFI_PASSWORD = "password";        // Your WiFi password
const char* MQTT_SERVER = "172.20.10.4";       // Your MacBook IP
const int MQTT_PORT = 1883;

// MQTT Topics
const char* TOPIC_DATA = "store/production";   // Main data topic for production hardware
const char* TOPIC_CONTROL = "store/production/control";   // Control signals (START/STOP)
const char* TOPIC_STATUS = "store/production/status";     // Status updates

// RFID Configuration
#define RFID_RX_PIN         6
#define RFID_TX_PIN         7
#define RFID_BAUD           115200
#define RFID_MAX_TX_POWER   3000        // 26.00dB
#define RFID_POLLING_COUNT  6
#define RFID_MAX_TAGS       200         // Maximum tags per polling cycle
#define UWB_MAX_ANCHORS     30          // Circular buffer size
#define UWB_FRESHNESS_MS    3000        // Data valid for 3 seconds  

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
    unsigned long timestamp;
};

struct AnchorStats {
    String macAddress;
    float totalDistance;
    uint32_t successCount;
    uint32_t totalCount;
    unsigned long timestamp;        // When this entry was last updated
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
    mqttClient.setBufferSize(32768);  // Large buffer for JSON
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
    
    DEBUG_PRINTLN("\n=================================");
    DEBUG_PRINTLN("✓ System Ready - Starting Tasks");
    DEBUG_PRINTLN("=================================\n");
    DEBUG_PRINTLN("Send START signal with:");
    DEBUG_PRINT("  mosquitto_pub -h ");
    DEBUG_PRINT(MQTT_SERVER);
    DEBUG_PRINT(" -t ");
    DEBUG_PRINT(TOPIC_CONTROL);
    DEBUG_PRINTLN(" -m 'START'\n");
    
    DEBUG_PRINT("Heap before tasks: ");
    DEBUG_PRINTLN(ESP.getFreeHeap());
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
    
    DEBUG_PRINT("Heap after tasks: ");
    DEBUG_PRINTLN(ESP.getFreeHeap());
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
            DEBUG_PRINT("[UWB CMD] ");
            DEBUG_PRINTLN(cmd);
        }
    }
    //DEBUG_PRINT("Free heap: ");
    //DEBUG_PRINTLN(ESP.getFreeHeap());
    vTaskDelay(pdMS_TO_TICKS(200));  // Minimal work - loop() runs on Core 1 by default
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
        unsigned long cycleStart = millis();
        
        uint8_t tagCount = rfid.pollingMultiple(RFID_POLLING_COUNT);
        
        // Wait until EITHER:
        // - Minimum time has passed
        // - UWB has accumulated data
        const unsigned long MIN_CYCLE_MS = 500;
        while (millis() - cycleStart < MIN_CYCLE_MS) {
            // Check if UWB has data
            bool hasUwbData = false;
            if (xSemaphoreTake(anchorStatsMutex, pdMS_TO_TICKS(5))) {
                hasUwbData = !anchorStatsMap.empty();
                xSemaphoreGive(anchorStatsMutex);
            }
            
            if (hasUwbData) break; // Early exit if data ready
            
            vTaskDelay(pdMS_TO_TICKS(50)); // Check every 50ms
        }
        
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
    DEBUG_PRINTLN("\n=== OUTPUT TASK STARTUP ===");
    UBaseType_t stackSize = uxTaskGetStackHighWaterMark(NULL);
    DEBUG_PRINT("Initial stack available: ");
    DEBUG_PRINT(stackSize * sizeof(StackType_t));
    DEBUG_PRINTLN(" bytes");
    DEBUG_PRINTLN("===========================\n");
    
    while (true) {
        // WiFi keepalive - reconnect if disconnected
        if (WiFi.status() != WL_CONNECTED) {
            DEBUG_PRINTLN("\n[WiFi] Connection lost! Reconnecting...");
            setupWiFi();
        }
        
        // MQTT keepalive (runs on Core 0 with WiFi/network stack)
        reconnectMQTT(); // Non-blocking retry logic
        
        if (mqttClient.connected()) {
            mqttClient.loop();
        }
        
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
            if (mqttClient.connected()) {
                // Do all the heavy work here (JSON building + MQTT publishing)
                combineDataFromPollingAndSend(cycleToProcess);
            } else {
                DEBUG_PRINTLN("[MQTT] Offline - Dropping data cycle to ensure freshness");
            }
            
            // Clear anchor statistics for next cycle
            // Time-based expiration in updateAnchorStatistics() handles staleness
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
    DEBUG_PRINTLN("\n--- Initializing RFID Module ---");
    
    rfid.begin(&rfidSerial, RFID_BAUD, RFID_RX_PIN, RFID_TX_PIN, false);
    rfid.waitModuleInitialization();
    rfid.setRegion(CURRENT_REGION);
    rfid.verifyRegion();
    
    // Set receiver gain to maximum for better sensitivity
    rfid.setReceiverParams(0x06, 0x07, 0x01B0); // Mixer Gain: 16dB, IF Gain: 40dB
    
    // Set maximum transmission power
    if (rfid.setTxPower(RFID_MAX_TX_POWER)) {
        DEBUG_PRINTLN("✓ TX Power set successfully");
        DEBUG_PRINT("✓ TX Power: ");
        DEBUG_PRINT(RFID_MAX_TX_POWER / 100.0);
        DEBUG_PRINTLN(" dB");
    } else {
        DEBUG_PRINTLN("✗ TX Power setting failed!");
    }
    
    DEBUG_PRINTLN("✓ RFID Module initialized successfully");
}

// ============================================
// OUTPUT FUNCTIONS
// ============================================

/**
 * Print combined RFID + UWB data triggered by RFID polling cycle
 * Also publishes to MQTT if START signal received
 * JSON format matches RFID+UWB_TEST reference exactly
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
    
    // Count only anchors with valid distance readings
    uint32_t validAnchorCount = 0;
    for (auto& pair : statsMap) {
        if (pair.second.successCount > 0) {
            validAnchorCount++;
        }
    }
    
    // Build and print complete JSON (matching RFID+UWB_TEST format exactly)
    Serial.println("{");
    Serial.printf("  \"polling_cycle\": %u,\n", cycleCount);
    Serial.printf("  \"timestamp\": %lu,\n", timestamp);
    
    // UWB section with averaged distances per anchor (only anchors with valid readings)
    Serial.println("  \"uwb\": {");
    Serial.printf("    \"n_anchors\": %u,\n", validAnchorCount);
    Serial.println("    \"anchors\": [");
    
    bool first = true;
    for (auto& pair : statsMap) {
        const AnchorStats& stats = pair.second;
        
        // Skip anchors with no successful measurements
        if (stats.successCount == 0) continue;
        
        if (!first) Serial.println(",");
        first = false;
        
        float avgDistance = stats.totalDistance / stats.successCount;
        
        Serial.println("      {");
        Serial.printf("        \"mac_address\": \"0x%s\",\n", stats.macAddress.c_str());
        Serial.printf("        \"average_distance_cm\": %.1f,\n", avgDistance);
        Serial.printf("        \"measurements\": %u,\n", stats.successCount);
        Serial.printf("        \"total_sessions\": %u\n", stats.totalCount);
        Serial.print("      }");
    }
    if (validAnchorCount > 0) Serial.println();
    
    Serial.println("    ]");
    Serial.println("  },");
    
    // RFID section
    Serial.println("  \"rfid\": {");
    Serial.printf("    \"tag_count\": %u,\n", tagCount);
    Serial.println("    \"tags\": [");
    
    for (uint8_t i = 0; i < tagCount; i++) {
        Serial.println("      {");
        Serial.printf("        \"epc\": \"%s\",\n", tags[i].epc.c_str());
        Serial.printf("        \"rssi_dbm\": %d\n", tags[i].rssi);
        Serial.print("      }");
        if (i < tagCount - 1) Serial.println(",");
        else Serial.println();
    }
    
    Serial.println("    ]");
    Serial.println("  }");
    Serial.println("}\n");
    
    // Build JSON document for MQTT (using ArduinoJson for proper serialization)
    StaticJsonDocument<4096> doc;
    
    doc["polling_cycle"] = cycleCount;
    doc["timestamp"] = timestamp;
    
    // UWB section (only anchors with valid readings)
    JsonObject uwb = doc.createNestedObject("uwb");
    uwb["n_anchors"] = validAnchorCount;
    JsonArray anchors = uwb.createNestedArray("anchors");
    
    for (auto& pair : statsMap) {
        const AnchorStats& stats = pair.second;
        
        // Skip anchors with no successful measurements
        if (stats.successCount == 0) continue;
        
        JsonObject anchor = anchors.createNestedObject();
        anchor["mac_address"] = "0x" + stats.macAddress;
        float avgDistance = stats.totalDistance / stats.successCount;
        anchor["average_distance_cm"] = avgDistance;
        anchor["measurements"] = stats.successCount;
        anchor["total_sessions"] = stats.totalCount;
    }
    
    // RFID section
    JsonObject rfid_obj = doc.createNestedObject("rfid");
    rfid_obj["tag_count"] = tagCount;
    JsonArray tagsArray = rfid_obj.createNestedArray("tags");
    
    for (uint8_t i = 0; i < tagCount; i++) {
        JsonObject tag = tagsArray.createNestedObject();
        tag["epc"] = tags[i].epc;
        tag["rssi_dbm"] = tags[i].rssi;
    }
    
    // Publish to MQTT if START signal received and we have data
    if (startSignal && (tagCount > 0 || !statsMap.empty())) {
        String payload;
        serializeJson(doc, payload);
        
        bool success = mqttClient.publish(TOPIC_DATA, payload.c_str());
        if (success) {
            DEBUG_PRINT("[MQTT] ✓ Published - Cycle #");
            DEBUG_PRINT(cycleCount);
            DEBUG_PRINT(" (");
            DEBUG_PRINT(tagCount);
            DEBUG_PRINT(" tags, ");
            DEBUG_PRINT(statsMap.size());
            DEBUG_PRINTLN(" UWB)");
        } else {
            DEBUG_PRINTLN("[MQTT] ✗ Publish failed!");
        }
    } else if (startSignal) {
        DEBUG_PRINTLN("[MQTT] ⊘ No data to publish");
    }
}

/**
 * Print combined RFID + UWB data (legacy function, kept for compatibility)
 */
void printCombinedData(UWBSession &uwbSession) {
    DEBUG_PRINTLN("\n╔════════════════════════════════════════╗");
    DEBUG_PRINT("║  Session #");
    DEBUG_PRINT(uwbSession.sessionCount);
    DEBUG_PRINT(" | Time: ");
    DEBUG_PRINT(uwbSession.timestamp);
    DEBUG_PRINTLN(" ║");
    DEBUG_PRINTLN("╚════════════════════════════════════════╝");
    
    // Print UWB data with average distance
    printUWBData(uwbSession);
    
    // Print RFID tags detected during this period
    printRFIDData();
    
    DEBUG_PRINTLN("════════════════════════════════════════\n");
}

void printUWBData(UWBSession &session) {
    DEBUG_PRINTLN("\n[UWB POSITIONING]");
    
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
        DEBUG_PRINT("  Average Distance: ");
        DEBUG_PRINT(avgDistance);
        DEBUG_PRINT(" cm (");
        DEBUG_PRINT(successCount);
        DEBUG_PRINTLN(" anchors)\n");
    } else {
        DEBUG_PRINTLN("  Average Distance: N/A (no successful measurements)\n");
    }
    
    // Print individual anchor distances
    DEBUG_PRINTLN("  Anchor Distances:");
    for (uint8_t i = 0; i < session.nMeasurements; i++) {
        DEBUG_PRINT("    • 0x");
        DEBUG_PRINT(session.measurements[i].macAddress);
        DEBUG_PRINT(": ");
        
        if (session.measurements[i].status == "SUCCESS") {
            DEBUG_PRINT(session.measurements[i].distanceCm);
            DEBUG_PRINTLN(" cm");
        } else {
            DEBUG_PRINTLN(session.measurements[i].status);
        }
    }
}

void printRFIDData() {
    DEBUG_PRINTLN("\n[RFID TAGS]");
    
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
        DEBUG_PRINT("  Tags Detected: ");
        DEBUG_PRINTLN(tagCount);
        DEBUG_PRINTLN("");
        
        for (uint8_t i = 0; i < tagCount; i++) {
            DEBUG_PRINT("  Tag #");
            DEBUG_PRINT(i + 1);
            DEBUG_PRINTLN(":");
            DEBUG_PRINT("    EPC:  ");
            DEBUG_PRINTLN(tags[i].epc);
            DEBUG_PRINT("    RSSI: ");
            DEBUG_PRINT(tags[i].rssi);
            DEBUG_PRINT(" dBm ");
            DEBUG_PRINTLN(rfid.getSignalQuality(tags[i].rssi));
        }
    } else {
        DEBUG_PRINTLN("  No tags detected");
    }
}

// ============================================
// UWB FUNCTIONS
// ============================================

void initializeUWB() {
    DEBUG_PRINTLN("\n--- Initializing UWB Module ---");
    
    uwbSerial.begin(UWB_BAUD, SERIAL_8N1, UWB_RX_PIN, UWB_TX_PIN);
    delay(500);
    
    DEBUG_PRINTLN("✓ DWM3001CDK UART Ready");
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
            DEBUG_PRINTLN("[UWB] Session buffer overflow!");
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
    
    unsigned long now = millis();
    
    // Update anchor statistics using circular buffer with time-based expiration
    if (xSemaphoreTake(anchorStatsMutex, pdMS_TO_TICKS(100))) {
        // First pass: Remove stale entries (older than 3 seconds)
        auto it = anchorStatsMap.begin();
        while (it != anchorStatsMap.end()) {
            if (now - it->second.timestamp > UWB_FRESHNESS_MS) {
                DEBUG_PRINT("[UWB] Removing stale anchor 0x");
                DEBUG_PRINTLN(it->first);
                it = anchorStatsMap.erase(it);
            } else {
                ++it;
            }
        }
        
        // Second pass: Update/add measurements
        for (uint8_t i = 0; i < session.nMeasurements; i++) {
            String macAddr = session.measurements[i].macAddress;
            
            // Check if anchor exists OR if we have space for new anchors
            bool anchorExists = anchorStatsMap.find(macAddr) != anchorStatsMap.end();
            bool hasSpace = anchorStatsMap.size() < UWB_MAX_ANCHORS;
            
            if (!anchorExists && !hasSpace) {
                // Buffer full - find and replace oldest entry
                String oldestMac;
                unsigned long oldestTime = now;
                
                for (auto& pair : anchorStatsMap) {
                    if (pair.second.timestamp < oldestTime) {
                        oldestTime = pair.second.timestamp;
                        oldestMac = pair.first;
                    }
                }
                
                if (!oldestMac.isEmpty()) {
                    DEBUG_PRINT("[UWB] Buffer full, replacing oldest anchor 0x");
                    DEBUG_PRINT(oldestMac);
                    DEBUG_PRINT(" with 0x");
                    DEBUG_PRINTLN(macAddr);
                    anchorStatsMap.erase(oldestMac);
                    anchorExists = false;
                    hasSpace = true;
                }
            }
            
            // Create new anchor stats if needed
            if (!anchorExists) {
                AnchorStats newStats;
                newStats.macAddress = macAddr;
                newStats.totalDistance = 0;
                newStats.successCount = 0;
                newStats.totalCount = 0;
                newStats.timestamp = now;
                anchorStatsMap[macAddr] = newStats;
            }
            
            // Update statistics
            anchorStatsMap[macAddr].totalCount++;
            anchorStatsMap[macAddr].timestamp = now;  // Update timestamp
            
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
    DEBUG_PRINTLN("\n[WiFi] Connecting...");
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        DEBUG_PRINT(".");
    }
    
    DEBUG_PRINTLN("\n[WiFi] ✓ Connected!");
    DEBUG_PRINT("[WiFi] IP: ");
    DEBUG_PRINTLN(WiFi.localIP());
}

void reconnectMQTT() {
    static unsigned long lastReconnectAttempt = 0;
    unsigned long now = millis();

    if (!mqttClient.connected()) {
        if (now - lastReconnectAttempt > 2000) {
            lastReconnectAttempt = now;
            DEBUG_PRINT("[MQTT] Connecting...");
            if (mqttClient.connect("ESP32_RFID_UWB")) {
                DEBUG_PRINTLN(" ✓ Connected!");
                mqttClient.subscribe(TOPIC_CONTROL);
                DEBUG_PRINTLN("[MQTT] Subscribed to control topic");
            } else {
                DEBUG_PRINT(" ✗ Failed, rc=");
                DEBUG_PRINTLN(mqttClient.state());
            }
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
            DEBUG_PRINTLN("\n[CONTROL] ▶ START received - Publishing enabled");
        } else if (msg == "STOP") {
            startSignal = false;
            DEBUG_PRINTLN("\n[CONTROL] ⏸ STOP received - Publishing paused");
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