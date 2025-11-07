/*
 * UHF RFID Reader for ESP32-S3 with Maximum Power
 * 
 * This code connects an ESP32-S3 dev board to a JRD-100 UHF RFID module
 * and continuously scans for RFID tags at maximum transmission power (26dB)
 * 
 * Wiring:
 * ESP32-S3 -> UHF RFID Module
 * TX (GPIO7) -> RX (white wire on RFID module)
 * RX (GPIO6) -> TX (blue wire on RFID module)
 * GND -> GND (black wire)
 * 5V -> VCC (red wire)
 */

#include "UNIT_UHF_RFID.h"

// ============================================
// CONFIGURATION
// ============================================
#define RX_PIN 6                    // ESP32-S3 RX pin (RFID TX connects here)
#define TX_PIN 7                    // ESP32-S3 TX pin (RFID RX connects here)
#define READ_TID_MEMORY false       // Set to true to read TID (Tag Identifier)
#define SCAN_INTERVAL_MS 1       // Time between scans in milliseconds
#define POLLING_COUNT 100            // Number of polling iterations per scan
#define MAX_TX_POWER 3000           // Maximum power in 0.01dB units (26.00dB)

// Region Codes
#define REGION_CHINA1   0x01        // 920–925 MHz
#define REGION_USA      0x02        // 902–928 MHz  
#define REGION_EUROPE   0x03        // 865–868 MHz
#define REGION_KOREA    0x04        // 917–923.5 MHz

#define CURRENT_REGION  REGION_CHINA1

// ============================================
// GLOBAL OBJECTS
// ============================================
Unit_UHF_RFID uhf;

// ============================================
// FUNCTION DECLARATIONS
// ============================================
void initializeRFIDModule();
void setRegion(uint8_t regionCode);
void verifyRegion();
String getRegionName(uint8_t regionCode);
void setReceiverParams(uint8_t mixer_g, uint8_t if_g, uint16_t thrd);
void scanAndDisplayTags();
void displayTagInfo(uint8_t tagIndex);
void readTID(uint8_t tagIndex);
String getSignalQuality(int rssi);

// ============================================
// SETUP
// ============================================
void setup() {
    Serial.begin(115200);
    delay(1000);
    
    Serial.println("=================================");
    Serial.println("ESP32-S3 UHF RFID Reader");
    Serial.println("Maximum Power Mode (26dB)");
    Serial.println("=================================");
    
    initializeRFIDModule();
    setRegion(CURRENT_REGION);
    verifyRegion();

    // Set receiver gain to maximum for better sensitivity
    setReceiverParams(0x06, 0x07, 0x01B0); // Mixer Gain: 16dB, IF Gain: 40dB
    
    // Set maximum transmission power
    if (uhf.setTxPower(MAX_TX_POWER)) {
        Serial.println("✓ TX Power set successfully");
    } else {
        Serial.println("✗ TX Power setting failed!");
    }


    Serial.printf("Transmission power set to: %.2f dB\n", MAX_TX_POWER / 100.0);
    
    Serial.println("\n=================================");
    Serial.println("Ready to scan RFID tags!");
    Serial.println("=================================\n");
}

// ============================================
// MAIN LOOP
// ============================================
void loop() {
    scanAndDisplayTags();
    delay(SCAN_INTERVAL_MS);
}

// ============================================
// FUNCTION IMPLEMENTATIONS
// ============================================

/**
 * Initialize the RFID module and wait for it to respond
 */
void initializeRFIDModule() {
    Serial.println("Initializing RFID module...");
    uhf.begin(&Serial2, 115200, RX_PIN, TX_PIN, false);
    
    String info = "";
    while (1) {
        info = uhf.getVersion();
        if (info != "ERROR") {
            Serial.println(info);
            break;
        }
        delay(100);
    }
}

/**
 * Set the working region/frequency band
 * @param regionCode Region code (REGION_EUROPE, REGION_USA, etc.)
 */
void setRegion(uint8_t regionCode) {
    Serial.printf("Setting region to %s...\n", getRegionName(regionCode).c_str());
    
    uint8_t setRegionCmd[] = {0xBB, 0x00, 0x07, 0x00, 0x01, regionCode, 0x00, 0x7E};
    
    // Calculate checksum (sum of bytes 1 to n-2)
    uint8_t checksum = 0;
    for (int i = 1; i < sizeof(setRegionCmd) - 2; i++) {
        checksum += setRegionCmd[i];
    }
    setRegionCmd[sizeof(setRegionCmd) - 2] = checksum;
    
    uhf.sendCMD(setRegionCmd, sizeof(setRegionCmd));
    delay(200);
    
    // Clear response buffer
    while (Serial2.available()) {
        Serial2.read();
    }
}

/**
 * Verify the current region setting
 */
void verifyRegion() {
    Serial.println("Verifying region setting...");
    
    uint8_t getRegionCmd[] = {0xBB, 0x00, 0x08, 0x00, 0x00, 0x08, 0x7E};
    uhf.sendCMD(getRegionCmd, sizeof(getRegionCmd));
    
    delay(300);
    
    uint8_t response[40];
    int idx = 0;
    unsigned long start = millis();
    
    while (millis() - start < 1000 && idx < 40) {
        if (Serial2.available()) {
            response[idx++] = Serial2.read();
        }
    }
    
    // Parse response
    for (int i = 0; i < idx - 6; i++) {
        if (response[i] == 0xBB && response[i + 1] == 0x01 && response[i + 2] == 0x08) {
            uint8_t region = response[i + 5];
            Serial.printf("✓ Current region: %s (0x%02X)\n", getRegionName(region).c_str(), region);
            return;
        }
    }
    
    Serial.println("⚠️  Could not verify region");
}

