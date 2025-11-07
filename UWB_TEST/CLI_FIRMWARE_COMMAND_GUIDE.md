# DWM3001CDK CLI Firmware - Complete Command Guide

## Overview

The CLI firmware provides a text-based interface for configuring and testing UWB ranging on DWM3001CDK boards.

---

## Application Modes

### **INITF** - Initiator FiRa (Anchor/Controller)
- **Role**: Controller/Initiator (starts ranging sessions)
- **Use case**: Anchor in your multi-anchor setup
- **Command**: `INITF`
- **Behavior**: 
  - Initiates ranging with tags
  - Sends ranging requests
  - Receives responses from tags
  - Displays distance measurements

### **RESPF** - Responder FiRa (Tag/Controlee)
- **Role**: Controlee/Responder (responds to ranging)
- **Use case**: Tag that communicates with anchors
- **Command**: `RESPF`
- **Behavior**:
  - Waits for ranging requests
  - Responds to anchors
  - Displays distance to anchor(s)

### **LISTENER** - Passive Receive Mode
- **Role**: Passive listener (no transmission)
- **Use case**: Testing, sniffing UWB traffic, debugging
- **Command**: `LISTENER`
- **Behavior**:
  - **Only receives** UWB packets (does NOT transmit)
  - Displays received frames
  - Good for:
    - Checking if UWB signals are present
    - Debugging communication issues
    - Analyzing packet structure
    - Verifying channel activity
  - **NOT used for normal ranging**

**Configuration**: Use `LCFG` to configure listener parameters:
```
LCFG -CHAN=9 -PAC=8 -PCODE=10 -SFDTYPE=3 -DRATE=6810
```

---

## Command Reference

### 🔧 **Anytime Commands** (Work in any mode)

#### `HELP` or `?`
Display help information.
```
HELP              # Show all commands
HELP SAVE         # Show help for specific command
```

#### `STOP`
Stop the current application (INITF, RESPF, or LISTENER).
```
STOP
```

#### `STAT`
Display status information (device state, config, etc.).
```
STAT
```

#### `THREAD`
Display thread information (stack usage, heap).
```
THREAD
```

---

### 📡 **Application Selection** (IDLE mode only)

#### `INITF`
Start as Initiator (Anchor).

**Basic Usage:**
```
INITF
# Press Ctrl+C to stop, or type STOP in another terminal
```

**With Custom Parameters:**
```
INITF -ADDR=0x10 -CHAN=9 -BLOCK=200
```

**Important:** You can set unique MAC addresses per anchor!
- `-ADDR=0x10` sets this anchor's MAC address to 0x10
- Use different addresses for each anchor: 0x10, 0x11, 0x12, etc.

#### `RESPF`
Start as Responder (Tag).

**Basic Usage:**
```
RESPF
# Press Ctrl+C to stop, or type STOP in another terminal
```

**With Custom Parameters:**
```
RESPF -ADDR=0x20 -PADDR=0x10 -CHAN=9 -BLOCK=200
```

**Parameters:**
- `-ADDR=0x20` sets tag's own MAC address
- `-PADDR=0x10` sets partner address (which anchor to range with)
- **Note:** Tag only responds to ONE anchor (the PADDR)

#### `LISTENER`
Start passive listening mode.
```
LISTENER
# Press Ctrl+C to stop, or type STOP in another terminal
```

---

### ⚙️ **Service Commands** (Configuration)

#### `SAVE`
**Save current configuration and default app to NVM** (Non-Volatile Memory).
```
SAVE
```

**What it saves:**
- Default application (INITF, RESPF, or NONE)
- FiRa parameters (session ID, MAC addresses, etc.)
- System configuration

**After SAVE + power cycle:**
- Board will automatically start in saved mode
- Perfect for battery-powered operation

#### `SETAPP`
Set the default application to run on boot.
```
SETAPP INITF      # Auto-start as anchor
SETAPP RESPF      # Auto-start as tag
SETAPP LISTENER   # Auto-start as listener
SETAPP NONE       # Don't auto-start anything
SETAPP            # Show current default app
```

**Combine with parameters:**
```
SETAPP INITF -ADDR=0x10 -CHAN=9 -BLOCK=200
SAVE
# Now anchor will auto-start with MAC address 0x10 on Channel 9
```

**Example workflow for battery operation:**
```
SETAPP INITF -ADDR=0x10    # Set default to initiator with unique MAC
SAVE                       # Save to NVM
# Now unplug and power from battery - will auto-start as INITF with MAC 0x10
```

---

