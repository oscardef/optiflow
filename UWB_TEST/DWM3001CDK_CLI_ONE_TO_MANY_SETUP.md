# DWM3001CDK CLI Firmware - ONE_TO_MANY Ranging Setup Guide

Complete guide to configure 1 tag (controller) + 4 anchors (controllees) using CLI firmware for FiRa ONE_TO_MANY ranging.

---

## 📋 Overview

- **Tag (Controller/Initiator)**: Mobile device that initiates ranging with multiple anchors
- **Anchors (Controllees/Responders)**: Fixed devices that respond to the controller's ranging requests
- **Protocol**: FiRa DS-TWR (Double-Sided Two-Way Ranging)
- **Mode**: ONE_TO_MANY (1 controller → 4 controllees)
- **Update Rate**: 5 Hz (200ms block duration)

---

## 🔧 Part 1: Flash CLI Firmware

### Prerequisites
- Download **J-Flash Lite** from Segger website
- Download CLI firmware hex file from Qorvo SDK

### Flash Each DWM3001CDK (5 devices total)

1. **Connect DWM3001CDK** via USB to your Mac
2. **Open J-Flash Lite**
3. **Select Device**: nRF52833_xxAA
4. **Select hex file**: `CLI_firmware.hex` (from SDK binaries)
5. **Click "Program Device"**
6. **Repeat** for all 5 boards

---

## 🔧 Part 2: Configure Anchors (Controllees)

### Connect to Each Anchor via Serial

```bash
# List available USB devices
ls /dev/cu.usbmodem*

# Connect to anchor serial port (115200 baud)
screen /dev/cu.usbmodemXXXXXXXXXXXX 115200
```

### Configure Anchor 1

```bash
# Configure the ranging parameters
RESPF -MULTI -ADDR=1 -PADDR=0 -CHAN=9 -BLOCK=200 -RRU=DSTWR -ID=42

# Set auto-start on boot
SETAPP RESPF

# Save all settings
SAVE

# Start ranging
START
```

**Expected output:**
```
FiRa Session Parameters: {
SESSION_ID: 42,
CHANNEL_NUMBER: 9,
DEVICE_ROLE: RESPONDER,
RANGING_ROUND_USAGE: DS_TWR_DEFERRED,
SLOT_DURATION [rstu]: 2400,
RANGING_DURATION [ms]: 200,
SLOTS_PER_RR: 25,
MULTI_NODE_MODE: UNICAST,
HOPPING_MODE: Disabled,
RFRAME_CONFIG: SP3,
SFD_ID: 2,
PREAMBLE_CODE_INDEX: 10,
STATIC_STS_IV: "01:02:03:04:05:06",
VENDOR_ID: "07:08",
DEVICE_MAC_ADDRESS: 0x0001,
DST_MAC_ADDRESS: 0x0000
}
OK
```

### Configure Anchor 2

```bash
RESPF -MULTI -ADDR=2 -PADDR=0 -CHAN=9 -BLOCK=200 -RRU=DSTWR -ID=42
SETAPP RESPF
SAVE
START
```

### Configure Anchor 3

```bash
RESPF -MULTI -ADDR=3 -PADDR=0 -CHAN=9 -BLOCK=200 -RRU=DSTWR -ID=42
SETAPP RESPF
SAVE
START
```

### Configure Anchor 4

```bash
RESPF -MULTI -ADDR=4 -PADDR=0 -CHAN=9 -BLOCK=200 -RRU=DSTWR -ID=42
SETAPP RESPF
SAVE
START
```

**Exit screen:** Press `Ctrl+A` then `K`, confirm with `Y`

**⚠️ IMPORTANT:** After configuring all anchors, **disconnect and power cycle** each one to ensure settings are saved and auto-start works on boot.

---

## 🔧 Part 3: Configure Tag (Controller)

### Connect to Tag via Serial