/**
 * Get human-readable region name
 * @param regionCode Region code
 * @return Region name with frequency range
 */
String getRegionName(uint8_t regionCode) {
    switch (regionCode) {
        case REGION_CHINA1:  return "CHINA (920–925 MHz)";
        case REGION_USA:     return "USA (902–928 MHz)";
        case REGION_EUROPE:  return "EUROPE (865–868 MHz)";
        case REGION_KOREA:   return "KOREA (917–923.5 MHz)";
        default:             return "UNKNOWN";
    }
}

/**
 * Scan for RFID tags and display their information
 */
void scanAndDisplayTags() {
    Serial.println("--- Scanning for RFID tags ---");
    
    uint8_t result = uhf.pollingMultiple(POLLING_COUNT);
    
    if (result > 0) {
        Serial.printf("\n✓ Found %d tag(s):\n\n", result);
        
        for (uint8_t i = 0; i < result; i++) {
            displayTagInfo(i);
            
#if READ_TID_MEMORY
            readTID(i);
#endif
        }
        Serial.println();
    } else {
        Serial.println("✗ No tags detected");
    }
}

/**
 * Display information for a specific tag
 * @param tagIndex Index of the tag in the cards array
 */
void displayTagInfo(uint8_t tagIndex) {
    Serial.printf("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n");
    Serial.printf("Tag #%d:\n", tagIndex + 1);
    Serial.printf("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n");
    
    // EPC - Electronic Product Code (main tag ID)
    Serial.println("📱 EPC (Tag ID): " + uhf.cards[tagIndex].epc_str);
    
    // RSSI - Received Signal Strength Indicator
    int rssi_dbm = (int8_t)uhf.cards[tagIndex].rssi;
    Serial.printf("📶 Signal Strength: %d dBm %s\n", 
                  rssi_dbm, getSignalQuality(rssi_dbm).c_str());
    
    // PC - Protocol Control
    Serial.println("🔧 Protocol Control: " + uhf.cards[tagIndex].pc_str);
    
    Serial.println();
}

/**
 * Read and display TID (Tag Identifier) for a specific tag
 * @param tagIndex Index of the tag in the cards array
 */
void readTID(uint8_t tagIndex) {
    if (uhf.select(uhf.cards[tagIndex].epc)) {
        uint8_t tid_buffer[12] = {0};
        
        if (uhf.readCard(tid_buffer, 8, 0x02, 0, 0x00000000)) {
            Serial.print("🔖 TID (Chip Serial): ");
            for (uint8_t j = 0; j < 8; j++) {
                Serial.printf("%02X", tid_buffer[j]);
            }
            Serial.println("\n");
        } else {
            Serial.println("🔖 TID: Read failed\n");
        }
    } else {
        Serial.println("⚠️  Could not select tag for TID read\n");
    }
}

/**
 * Get signal quality description based on RSSI value
 * @param rssi RSSI value in dBm
 * @return Signal quality description
 */
String getSignalQuality(int rssi) {
    if (rssi > -50)      return "(Excellent)";
    else if (rssi > -65) return "(Good)";
    else if (rssi > -75) return "(Fair)";
    else                 return "(Weak)";
}

/**
 * Set receiver demodulator parameters (Mixer Gain, IF AMP Gain, Threshold)
 * @param mixer_g Mixer gain code (0x00-0x06)
 * @param if_g IF AMP gain code (0x00-0x07)
 * @param thrd Signal demodulation threshold
 */
void setReceiverParams(uint8_t mixer_g, uint8_t if_g, uint16_t thrd) {
    Serial.println("Setting receiver parameters for maximum sensitivity...");
    
    uint8_t setParamsCmd[] = {
        0xBB, 0x00, 0xF0, 0x00, 0x04, 
        mixer_g, 
        if_g, 
        (uint8_t)(thrd >> 8), 
        (uint8_t)(thrd & 0xFF), 
        0x00, 0x7E
    };
    
    // Calculate checksum
    uint8_t checksum = 0;
    for (int i = 1; i < sizeof(setParamsCmd) - 2; i++) {
        checksum += setParamsCmd[i];
    }
    setParamsCmd[sizeof(setParamsCmd) - 2] = checksum;
    
    // Clear any old data from the serial buffer
    while (Serial2.available()) {
        Serial2.read();
    }

    uhf.sendCMD(setParamsCmd, sizeof(setParamsCmd));
    
    // Wait for and verify the response
    unsigned long startTime = millis();
    uint8_t response[10];
    int responseIdx = 0;
    bool success = false;

    while (millis() - startTime < 500 && responseIdx < sizeof(response)) {
        if (Serial2.available()) {
            response[responseIdx++] = Serial2.read();
        }
    }

    // Check for success response: BB 01 F0 00 01 00 F2 7E
    if (responseIdx >= 7 && response[0] == 0xBB && response[1] == 0x01 && response[2] == 0xF0 && response[5] == 0x00) {
        Serial.printf("✓ Receiver params set successfully: MixerGain=0x%02X, IFGain=0x%02X, Threshold=0x%04X\n", mixer_g, if_g, thrd);
    } else {
        Serial.println("⚠️  Failed to set receiver parameters. No valid response from module.");
    }
}