### 🔧 **Available Parameters for INITF/RESPF/SETAPP**

All these parameters work with `INITF`, `RESPF`, and `SETAPP` commands:

| Parameter | Description | Example | Default |
|-----------|-------------|---------|---------|
| `-ADDR=<hex>` | **Own MAC address** | `-ADDR=0x10` | 0x0 (anchor), 0x1 (tag) |
| `-PADDR=<hex>` | **Partner address** (RESPF only) | `-PADDR=0x10` | 0x0 |
| `-CHAN=<num>` | UWB channel (5 or 9) | `-CHAN=9` | 9 |
| `-SLOT=<num>` | Slot duration (RSTU units) | `-SLOT=2400` | 2400 |
| `-BLOCK=<num>` | Block duration (milliseconds) | `-BLOCK=200` | 200 |
| `-ROUND=<num>` | Round duration (slots, 1-255) | `-ROUND=25` | 25 |
| `-RRU=<mode>` | Ranging round usage | `-RRU=DSTWR` | DSTWR |
| `-PRFSET=<mode>` | PRF setting | `-PRFSET=BPRF4` | BPRF4 |

**Ranging Round Usage (RRU) Options:**
- `SSTWR` - Single-Sided TWR Deferred
- `DSTWR` - Double-Sided TWR Deferred (most accurate)
- `SSTWRNDEF` - Single-Sided TWR Non-Deferred
- `DSTWRNDEF` - Double-Sided TWR Non-Deferred

**PRF Set Options:**
- `BPRF3` - SP1, SFD 2
- `BPRF4` - SP3, SFD 2 (default)
- `BPRF5` - SP1, SFD 0
- `BPRF6` - SP3, SFD 0

**Multi-Anchor Example:**
```bash
# Anchor 1
SETAPP INITF -ADDR=0x10 -CHAN=9 -BLOCK=200 -RRU=DSTWR
SAVE

# Anchor 2  
SETAPP INITF -ADDR=0x11 -CHAN=9 -BLOCK=200 -RRU=DSTWR
SAVE

# Anchor 3
SETAPP INITF -ADDR=0x12 -CHAN=9 -BLOCK=200 -RRU=DSTWR
SAVE

# Tag (can only range with ONE anchor at a time)
SETAPP RESPF -ADDR=0x20 -PADDR=0x10 -CHAN=9 -BLOCK=200 -RRU=DSTWR
SAVE
```

---

#### `RESTORE`
Restore default configuration (factory reset).
```
RESTORE
```

#### `DIAG`
Enable/disable diagnostic mode for detailed ranging info.
```
DIAG 1            # Enable diagnostics
DIAG 0            # Disable diagnostics
```

#### `DECAID`
Display UWB chip information.
```
DECAID
```

**Output example:**
```
Device ID: DW3110
Device Version: X.X
Lot ID: XXXXX
```

#### `GETOTP`
Get OTP (One-Time Programmable) memory values.
```
GETOTP
```

---

### 🎯 **IDLE Time Commands** (Only when not ranging)

#### `UART`
UART configuration (if supported).
```
UART
```

#### `CALKEY`
Show available calibration keys.
```
CALKEY
```

**Output**: Lists all calibration parameters that can be read/written.

#### `LISTCAL`
List current calibration values.
```
LISTCAL
```

**Output example:**
```
ant0.transceiver: 0x01
ant0.tx.ch5.power: 0xXXXXXXXX
ant0.tx.ch9.power: 0xXXXXXXXX
ant0.rx.ch5.delay: 0xXXXX
ant0.rx.ch9.delay: 0xXXXX
xtal_trim: 0xXX
```

---

### 📻 **LISTENER Options**

#### `LCFG`
Configure LISTENER mode parameters.
```
LCFG [options]
```

**Available options:**
- `-CHAN=9` - Channel (5 or 9)
- `-PAC=8` - Preamble Acquisition Chunk (4, 8, 16, 32)
- `-PCODE=10` - Preamble Code (9-12)
- `-SFDTYPE=3` - Start Frame Delimiter (0-3)
- `-DRATE=6810` - Data Rate in kbps (850 or 6810)
- `-PHRMODE=0` - PHR Mode (0 or 1)
- `-PHRRATE=0` - PHR Data Rate (0 or 1)
- `-STSMODE=0` - STS Mode (0-3, 8)
- `-STSLEN=0` - STS Length (32-2048)
- `-PDOAMODE=1` - PDoA Mode (0, 1, 3)
- `-XTALTRIM=46` - Crystal trim (0-63)