```bash
# List available USB devices
ls /dev/cu.usbmodem*

# Connect to tag serial port (115200 baud)
screen /dev/cu.usbmodemXXXXXXXXXXXX 115200
```

### Configure Tag for 4 Anchors

```bash
# Configure the ranging parameters
INITF -MULTI -ADDR=0 -PADDR=[1,2,3,4] -CHAN=9 -BLOCK=200 -RRU=DSTWR -ID=42

# Set auto-start on boot
SETAPP INITF

# Enable UART on hardware pins (P0.06 TX, P0.08 RX) for ESP32 integration
UART 1

# Save all settings
SAVE

# Start ranging
START
```

**⚠️ CRITICAL:** After configuration, **disconnect the tag and power cycle it**. This ensures all settings (including auto-start and UART redirection) are properly saved and activated on boot.

**Expected output:**
```
FiRa Session Parameters: {
SESSION_ID: 42,
CHANNEL_NUMBER: 9,
DEVICE_ROLE: INITIATOR,
RANGING_ROUND_USAGE: DS_TWR_DEFERRED,
SLOT_DURATION [rstu]: 2400,
RANGING_DURATION [ms]: 200,
SLOTS_PER_RR: 25,
MULTI_NODE_MODE: ONE_TO_MANY,
HOPPING_MODE: Disabled,
RFRAME_CONFIG: SP3,
SFD_ID: 2,
PREAMBLE_CODE_INDEX: 10,
STATIC_STS_IV: "01:02:03:04:05:06",
VENDOR_ID: "07:08",
DEVICE_MAC_ADDRESS: 0x0000,
DST_MAC_ADDRESS[0]: 0x0001,
DST_MAC_ADDRESS[1]: 0x0002,
DST_MAC_ADDRESS[2]: 0x0003,
DST_MAC_ADDRESS[3]: 0x0004
}
OK
```

---

## ✅ Verify Ranging

After starting the tag, you should see continuous distance measurements:

```
SESSION_INFO_NTF: {session_handle=1, sequence_number=1, block_index=1, n_measurements=4
 [mac_address=0x0001, status="SUCCESS", distance[cm]=245];
 [mac_address=0x0002, status="SUCCESS", distance[cm]=312];
 [mac_address=0x0003, status="SUCCESS", distance[cm]=189];
 [mac_address=0x0004, status="SUCCESS", distance[cm]=403]}
SESSION_INFO_NTF: {session_handle=1, sequence_number=2, block_index=2, n_measurements=4
 [mac_address=0x0001, status="SUCCESS", distance[cm]=247];
 [mac_address=0x0002, status="SUCCESS", distance[cm]=315];
 [mac_address=0x0003, status="SUCCESS", distance[cm]=191];
 [mac_address=0x0004, status="SUCCESS", distance[cm]=405]}
```

**Distance updates every 200ms (5 Hz)**

---

## 📊 Configuration Parameters Explained

| Parameter | Value | Description |
|-----------|-------|-------------|
| `-MULTI` | flag | Enable ONE_TO_MANY mode (controller only) |
| `-ADDR=X` | 0-65535 | Device MAC address (0=controller, 1-4=controllees) |
| `-PADDR=X` | address or [list] | Peer address(es). Controller uses `[1,2,3,4]`, controllees use `0` |
| `-CHAN=9` | 5 or 9 | UWB channel (9 recommended for better range) |
| `-BLOCK=200` | ≥1 ms | Block duration - time for one ranging cycle (200ms = 5Hz) |
| `-RRU=DSTWR` | SSTWR/DSTWR/etc | Ranging Round Usage (DS-TWR = Double-Sided TWR) |
| `-ID=42` | ≠0 | Session ID - **must match** between controller and controllees |

### Special Commands

