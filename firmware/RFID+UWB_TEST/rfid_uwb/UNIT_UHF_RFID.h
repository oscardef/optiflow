/*
 * SPDX-FileCopyrightText: 2024 M5Stack Technology CO LTD
 *
 * SPDX-License-Identifier: MIT
 */
#ifndef _UNIT_UHF_RFID_H_
#define _UNIT_UHF_RFID_H_

#include <Arduino.h>
#include "pins_arduino.h"

/*

Header Type Command PL(MSB) PL(LSB) Parameter Checksum End
  BB    00     07     00      01        01       09     7E
                     param length

*/

struct CARD {
    uint8_t rssi;
    uint8_t pc[2];
    uint8_t epc[12];
    String rssi_str;
    String pc_str;
    String epc_str;
};

class Unit_UHF_RFID {
   private:
    HardwareSerial *_serial;
    bool waitMsg(unsigned long timerout = 500);
    void cleanBuffer();
    void cleanCardsBuffer();
    bool saveCardInfo(CARD *card);
    bool filterCardInfo(String epc);

   public:
    bool _debug;
    uint8_t buffer[256] = {0};
    CARD cards[200];

   public:
    void begin(HardwareSerial *serial = &Serial2, int baud = 115200, uint8_t RX = 16, uint8_t TX = 17,
               bool debug = false);
    String getVersion();
    String selectInfo();
    uint8_t pollingOnce();
    uint8_t pollingMultiple(uint16_t polling_count);
    bool select(uint8_t *epc);
    bool setTxPower(uint16_t db);
    void sendCMD(uint8_t *data, size_t size);
    bool writeCard(uint8_t *data, size_t size, uint8_t membank, uint16_t sa, uint32_t access_password = 0);
    bool readCard(uint8_t *data, size_t size, uint8_t membank, uint16_t sa, uint32_t access_password = 0);
    
    // Initialization and configuration functions
    void initializeModule(uint8_t rx_pin, uint8_t tx_pin);
    bool setRegion(uint8_t regionCode);
    bool verifyRegion();
    String getRegionName(uint8_t regionCode);
    bool setReceiverParams(uint8_t mixer_g, uint8_t if_g, uint16_t thrd);
    
    // Display and utility functions
    void displayTagInfo(uint8_t tagIndex);
    bool readTID(uint8_t tagIndex);
    String getSignalQuality(int rssi);
};

#endif