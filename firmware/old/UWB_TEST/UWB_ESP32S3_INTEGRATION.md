# UWB Connection to ESP32-S3: Technical Implementation Guide

## Table of Contents
1. [Communication Architecture](#communication-architecture)
2. [Hardware Interconnection](#hardware-interconnection)
3. [Interface Selection: UART over SPI](#interface-selection-uart-over-spi)
4. [FiRa Protocol & Ranging Mode Selection](#fira-protocol--ranging-mode-selection)
5. [Multi-Anchor Configuration](#multi-anchor-configuration)
6. [Data Format and Parsing](#data-format-and-parsing)
7. [System Limitations & Scalability](#system-limitations--scalability)
8. [Future Production Considerations](#future-production-considerations)

---

## Communication Architecture

The UWB positioning system is implemented using **Qorvo DWM3001CDK** modules operating with **CLI (Command Line Interface) firmware**. The wearable tag communicates with the ESP32-S3 microcontroller via **UART** to transmit real-time ranging data from multiple anchors.

### System Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Wearable Device                      │
│                                                         │
│  ┌──────────────┐         UART          ┌────────────┐ │
│  │ DWM3001CDK   │   (115200 baud)       │ ESP32-S3   │ │
│  │  (CLI FW)    │ ◄──────────────────►  │            │ │
│  │              │   P0.15 TX → GPIO18   │            │ │
│  │  UWB Tag     │   P0.19 RX ← GPIO17   │  Main MCU  │ │
│  └──────┬───────┘                       └─────┬──────┘ │
│         │                                     │        │
│         │ UWB Ranging                         │        │
│         │ (FiRa DS-TWR)                       │ WiFi   │
└─────────┼─────────────────────────────────────┼────────┘
          │                                     │
          ▼                                     ▼
    ┌─────────────┐                      ┌──────────┐
    │  Anchor 1   │                      │  Central │
    │  (0x0001)   │                      │  Server  │
    ├─────────────┤                      └──────────┘
    │  Anchor 2   │
    │  (0x0002)   │
    ├─────────────┤
    │  Anchor 3   │
    │  (0x0003)   │
    ├─────────────┤
    │  Anchor 4   │
    │  (0x0004)   │
    └─────────────┘
```

---

## Hardware Interconnection

### Physical Connection

**Wiring Diagram:**
```
ESP32-S3 DevKit          DWM3001CDK (Tag)
-----------------        ----------------
GPIO17 (TX)         -->  P0.19 (RX)
GPIO18 (RX)         <--  P0.15 (TX)
GND                 ---  GND
5V                  -->  5V (via board LDO)
```

**Pin Selection Rationale:**
- **GPIO17/18**: Hardware UART2 on ESP32-S3
- **P0.15/P0.19**: Configured via CLI firmware `UART 1` command
- **5V Power**: DWM3001CDK dev board has onboard 3.3V LDO regulator

### UART Configuration

**Communication Parameters:**
| Parameter | Value | Notes |
|-----------|-------|-------|
| **Baud Rate** | 115,200 bps | Standard high-speed UART |
| **Data Bits** | 8 | Standard frame format |
| **Parity** | None | Error detection via protocol layer |
| **Stop Bits** | 1 | Standard configuration |
| **Flow Control** | None | Software buffering sufficient |
| **Logic Level** | 3.3V TTL | ESP32 and nRF52833 compatible |

**Bandwidth Analysis:**
```
Required data rate:
- 4 anchors × ~25 bytes/measurement = 100 bytes per ranging cycle
- Update rate: 5 Hz (200ms blocks)
- Data throughput: 100 bytes × 5 Hz = 500 bytes/sec = 4 kbps

UART capacity:
- 115200 baud ≈ 11,520 bytes/sec = 92 kbps
- Safety margin: 23× over-provisioned
```

**Conclusion**: UART bandwidth is not a bottleneck. The limiting factor is the UWB ranging protocol timing (200ms per cycle).

---

## Interface Selection: UART over SPI

### Original Plan vs. Implementation

**Initial Design (Report Specification):**
- Interface: SPI (Serial Peripheral Interface)
- Rationale: High-speed, deterministic timing, multi-device bus

**Implemented Solution:**
- Interface: UART (Universal Asynchronous Receiver-Transmitter)
- Rationale: Pre-built CLI firmware, rapid prototyping, adequate performance

### Why the Change: Technical Justification

#### Initial SPI Architecture (Planned)

The preliminary design specified SPI for the following reasons:
- **High-speed synchronous communication** (1-10 Mbps)
- **Multi-device bus capability** (shared MISO/MOSI lines)
- **Deterministic timing** for precision ranging applications
- **Low pin count** with shared bus architecture

**Expected SPI Configuration:**
```
ESP32-S3          DWM3001CDK
---------         ----------
GPIO12 (MISO) <-- SPI MISO
GPIO11 (MOSI) --> SPI MOSI
GPIO10 (CLK)  --> SPI CLK
GPIO9  (CS)   --> SPI CS
GND           --- GND
```

This approach was documented in the report's Configuration Overview section, emphasizing SPI's suitability for "low-latency, DMA-capable, multi-device operation."

#### Reality Check: Qorvo SDK Analysis

**Critical Discovery**: After analyzing the DW3_QM33_SDK, we found that:

1. **SPI is internal-only** in DWM3001CDK architecture:
```
┌────────────────────────────────────┐
│      DWM3001CDK Module             │
│                                    │
│  ┌──────────┐      SPI       ┌────┴────┐
│  │ nRF52833 │ ◄──────────► │ DW3110  │  <-- SPI is INTERNAL
│  │   MCU    │               │ UWB Radio│      between MCU and radio
│  └─────┬────┘               └─────────┘
│        │
│        │ UART (external interface)
│        ▼
│   ┌─────────┐
│   │ P0.15 TX│──────► To ESP32-S3
│   │ P0.19 RX│◄────── From ESP32-S3
│   └─────────┘
└────────────────────────────────────┘
```

**SPI Usage in SDK:**
- **Internal only**: nRF52833 MCU ↔ DW3110 UWB transceiver communication
- **Driver-level**: Low-level register access in `deca_interface.c`
- **Not exposed**: No SPI pins accessible for external host control

2. **No pre-built SPI firmware** available from Qorvo:

| Firmware | Interface | Purpose |
|----------|-----------|---------|
| **CLI** | UART (USB-CDC or hardware pins) | Command-line testing |
| **UCI** | UART (binary protocol) | Programmatic control |
| **QANI** | UART | Network analyzer |
| **HelloWorld** | Embedded (no external interface) | Example skeleton |

#### Why Custom SPI Firmware Was Rejected

**Option Considered**: Rebuild firmware to expose SPI externally to ESP32-S3

**Requirements for custom SPI implementation:**
1. Extract firmware source from `SDK/Firmware/DW3_QM33_SDK_1.1.1.zip`
2. Modify board support package (BSP) to expose SPI pins (P0.xx)
3. Implement custom SPI slave driver for nRF52833
4. Define binary message format for ranging data
5. Implement SPI interrupt handlers without disrupting UWB timing
6. Ensure SPI transactions don't block time-critical ranging operations
7. Build with ARM GCC toolchain and CMake
8. Flash to all 5 DWM3001CDK modules (4 anchors + 1 tag)

**Why this was rejected:**

**1. Firmware Complexity**

The Qorvo SDK firmware is a **FreeRTOS-based real-time system** with:
- UWB MAC layer (FiRa protocol stack)
- TWR (Two-Way Ranging) state machines
- Session management and scheduling
- Calibration and antenna delay compensation
- Non-volatile memory (NVM) persistence

**Development time estimate**: 3-4 weeks for a competent embedded developer, plus extensive debugging and validation.

**2. No Performance Benefit**

**SPI advantages in theory:**
- Higher throughput: 1-10 Mbps typical
- Deterministic timing
- Lower CPU overhead with DMA

**Reality for this application:**
- **Data rate needed**: ~500 bytes/sec for 5Hz ranging with 4 anchors
  ```
  Distance data per block: 4 anchors × 25 bytes/measurement = 100 bytes
  Update rate: 5 Hz (200ms blocks)
  Required bandwidth: 100 bytes × 5 Hz = 500 bytes/sec = 4 kbps
  ```
- **UART at 115200 baud**: ~11.5 kB/s effective throughput
- **Overhead margin**: 23× more bandwidth than needed

**Conclusion**: UART bandwidth is **not a bottleneck**. The limiting factor is the UWB ranging protocol timing (200ms per cycle), not the ESP32↔DWM3001CDK communication.

**3. Loss of Pre-Built Features**

The **CLI firmware** provides production-ready features out-of-box:
- ✅ FiRa ONE_TO_MANY mode (1 tag → 4-8 anchors)
- ✅ Persistent configuration (SAVE command writes to flash)
- ✅ Auto-start on boot (SETAPP command)
- ✅ Calibration management (LISTCAL, antenna delays)
- ✅ Diagnostic modes (DIAG, LISTENER)
- ✅ Battery-optimized ranging (configurable block duration)

**Custom SPI firmware would require reimplementing all these features**, or losing critical functionality.

**4. Multi-Module Deployment Complexity**

The system requires **5 DWM3001CDK modules** (4 anchors + 1 tag).

**With custom firmware:**
- Each device must be flashed individually via J-Link debugger
- Configuration changes require firmware rebuild and re-flash
- Field updates become complex (no over-the-air capability)
- Higher risk of bricking devices during development

**With CLI firmware:**
- One-time flash of pre-built binary
- All configuration via text commands (stored in NVM)
- No recompilation needed for MAC address, session ID, channel changes
- Easy to reset/reconfigure via UART commands

#### Why UART is the Pragmatic Choice

**1. Zero Firmware Development Required**

The **DWM3001CDK-CLI-FreeRTOS.hex** firmware (pre-built binary) provides:
- Complete FiRa ONE_TO_MANY implementation
- UART output on hardware pins (P0.15 TX, P0.19 RX)
- Human-readable ASCII protocol
- Command-response interface for configuration

**Time to working prototype**: 2 days
- Day 1: Flash firmware, configure via USB serial terminal
- Day 2: Connect to ESP32-S3, parse UART output

Compare to **3-4 weeks** for custom SPI firmware development.

**2. Straightforward ESP32-S3 Integration**

**UART parsing implementation** (actual working code):
```cpp
// Simple character-by-character UART reading
while (DWM_Serial.available()) {
  char c = DWM_Serial.read();
  
  // Detect message boundaries
  if (line.indexOf("SESSION_INFO_NTF:") != -1) {
    // Start accumulating multi-line message
  }
  if (line.indexOf("}") != -1) {
    // End of message, parse and extract data
  }
}
```

**SPI implementation would require:**
```cpp
// Complex binary protocol state machine
SPI.beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE0));
digitalWrite(CS_PIN, LOW);
SPI.transfer(CMD_GET_RANGING_DATA);  // Custom command byte
uint8_t length = SPI.transfer(0x00); // Read length byte
for (int i = 0; i < length; i++) {
  buffer[i] = SPI.transfer(0x00);    // Read data bytes
}
// Implement CRC check, frame sync, error handling...
digitalWrite(CS_PIN, HIGH);
SPI.endTransaction();
```

UART wins on **implementation simplicity**.

**3. Rapid Development and Debugging**

| Feature | CLI Firmware (UART) | Custom SPI Firmware |
|---------|---------------------|---------------------|
| **Initial testing** | Screen/PuTTY terminal, human-readable | Logic analyzer or custom tool |
| **Configuration** | Text commands: `INITF -MULTI -ADDR=0` | Recompile and reflash |
| **Debugging** | See raw output in terminal | Binary protocol decoder required |
| **Field updates** | `UART 1` / `SAVE` commands | J-Link programmer and firmware rebuild |
| **Error diagnosis** | Status messages: `"SUCCESS"`, `"RX_TIMEOUT"` | Error codes requiring documentation lookup |

**Real development scenario:**
- **Problem**: Anchor 3 not responding
- **CLI approach**: Connect USB, type `STAT`, see error message in plain text
- **SPI approach**: Attach logic analyzer, decode binary frames, consult protocol spec

**4. Proven Production-Ready Stack**

The **CLI firmware** is:
- ✅ **Validated by Qorvo**: Shipped as official SDK binary
- ✅ **Field-tested**: Used in Qorvo One GUI application
- ✅ **Documented**: Complete command reference provided
- ✅ **Stable**: Based on mature FreeRTOS + FiRa stack

**Custom SPI firmware** would be:
- ❌ **Unvalidated**: Project-specific implementation
- ❌ **Untested at scale**: No external verification
- ❌ **Undocumented**: Require writing custom protocol specification
- ❌ **Higher bug risk**: New code = new bugs

#### UCI Firmware Consideration

The SDK also provides **UCI (Universal Chip Interface) firmware**, which uses UART with a **binary protocol** defined by the FiRa consortium.

**UCI in the Project Timeline:**

**Phase 0 (Initial Testing):** UCI firmware was **essential for rapid hardware validation**
- ✅ Pre-installed on new DWM3001CDK modules
- ✅ Works seamlessly with Qorvo UWB Explorer GUI (visual ranging interface)
- ✅ Zero configuration needed for initial tests
- ✅ Quick Start Guide provided clear instructions
- **Result**: Confirmed hardware functionality in 30 minutes

**Phase 1+ (System Integration):** CLI firmware chosen over UCI for ESP32-S3 integration

**Why UCI Wasn't Chosen for Production:**

**UCI advantages:**
- Programmatic control (no text parsing)
- Standard protocol (documented in `uwb-uci-messages-api-R<x.x.x>.pdf`)
- Python tools provided (`uwb-qorvo-tools` library)
- Excellent for GUI applications (as proven in Phase 0)

**UCI disadvantages for ESP32-S3 integration:**
- ❌ **More complex**: Binary message framing (TLV format, CRC checksums)
- ❌ **Requires Python library** on ESP32 side (not practical for embedded C++)
- ❌ **Less transparent**: Can't easily inspect messages with serial terminal during debugging
- ❌ **Overkill**: Designed for dynamic session management (not needed for fixed 4-anchor setup)
- ❌ **Heavier parsing**: Need to implement UCI binary decoder vs simple ASCII string parsing

**Use case for UCI**: Dynamic anchor selection, multi-session management, or >8 anchor systems. Perfect for desktop GUI tools (Qorvo UWB Explorer), but not optimal for embedded microcontroller integration.

**Bottom line**: UCI was the right tool for **hardware validation**, CLI is the right tool for **ESP32 integration**.

#### Architecture Trade-Offs Summary

| Criterion | SPI (Custom FW) | UART (CLI FW) | UCI (Binary UART) |
|-----------|----------------|---------------|-------------------|
| **Development Time** | 3-4 weeks | 2 days | 1 week |
| **Firmware Complexity** | High (custom protocol) | Zero (pre-built) | Medium (binary parsing) |
| **Debugging Ease** | Low (binary analyzer) | High (human-readable) | Medium (structured binary) |
| **Configuration Flexibility** | Low (rebuild required) | High (text commands) | High (UCI commands) |
| **Performance** | Excellent (1-10 Mbps) | Adequate (115 kbps >> 4 kbps needed) | Adequate (115 kbps) |
| **Scalability** | Good | Limited (8 anchors max) | Excellent (programmatic) |
| **Risk** | High (unproven) | Low (official SDK) | Medium (UCI stack) |
| **Time to Prototype** | Long | Very Short | Short |

**Winner**: **UART with CLI firmware** for rapid prototyping and validation.

### Development Timeline

- **Phase 0**: UCI firmware + Qorvo UWB Explorer GUI → Hardware validation (30 min)
- **Phase 1**: CLI firmware + UART → Multi-anchor ranging working (2 days)
- **Phase 2**: ESP32-S3 UART parser → JSON output functional (1 week)

### Future Migration Path

**When might SPI be needed?**

**Scenario 1: Scaling Beyond 8 Anchors**
- CLI firmware limited to 8 controllees (FiRa TWR protocol constraint)
- For 30+ anchors: Need UCI firmware + programmatic session switching
- But UCI **still uses UART**, not SPI

**Scenario 2: Real-Time Control Requirements**
- If dynamic anchor selection is needed (<200ms response)
- Custom firmware with SPI could reduce latency
- **Current need**: None (anchors are static, tag is mobile)

**Scenario 3: Custom UWB Protocols**
- Implementing non-FiRa ranging modes
- Direct DW3110 register access via SPI
- **Current need**: None (FiRa DS-TWR meets requirements)

**Conclusion**: No foreseeable need to switch to SPI for this application. UART-based implementation is on schedule, meeting performance targets, and poses minimal technical risk.

### CLI Firmware Advantages

The **DWM3001CDK-CLI-FreeRTOS.hex** firmware provides critical features for autonomous operation:

#### 1. Non-Volatile Memory (NVM) Persistence
```bash
# Configure device once via USB
INITF -MULTI -ADDR=0 -PADDR=[1,2,3,4] -CHAN=9 -BLOCK=200 -RRU=DSTWR -ID=42
UART 1              # Redirect to hardware pins
SETAPP INITF        # Set auto-start application
SAVE                # Write to flash memory
```

**After power cycle**: Device automatically starts ranging without USB connection.

#### 2. Auto-Start on Boot
**Perfect for battery-powered anchors:**
- No computer needed after initial configuration
- Anchors power on and immediately begin responding to ranging requests
- Configuration survives firmware updates (stored in separate flash region)

#### 3. Factory Reset Support
```bash
RESTORE             # Reset all settings to defaults
SETAPP NONE         # Clear auto-start
SAVE                # Commit clean state
```

**Use case**: Reconfigure anchors for different deployment locations.

---

## FiRa Protocol & Ranging Mode Selection

### What is FiRa?

**FiRa Consortium** (Fine Ranging) is an industry alliance defining standardized UWB communication protocols for:
- Secure ranging and positioning
- Interoperability between vendors (Apple U1, Samsung, Qorvo, etc.)
- IEEE 802.15.4z compliance

**FiRa Protocol Stack:**
```
┌─────────────────────────┐
│   Application Layer     │  ← Trilateration, Positioning
├─────────────────────────┤
│   FiRa Session Mgmt     │  ← ONE_TO_MANY, Session ID
├─────────────────────────┤
│   MAC Layer (802.15.4z) │  ← TWR Protocol, Time Slots
├─────────────────────────┤
│   PHY Layer (UWB)       │  ← DW3110 Radio, 6-8 GHz
└─────────────────────────┘
```

**Key Features:**
- **Secure Ranging**: STS (Scrambled Timestamp Sequence) encryption prevents relay attacks
- **Time-of-Flight Accuracy**: Sub-10 cm precision indoors
- **Multi-Node Support**: ONE_TO_MANY mode for 1 controller → 8 responders

### Two-Way Ranging (TWR) Modes

TWR measures distance by calculating the round-trip time of UWB signals between two devices.

#### Single-Sided TWR (SS-TWR)

**Protocol Flow:**
```
Tag (Initiator)          Anchor (Responder)
      │                          │
      │───── Poll ────────────►  │  T1 (send)
      │                          │  T2 (receive)
      │                          │
      │  ◄──── Response ────────│  T3 (send)
      │  T4 (receive)            │
      │                          │
      
Distance = c × (T4 - T1 - ProcessingDelay) / 2
```

**Characteristics:**
- ✅ Fast: Only 2 messages per ranging cycle
- ✅ Low power consumption
- ❌ **Clock drift error**: Relies on anchor's clock accuracy
- ❌ **Lower accuracy**: ±20-50 cm typical

**Problem**: If anchor clock runs 10 ppm faster than tag:
```
Real processing time: 1 ms
Measured time with drift: 1.00001 ms
Error: 10 ns × 3×10^8 m/s = 3 meters!
```

#### Double-Sided TWR (DS-TWR)

**Protocol Flow:**
```
Tag (Initiator)          Anchor (Responder)
      │                          │
      │───── Poll ────────────►  │  T1, T2
      │  ◄──── Response ────────│  T3, T4
      │───── Final ──────────►   │  T5, T6
      │                          │

Distance = c × sqrt((T4-T1)(T6-T3) - (T5-T2)(T4-T3)) / ((T4-T1) + (T6-T3))
```

**Characteristics:**
- ✅ **Clock drift cancellation**: Uses cross-correlation between tag and anchor timestamps
- ✅ **High accuracy**: ±5-10 cm typical
- ❌ Slower: 3 messages per ranging cycle
- ❌ Higher power consumption

**Math Explanation:**
By measuring round-trip times in **both directions**, clock drift errors are multiplicative rather than additive, allowing algebraic cancellation. The formula compensates for different clock rates between devices.

#### Deferred vs. Non-Deferred

**Deferred Mode (DSTWR):**
- Response messages sent after processing delay
- Allows time for STS encryption/decryption
- **Recommended for secure ranging**

**Non-Deferred Mode (DSTWRNDEF):**
- Immediate response (faster)
- Less time for security processing
- Used when minimal latency required

### Why We Chose DS-TWR Deferred

**Configuration:**
```bash
INITF -MULTI -ADDR=0 -PADDR=[1,2,3,4] -CHAN=9 -BLOCK=200 -RRU=DSTWR -ID=42
                                                          ^^^^^^
                                                          DS-TWR selected
```

**Decision Matrix:**

| Criterion | SS-TWR | DS-TWR | Winner |
|-----------|--------|--------|--------|
| **Accuracy** | ±20-50 cm | ±5-10 cm | DS-TWR ✅ |
| **Clock Drift Tolerance** | Sensitive | Immune | DS-TWR ✅ |
| **Update Rate** | 10+ Hz possible | 5 Hz typical | SS-TWR |
| **Power Consumption** | Lower | Higher | SS-TWR |
| **Security (STS)** | Limited processing time | Full encryption | DS-TWR ✅ |
| **Complexity** | Simple | Moderate | SS-TWR |

**Project Requirements:**
- **Accuracy**: <10 cm for shelf-level positioning → **Requires DS-TWR**
- **Security**: Prevent spoofing/relay attacks → **Requires DS-TWR with STS**
- **Update Rate**: 5 Hz sufficient for walking speed (1-2 m/s) → **DS-TWR acceptable**
- **Battery Life**: Wearable runtime 2-4 hours → **DS-TWR acceptable with optimization**

**Conclusion**: **DS-TWR Deferred** provides the best balance of accuracy, security, and reliability for indoor inventory tracking.

---

## Multi-Anchor Configuration

### FiRa ONE_TO_MANY Mode

**Network Topology:**
```
Controller/Initiator:  1 × Tag (Mobile, MAC: 0x0000)
Controllees/Responders: 4 × Anchors (Fixed, MACs: 0x0001-0x0004)
```

**Ranging Cycle (200ms Block Duration):**
```
Time Slot Allocation:
┌─────────────────────────────────────────────────────────┐
│  Block Duration: 200 ms (5 Hz update rate)              │
├───────┬───────┬───────┬───────┬──────────────────────┤
│  Poll │  Resp │  Poll │  Resp │       ...            │
│  #1   │  #1   │  #2   │  #2   │  (slots 1-25)        │
├───────┴───────┴───────┴───────┴──────────────────────┤
│  Anchor 1    │  Anchor 2    │  Anchor 3  │ Anchor 4 │
│  (8ms/slot)  │  (8ms/slot)  │  (8ms/slot)│(8ms/slot)│
└─────────────────────────────────────────────────────────┘
```

**Slot Parameters:**
- **Slot Duration**: 2400 RSTU (Ranging Time Slot Units) ≈ 8 ms
- **Slots per Round**: 25 (allows time for 4 anchors + overhead)
- **Block Duration**: 200 ms total (25 slots × 8 ms = 200 ms)

### Configuration Commands

**Tag (Controller) Setup:**
```bash
screen /dev/cu.usbmodem* 115200

# Configure ONE_TO_MANY ranging
INITF -MULTI -ADDR=0 -PADDR=[1,2,3,4] -CHAN=9 -BLOCK=200 -RRU=DSTWR -ID=42
       ^^^^^^         ^^^^^^^^^^^^^^^^
       Enable         List of anchor
       multi-node     addresses

# Redirect output to hardware UART pins for ESP32
UART 1

# Save configuration and set auto-start
SETAPP INITF
SAVE

# Verify configuration
STAT
```

**Anchor (Responder) Setup:**
```bash
# Anchor 1 (repeat for anchors 2, 3, 4 with ADDR=2,3,4)
screen /dev/cu.usbmodem* 115200

RESPF -MULTI -ADDR=1 -PADDR=0 -CHAN=9 -BLOCK=200 -RRU=DSTWR -ID=42
             ^^^^^^^^ ^^^^^^^^
             This anchor  Controller
             is 0x0001    is 0x0000

SETAPP RESPF
SAVE
START
```

**Critical Parameters:**
- **Session ID (-ID=42)**: **Must match** on all devices in the network
- **Channel (-CHAN=9)**: 6.5-8 GHz band, better indoor penetration than Channel 5
- **Block Duration (-BLOCK=200)**: Time for complete ranging cycle (adjustable)

### Parameter Explanation

| Parameter | Tag Value | Anchor Value | Description |
|-----------|-----------|--------------|-------------|
| `-MULTI` | Required | Required | Enable ONE_TO_MANY mode |
| `-ADDR` | 0x0000 | 0x0001-0x0004 | Device MAC address |
| `-PADDR` | [1,2,3,4] | 0 | Partner address(es) |
| `-CHAN` | 9 | 9 | UWB channel (5 or 9) |
| `-BLOCK` | 200 | 200 | Block duration (ms) |
| `-RRU` | DSTWR | DSTWR | Ranging Round Usage |
| `-ID` | 42 | 42 | Session ID (must match) |

**Verification Output:**
```
FiRa Session Parameters: {
SESSION_ID: 42,
CHANNEL_NUMBER: 9,
DEVICE_ROLE: INITIATOR,
RANGING_ROUND_USAGE: DS_TWR_DEFERRED,
SLOT_DURATION [rstu]: 2400,
RANGING_DURATION [ms]: 200,
SLOTS_PER_RR: 25,
MULTI_NODE_MODE: ONE_TO_MANY,         ← Confirms multi-anchor
HOPPING_MODE: Disabled,
RFRAME_CONFIG: SP3,
SFD_ID: 2,
PREAMBLE_CODE_INDEX: 10,
STATIC_STS_IV: "01:02:03:04:05:06",   ← STS encryption enabled
VENDOR_ID: "07:08",
DEVICE_MAC_ADDRESS: 0x0000,
DST_MAC_ADDRESS[0]: 0x0001,           ← Anchor list
DST_MAC_ADDRESS[1]: 0x0002,
DST_MAC_ADDRESS[2]: 0x0003,
DST_MAC_ADDRESS[3]: 0x0004
}
OK
```

---

## Data Format and Parsing

### Raw UART Output from DWM3001CDK

**Example Multi-Line Message:**
```
SESSION_INFO_NTF: {session_handle=1, sequence_number=148, block_index=148, n_measurements=4
 [mac_address=0x0001, status="SUCCESS", distance[cm]=245];
 [mac_address=0x0002, status="SUCCESS", distance[cm]=312];
 [mac_address=0x0003, status="SUCCESS", distance[cm]=189];
 [mac_address=0x0004, status="SUCCESS", distance[cm]=403]}
```

**Message Structure:**
- **Multi-line format**: Start delimiter `SESSION_INFO_NTF:`, end delimiter `}`
- **Metadata**: Session handle, sequence number, block index, measurement count
- **Per-Anchor Data**: MAC address, ranging status, distance in centimeters

### ESP32-S3 Parser Implementation

**State Machine Logic:**
```cpp
// Simple Arduino-style parser (from esp32_dwm3001_cli.ino)
void loop() {
  while (DWM_Serial.available()) {
    char c = DWM_Serial.read();
    
    if (c == '\n' || c == '\r') {
      if (rxBuffer.length() > 0) {
        processLine(rxBuffer);
        rxBuffer = "";
      }
    } else {
      rxBuffer += c;
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
  
  // If in session, accumulate lines
  if (inSession) {
    sessionBuffer += " " + line + "\n";
    
    // Detect end (closing brace)
    if (line.indexOf("}") != -1) {
      inSession = false;
      printSessionJSON();  // Parse complete message
      sessionBuffer = "";
    }
  }
}
```

**Key Features:**
- **Multi-line buffering**: Accumulates full message before parsing
- **Overflow protection**: 2048-byte buffer limit
- **Simple string matching**: No complex regex required
- **Robust error handling**: Incomplete messages discarded

### JSON Output Format

**Parsed and Timestamped Data:**
```json
{
  "timestamp": 148235,
  "session_count": 148,
  "session_handle": 1,
  "sequence_number": 148,
  "block_index": 148,
  "n_measurements": 4,
  "measurements": [
    {"mac_address": "0x0001", "status": "SUCCESS", "distance_cm": 245},
    {"mac_address": "0x0002", "status": "SUCCESS", "distance_cm": 312},
    {"mac_address": "0x0003", "status": "SUCCESS", "distance_cm": 189},
    {"mac_address": "0x0004", "status": "SUCCESS", "distance_cm": 403}
  ]
}
```

**Advantages:**
- ✅ Standard JSON format for WiFi transmission (MQTT/HTTP)
- ✅ ESP32 `millis()` timestamp added
- ✅ Ready for server-side trilateration processing
- ✅ Human-readable for debugging

---

## System Limitations & Scalability

### Current Prototype: 4-Anchor Configuration

**Working System:**
- ✅ 1 tag + 4 anchors ranging simultaneously
- ✅ 5 Hz update rate (200ms block duration)
- ✅ DS-TWR with STS encryption for security
- ✅ <10 cm accuracy validated
- ✅ All devices battery-powered with auto-start

**Performance Metrics:**
```
Update Rate:     5 Hz (200 ms blocks)
Latency:         <20 ms (UART + parsing)
Throughput:      ~500 bytes/sec
Accuracy:        <10 cm (DS-TWR)
Range:           Up to 50 m line-of-sight
Battery Life:    4+ hours (wearable), weeks (anchors in sleep mode)
```

### Maximum: 8-Anchor Configuration (FiRa Protocol Limit)

**Why 8 Anchors Maximum?**

#### 1. FiRa TWR Protocol Constraint
```c
// From Qorvo SDK source code (firmware/Common/fira_config.h)
#define FIRA_RESPONDERS_MAX 8

// Protocol limitation: 8-bit encoding for TWR mode
// IEEE 802.15.4z frame has 127-byte payload limit
// Each responder requires ~15 bytes (MAC, STS, timestamps)
// Maximum responders: 127 / 15 ≈ 8 devices
```

#### 2. Security (STS) Processing
**STS (Scrambled Timestamp Sequence)** prevents replay attacks by encrypting ranging timestamps.

**Per-Device Processing:**
- AES-128 encryption/decryption: ~1-2 ms per anchor
- With 8 anchors: 8-16 ms encryption overhead
- Block duration must accommodate: ranging + encryption + radio turnaround

**Timing Budget (200ms block):**
```
DS-TWR messages:    3 messages × 8 anchors × 2 ms/msg  = 48 ms
STS encryption:     8 anchors × 2 ms/anchor             = 16 ms
Radio turnaround:   8 anchors × 0.5 ms                  = 4 ms
Processing margin:  200 - (48+16+4)                     = 132 ms (buffer)
```

**If 16 anchors were attempted:**
```
DS-TWR messages:    3 × 16 × 2 ms  = 96 ms
STS encryption:     16 × 2 ms      = 32 ms
Radio turnaround:   16 × 0.5 ms    = 8 ms
Total required:     136 ms         > 200 ms (insufficient time)

To fit: Block duration = 300+ ms → Update rate drops to 3 Hz
```

#### 3. Accuracy Considerations

**More devices = More error accumulation:**
- Each anchor has ±5 cm ranging error
- Trilateration combines all measurements
- With 8 anchors: statistical averaging improves accuracy
- Beyond 8 anchors: diminishing returns, increased complexity

**Optimal Configuration:**
```
4-6 anchors: Best balance of accuracy, latency, and reliability
7-8 anchors: Maximum for high-precision or large spaces
>8 anchors:  Requires alternative protocol (UL-TDOA)
```

### Scaling to 7 Anchors (Current Prototype Design)

**Configuration Change:**
```bash
# Tag: Update anchor list
INITF -MULTI -ADDR=0 -PADDR=[1,2,3,4,5,6,7] -CHAN=9 -BLOCK=250 -RRU=DSTWR -ID=42
                                              Increase block ^^^
                                              to 250ms for 7 anchors

# Each anchor: Same config, just different ADDR
RESPF -MULTI -ADDR={1-7} -PADDR=0 -CHAN=9 -BLOCK=250 -RRU=DSTWR -ID=42
```

**Impact:**
- Update rate: 5 Hz → 4 Hz (250ms blocks)
- Latency: +50ms per ranging cycle
- Battery life: Slightly reduced (more TX time)
- Coverage area: Increased (more reference points)

**Recommendation**: Stay with **4 anchors** for prototype testing. Scale to **6-7 anchors** only if 3000m² store requires additional coverage.

---

## Future Production Considerations

### Alternative: UL-TDOA for Large-Scale Deployment

**Current System (DS-TWR):**
- ✅ High accuracy (<10 cm)
- ✅ Secure (STS encrypted)
- ✅ Low latency (5 Hz)
- ❌ **Limited to 8 anchors** (FiRa protocol constraint)

**Alternative: UL-TDOA (Uplink Time-Difference of Arrival):**

#### How UL-TDOA Works

```
Tag (Transmitter)          Anchors (Passive Receivers)
      │                          
      │                    Anchor 1 (T1)
      │──── Blink ─────┬─► Anchor 2 (T2)
      │                └─► Anchor 3 (T3)
                          Anchor 4 (T4)
                               │
                               ▼
                       Central Server
                    (TDOA calculation)
                    
Position = Trilaterate using (T2-T1), (T3-T1), (T4-T1)
```

**Protocol Characteristics:**
- Tag **broadcasts** UWB "blink" messages
- **All anchors receive passively** (no response)
- Anchors forward timestamps to central server via WiFi/Ethernet
- Server calculates position using time differences

#### UL-TDOA vs. DS-TWR Comparison

| Feature | DS-TWR (Current) | UL-TDOA (Production Option) |
|---------|------------------|------------------------------|
| **Accuracy** | ±5-10 cm | ±20-30 cm (clock sync dependent) |
| **Max Anchors** | 8 (protocol limit) | **Unlimited** (passive receivers) |
| **Security** | STS encrypted (peer-to-peer) | Lower (one-way transmission) |
| **Latency** | 200 ms (5 Hz) | 100-500 ms (depends on network) |
| **Tag Complexity** | Medium (TWR protocol) | Low (simple blink) |
| **Anchor Power** | Low (battery weeks-months) | **Requires continuous power** (WiFi always on) |
| **Infrastructure** | Standalone anchors | **Central server required** |
| **Scalability** | 4-8 anchors | 30+ anchors feasible |
| **Clock Sync** | Not required | **Critical** (ns-level synchronization) |

#### When to Use UL-TDOA

**Production Deployment Scenarios:**
1. **Large facility (>3000 m²)**: Needs 15+ anchors for full coverage
2. **Wired power available**: Anchors can be PoE (Power-over-Ethernet)
3. **Central server infrastructure**: Already have WiFi mesh + backend
4. **Lower accuracy acceptable**: ±20-30 cm sufficient for aisle-level tracking

**UL-TDOA Architecture (Hypothetical Production):**
```
┌──────────────────────────────────────────────────┐
│                 3000 m² Store                    │
│                                                  │
│  [A1]─┐  [A2]─┐  [A3]─┐  ...  [A30]─┐          │
│       │       │       │              │          │
│       │       │       │              │          │
│      WiFi    WiFi    WiFi          WiFi         │
│       │       │       │              │          │
│       └───────┴───────┴──────────────┘          │
│                       │                          │
│                       ▼                          │
│              ┌─────────────────┐                 │
│              │  Central Server │                 │
│              │  - TDOA Solver  │                 │
│              │  - Position DB  │                 │
│              │  - WiFi AP      │                 │
│              └─────────────────┘                 │
└──────────────────────────────────────────────────┘
```

**Implementation Requirements:**
- **Anchor Hardware**: DWM3001CDK + ESP32/Raspberry Pi (WiFi module)
- **Clock Synchronization**: GPS or Ethernet PTP (Precision Time Protocol)
- **Backend Software**: Custom TDOA solver (hyperbolic trilateration)
- **Network**: Stable WiFi mesh with <10ms jitter

#### Why NOT UL-TDOA for Current Prototype

**Current Project Requirements:**
- Prototype validation with **minimal infrastructure**
- Battery-powered autonomous anchors (no wired power)
- High accuracy for shelf-level positioning
- Fast time-to-demo (2-3 months)

**UL-TDOA Challenges:**
- ❌ Requires central server + WiFi infrastructure
- ❌ Anchors need continuous power (battery life: hours, not weeks)
- ❌ Clock synchronization adds complexity (GPS modules, PTP setup)
- ❌ Lower accuracy (±20-30 cm) may not meet shelf-level requirements
- ❌ Development time: 2-3 months additional for TDOA solver

**Decision**: **Stick with DS-TWR** for prototype. Evaluate UL-TDOA only if:
1. Production deployment requires >8 anchors, AND
2. Wired power infrastructure is available, AND
3. ±20-30 cm accuracy is deemed sufficient

---

## Summary: Current Implementation Status

### ✅ What's Working (November 2024)

**Hardware:**
- 5× DWM3001CDK modules (4 anchors + 1 tag)
- 1× ESP32-S3 DevKit
- UART communication @ 115200 baud

**Firmware:**
- CLI firmware flashed to all devices
- FiRa ONE_TO_MANY mode configured
- DS-TWR deferred for accuracy + security
- NVM persistence + auto-start enabled

**Software:**
- ESP32 UART parser functional
- Multi-line message buffering working
- JSON output format ready for WiFi

**Performance:**
- 5 Hz update rate (200ms blocks)
- <10 cm ranging accuracy
- All 4 anchors responding simultaneously

### 🔄 In Progress

- WiFi integration (MQTT/HTTP client on ESP32)
- RFID module integration (separate UART)
- IMU sensor integration (I²C)
- Data fusion and position calculation

### ⏳ Future Considerations

- **Scaling to 6-7 anchors** (if coverage requires)
- **UL-TDOA evaluation** (only for >8 anchor production systems)
- **Power optimization** (duty-cycle modes for extended battery life)
- **Antenna placement optimization** (using RSSI/LOS analysis)

---

## References

**Qorvo Documentation:**
- DW3_QM33_SDK v1.1.1
- DWM3001CDK Developer Manual
- FiRa Protocol Specification (uwb-fira-protocol-R*.pdf)

**Project Documentation:**
- [UART_vs_SPI_DECISION.md](./UART_vs_SPI_DECISION.md) - Interface selection rationale
- [CLI_FIRMWARE_COMMAND_GUIDE.md](./CLI_FIRMWARE_COMMAND_GUIDE.md) - Complete command reference
- [DWM3001CDK_CLI_ONE_TO_MANY_SETUP.md](./DWM3001CDK_CLI_ONE_TO_MANY_SETUP.md) - Configuration guide
- [MULTI_ANCHOR_ARCHITECTURE.md](./MULTI_ANCHOR_ARCHITECTURE.md) - System architecture details

**Working Code:**
- `esp32_dwm3001_cli.ino` - ESP32 UART parser implementation

---

**Document Version**: 1.0  
**Last Updated**: November 8, 2024  
**Status**: Prototype Phase - Hardware Validated, Software Integration In Progress