**Example:**
```
LCFG -CHAN=9 -PCODE=10 -DRATE=6810
```

#### `LSTAT`
Display LISTENER statistics.
```
LSTAT
```

**Output**: Shows received packet statistics in LISTENER mode.

---

## Typical Usage Workflows

### 1️⃣ **Quick Test (One-time ranging)**

**Anchor (Board 1):**
```
INITF
# Watch for ranging output
```

**Tag (Board 2):**
```
RESPF
# Watch for distance measurements
```

### 2️⃣ **Configure for Battery Operation**

**Anchor:**
```
SETAPP INITF      # Set default app
SAVE              # Save to NVM
# Unplug and connect to battery - auto-starts as INITF
```

**Tag (if also battery-powered):**
```
SETAPP RESPF
SAVE
# Auto-starts as RESPF on battery
```

### 3️⃣ **Debug UWB Communication**

**Listener Board:**
```
LCFG -CHAN=9      # Set to same channel as your devices
LISTENER          # Start listening
# Should see UWB packets if communication is happening
```

### 4️⃣ **Check Calibration**

```
LISTCAL           # Show current calibration
CALKEY            # Show available calibration keys
```

### 5️⃣ **Factory Reset**

```
RESTORE           # Reset to defaults
SETAPP NONE       # Clear default app
SAVE              # Save clean state
```

---

## Important Notes

### ⚠️ **Current Limitation: One-to-One Only**

The **default CLI firmware** is configured for:
- **1 Anchor ↔ 1 Tag**
- `FIRA_DEFAULT_NUM_OF_CONTROLEES = 1`

**For your 4 anchors + 1 tag setup:**
- You need to **rebuild the firmware** with modified parameters
- See `BUILD_MULTI_ANCHOR_CLI_FIRMWARE.md` for instructions

### 💾 **SAVE Command**

**CRITICAL**: Always use `SAVE` after configuration changes you want to persist!
- `SETAPP INITF` alone is temporary
- `SETAPP INITF` + `SAVE` is permanent

### 🔋 **Battery Operation**

For standalone battery operation:
1. Configure board via USB
2. Use `SETAPP` to set mode
3. Use `SAVE` to write to NVM
4. Disconnect USB
5. Connect battery → Auto-starts in saved mode

### 📶 **Ranging Parameters**

**Cannot be changed via CLI** (hardcoded):
- Session ID
- MAC addresses
- Channel (for INITF/RESPF)
- Ranging interval
- Multi-node settings

**To change these**: Rebuild firmware with different defaults.

---

## Quick Reference Card

| Command | What it does | When to use |
|---------|-------------|-------------|
| `INITF` | Start as anchor | Testing anchor |
| `RESPF` | Start as tag | Testing tag |
| `LISTENER` | Passive receive | Debugging |
| `STOP` | Stop ranging | Exit application |
| `SETAPP INITF` | Set default to anchor | Before SAVE |
| `SAVE` | Write config to NVM | Make persistent |
| `RESTORE` | Factory reset | Start fresh |
| `STAT` | Show status | Check config |
| `LISTCAL` | Show calibration | Check antenna delay |
| `DIAG 1` | Enable debug info | Troubleshooting |

---

## Example Session: Configure Anchor for Battery

```
# Connect anchor via USB, open serial terminal

DWM3001CDK - DW3_QM33_SDK - FreeRTOS
ok

STAT                    # Check current state
LISTCAL                 # Check calibration
SETAPP INITF            # Set mode to initiator
SAVE                    # Save to NVM
INITF                   # Test it now
# See ranging output...
STOP                    # Stop test
# Unplug USB, connect battery
# Board now auto-starts as INITF!
```

---

## When LISTENER Mode is Useful

1. **Verifying UWB Activity**
   - Check if ranging is happening
   - Confirm channel is active

2. **Range Testing**
   - Place listener between anchor and tag
   - Verify signal strength at distance

3. **Packet Analysis**
   - See frame structure
   - Check for errors/retries

4. **Troubleshooting**
   - "Is anything transmitting?"
   - "Am I on the right channel?"

**Note**: LISTENER does NOT participate in ranging - it just watches!

---

## Next Steps

For **multi-anchor setup (4 anchors + 1 tag)**:
- See `BUILD_MULTI_ANCHOR_CLI_FIRMWARE.md`
- Need to modify firmware source and rebuild
- Or use UCI firmware with ESP32 control

For **calibration and accuracy**:
- Use `LISTCAL` to check antenna delays
- Adjust if distance measurements are consistently off
- See calibration guide for details