| Command | Description |
|---------|-------------|
| `SETAPP INITF` | Set tag to auto-start as initiator on boot |
| `SETAPP RESPF` | Set anchor to auto-start as responder on boot |
| `SETAPP NONE` | Disable auto-start (manual control) |
| `UART 1` | **Redirect CLI to hardware UART pins** (P0.06 TX, P0.08 RX) for ESP32 integration |
| `UART 0` | Switch CLI back to USB-CDC (default) |
| `SAVE` | Save all settings to flash (auto-start, UART mode, session config) |
| `GETAPP` | Check current auto-start application |

---

## 🔌 ESP32 Integration via UART

The `UART 1` command redirects the CLI output from USB to the **hardware UART pins**, allowing an ESP32 to read ranging data directly.

### Hardware Connections

**DWM3001CDK → ESP32-S3:**
- **P0.06 (TX)** → GPIO18 (RX)
- **P0.08 (RX)** → GPIO17 (TX)
- **GND** → GND

### Why UART 1 is needed

By default, CLI firmware uses **USB-CDC** (virtual serial over USB). The `UART 1` command switches output to physical UART pins so an external microcontroller can read the ranging data without a computer.

**⚠️ Only configure UART on the TAG**, not the anchors (anchors don't need external monitoring).

---

## 🔍 Troubleshooting

### RX_TIMEOUT on all anchors
- ✅ Verify all 4 anchors are running (START command)
- ✅ Check SESSION_ID matches (42 on all devices)
- ✅ Restart anchors after changing tag configuration
- ✅ Try increasing BLOCK duration to 300-400ms

### RX_MAC_IE_DEC_FAILED
- ✅ Verify SESSION_ID matches between tag and anchor
- ✅ Check all parameters match (CHAN, RRU, etc.)
- ✅ Restart both devices

### INITF gives KO
- ❌ Don't use `SETAPP INITF -parameters...` (parameters are ignored!)
- ✅ Use direct command: `INITF -parameters...`
- ✅ Put `-MULTI` flag at the beginning: `INITF -MULTI -ADDR=0 ...`

### Invalid destination address list
- ✅ Make sure `-MULTI` flag is included in INITF command
- ✅ Verify `MULTI_NODE_MODE: ONE_TO_MANY` appears in configuration output

---

## 🚀 Next Steps

### ESP32 Integration
- Connect DWM3001CDK UART to ESP32-S3
- Parse `SESSION_INFO_NTF` messages for distance data
- Implement trilateration algorithm for (x,y,z) position

### Optimization
- Adjust `-BLOCK` duration (100ms = 10Hz, 500ms = 2Hz battery-saving)
- Calibrate antenna delays for better accuracy
- Set anchor positions in 3D space for trilateration

### Scaling to 30+ Anchors
- Use multiple sessions (4 sessions × 8 anchors each)
- Implement proximity filtering (only range with nearby anchors)
- Consider switching to UCI firmware for programmatic control

---

## 📝 Command Reference Card

### Quick Setup (Copy-Paste Ready)

**Anchors:**
```bash
# Anchor 1
screen /dev/cu.usbmodem[TAB] 115200
RESPF -MULTI -ADDR=1 -PADDR=0 -CHAN=9 -BLOCK=200 -RRU=DSTWR -ID=42
SAVE
START
# Ctrl+A, K, Y to exit

# Repeat for anchors 2, 3, 4 (change -ADDR=2, 3, 4)
```

**Tag:**
```bash
screen /dev/cu.usbmodem[TAB] 115200
INITF -MULTI -ADDR=0 -PADDR=[1,2,3,4] -CHAN=9 -BLOCK=200 -RRU=DSTWR -ID=42
SAVE
START
# Ctrl+A, K, Y to exit
```

---

## 📚 Additional Resources

- **SDK Manual**: `DW3_QM33_SDK_1.1.1/SDK/Documentation/`
- **CLI Commands**: Type `HELP INITF` or `HELP RESPF` in serial terminal
- **Python Tools**: `uwb-qorvo-tools` for UCI firmware control
- **Hardware Guide**: DWM3001CDK datasheet and pinout

---

**✅ Setup Complete!** You now have a working 1-to-4 UWB ranging system with 5Hz updates.
