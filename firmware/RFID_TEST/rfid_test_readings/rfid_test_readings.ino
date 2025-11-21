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
void scanAndDisplayTags();

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
    
    uhf.initializeModule(RX_PIN, TX_PIN);
    uhf.setRegion(CURRENT_REGION);
    uhf.verifyRegion();

    // Set receiver gain to maximum for better sensitivity
    uhf.setReceiverParams(0x06, 0x07, 0x01B0); // Mixer Gain: 16dB, IF Gain: 40dB
    
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
 * Scan for RFID tags and display their information
 */
void scanAndDisplayTags() {
    Serial.println("--- Scanning for RFID tags ---");
    
    uint8_t result = uhf.pollingMultiple(POLLING_COUNT);
    
    if (result > 0) {
        Serial.printf("\n✓ Found %d tag(s):\n\n", result);
        
        for (uint8_t i = 0; i < result; i++) {
            uhf.displayTagInfo(i);
            
#if READ_TID_MEMORY
            uhf.readTID(i);
#endif
        }
        Serial.println();
    } else {
        Serial.println("✗ No tags detected");
    }
}