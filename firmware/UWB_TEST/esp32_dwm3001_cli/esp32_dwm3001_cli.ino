/*
 * ESP32-S3 + DWM3001CDK (CLI Firmware)
 * JSON-like Parser with Timestamp
 * Ready for WiFi transmission
 * 
 * Wiring:
 * - ESP32 GPIO17 (TX) -> DWM3001CDK P0.15 (RX)
 * - ESP32 GPIO18 (RX) -> DWM3001CDK P0.19 (TX)
 * - GND -> GND
 */

#include <HardwareSerial.h>

HardwareSerial DWM_Serial(2);  // UART2
#define DWM_TX_PIN 17
#define DWM_RX_PIN 18
#define DWM_BAUD 115200

String rxBuffer = "";
String sessionBuffer = "";  // Buffer for complete SESSION_INFO_NTF
bool inSession = false;
uint32_t sessionCount = 0;

void setup() {
  Serial.begin(115200);
  delay(500);
  
  Serial.println("\nESP32-S3 + DWM3001CDK Parser");
  Serial.println("JSON Format with Timestamp\n");
  
  DWM_Serial.begin(DWM_BAUD, SERIAL_8N1, DWM_RX_PIN, DWM_TX_PIN);
  delay(500);
  
  Serial.println("UART Ready\n");
}

void loop() {
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
  
  // Forward commands to DWM
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

void processLine(String line) {
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
      printSessionJSON();
      sessionBuffer = "";
    }
  }
}

void printSessionJSON() {
  sessionCount++;
  
  // Get timestamp in milliseconds
  unsigned long timestamp = millis();
  
  // Print JSON-like format
  Serial.println("{");
  Serial.print("  \"timestamp\": ");
  Serial.print(timestamp);
  Serial.println(",");
  Serial.print("  \"session_count\": ");
  Serial.print(sessionCount);
  Serial.println(",");
  
  // Extract session_handle
  int handleIdx = sessionBuffer.indexOf("session_handle=");
  if (handleIdx != -1) {
    int handleEnd = sessionBuffer.indexOf(",", handleIdx);
    String handle = sessionBuffer.substring(handleIdx + 15, handleEnd);
    Serial.print("  \"session_handle\": ");
    Serial.print(handle);
    Serial.println(",");
  }
  
  // Extract sequence_number
  int seqIdx = sessionBuffer.indexOf("sequence_number=");
  if (seqIdx != -1) {
    int seqEnd = sessionBuffer.indexOf(",", seqIdx);
    String seq = sessionBuffer.substring(seqIdx + 16, seqEnd);
    Serial.print("  \"sequence_number\": ");
    Serial.print(seq);
    Serial.println(",");
  }
  
  // Extract block_index
  int blockIdx = sessionBuffer.indexOf("block_index=");
  if (blockIdx != -1) {
    int blockEnd = sessionBuffer.indexOf(",", blockIdx);
    String block = sessionBuffer.substring(blockIdx + 12, blockEnd);
    Serial.print("  \"block_index\": ");
    Serial.print(block);
    Serial.println(",");
  }
  
  // Extract n_measurements
  int nMeasIdx = sessionBuffer.indexOf("n_measurements=");
  if (nMeasIdx != -1) {
    int nMeasEnd = sessionBuffer.indexOf("\n", nMeasIdx);
    String nMeas = sessionBuffer.substring(nMeasIdx + 15, nMeasEnd);
    nMeas.trim();
    Serial.print("  \"n_measurements\": ");
    Serial.print(nMeas);
    Serial.println(",");
  }
  
  // Parse measurements array
  Serial.println("  \"measurements\": [");
  
  int searchStart = 0;
  bool firstMeas = true;
  
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
    String mac = measurement.substring(macStart, macStart + 4);
    
    // Extract status
    int statusIdx = measurement.indexOf("status=\"");
    int statusEnd = measurement.indexOf("\"", statusIdx + 8);
    String status = measurement.substring(statusIdx + 8, statusEnd);
    
    // Extract distance if SUCCESS
    int distance = -1;
    if (status == "SUCCESS") {
      int distIdx = measurement.indexOf("distance[cm]=");
      if (distIdx != -1) {
        distIdx += 13; // Move past "distance[cm]="
        // Find end: could be ], ]}, or ;}
        int distEnd = distIdx;
        while (distEnd < measurement.length() && 
               isDigit(measurement.charAt(distEnd))) {
          distEnd++;
        }
        String distStr = measurement.substring(distIdx, distEnd);
        distance = distStr.toInt();
      }
    }
    
    // Print measurement
    if (!firstMeas) Serial.println(",");
    firstMeas = false;
    
    Serial.println("    {");
    Serial.print("      \"mac_address\": \"0x");
    Serial.print(mac);
    Serial.println("\",");
    Serial.print("      \"status\": \"");
    Serial.print(status);
    Serial.println("\",");
    Serial.print("      \"distance_cm\": ");
    Serial.println(distance);
    Serial.print("    }");
    
    searchStart = measEnd + 1;
  }
  
  Serial.println();
  Serial.println("  ]");
  Serial.println("}");
  Serial.println();
}