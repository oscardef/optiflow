# Network and MQTT Configuration Guide

## Overview
OptiFlow simulation requires MQTT broker connectivity to send sensor data. The system includes automatic connection checking, retry logic, and automatic reconnection if the network changes.

## Configuration

### MQTT Broker Setup

The MQTT broker address is configurable via environment variables. By default, it uses `172.20.10.3` (typical iPhone hotspot gateway address).

**To configure:**
1. Copy `.env.example` to `.env` in the project root
2. Set the MQTT broker address:
```bash
MQTT_BROKER=172.20.10.3  # Your MQTT broker IP
MQTT_PORT=1883            # MQTT broker port
```

## Important: Network Requirements

The MQTT broker IP address (e.g., `172.20.10.3`) is **only accessible when connected to a specific WiFi network** (like the "Oscar" iPhone hotspot). If you're not on the correct network, MQTT will fail to connect.

## How It Works

### Automatic Connection Retry

When you start the simulation:

1. **Pre-Start MQTT Check** (Admin Panel):
   - Tests connection to MQTT broker before starting
   - Shows current WiFi network for reference
   - Prevents starting if MQTT is unreachable
   - Displays helpful error messages

2. **Simulation MQTT Connection** (with retry):
   - Attempts to connect to MQTT broker (up to 5 retries)
   - Waits 2 seconds between retry attempts
   - Shows clear error if all attempts fail
   - Exits gracefully with helpful troubleshooting tips

3. **Automatic Reconnection**:
   - If connection drops during simulation, automatically tries to reconnect
   - Continues running while attempting reconnection
   - Shows status: "⚠️ MQTT disconnected. Waiting for reconnection..."
   - Notifies when reconnected: "✅ MQTT reconnected successfully!"

### Manual Connection Testing

Use the **"Test Connection"** button in the Admin Panel to check MQTT connectivity without starting the simulation.

The connection status panel shows:
- ✓/✗ MQTT Broker connection status with IP address
- Current WiFi network (informational only)
- Detailed error messages for troubleshooting
- Helpful tips when connection fails

## Platform Notes

### macOS
WiFi SSID detection works automatically using the built-in `airport` utility.

### Linux/Windows
WiFi checking is currently macOS-specific. On other platforms:
- Leave `REQUIRED_WIFI_SSID` empty to skip WiFi validation
- MQTT checking still works across all platforms

## Troubleshooting

### "Cannot connect to MQTT broker"
**Cause:** MQTT broker is not reachable at the configured IP address.

**Solutions:**
1. **Check WiFi connection**: Make sure you're connected to the correct network (e.g., "Oscar" hotspot)
2. **Verify MQTT broker is running**: `mosquitto -v`
3. **Check IP address**: For iPhone hotspot, go to Settings → Personal Hotspot to see the IP
   - Or use `ipconfig getifaddr en0` (macOS) to get your current IP
4. **Update .env file**: If IP changed, update `MQTT_BROKER` in `.env` and restart containers
5. **Firewall**: Ensure port 1883 is not blocked

### Simulation fails to start after switching networks
**Cause:** You were on a different network when you first tried to start, MQTT failed, and now it won't retry.

**Solution:**
1. Make sure you're connected to the correct WiFi network (e.g., "Oscar" hotspot)
2. Click "Test Connection" button to verify MQTT is reachable
3. Click "Start Simulation" again - it will now retry the connection
4. The simulation includes automatic retry logic (5 attempts) when starting

### Simulation loses connection during run
**Cause:** Network interruption or WiFi switch while simulation is running.

**Result:** Simulation will automatically attempt to reconnect (shows "⚠️ MQTT disconnected. Waiting for reconnection...")
- If you switched networks, the old MQTT broker IP won't be reachable
- You'll need to stop and restart the simulation on the new network

### Connection check hangs
- MQTT connection times out after 3 seconds
- Check network connectivity
- Verify broker address is correct

## Example Configuration

**For iPhone Hotspot "Oscar":**
```bash
# .env
MQTT_BROKER=172.20.10.3
MQTT_PORT=1883
REQUIRED_WIFI_SSID=Oscar
```

**For Local Development (no WiFi check):**
```bash
# .env
MQTT_BROKER=localhost
MQTT_PORT=1883
# REQUIRED_WIFI_SSID=
```

**For Production Server:**
```bash
# .env
MQTT_BROKER=192.168.1.100
MQTT_PORT=1883
# REQUIRED_WIFI_SSID=
```
