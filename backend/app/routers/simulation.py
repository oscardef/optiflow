"""Simulation control and management router"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import subprocess
import signal
import os
import sys
import socket
from pathlib import Path
from datetime import datetime

from ..config import config_state, ConfigMode
from ..core import logger

# Optional MQTT client for hardware control
try:
    import paho.mqtt.publish as mqtt_publish
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    logger.warning("paho-mqtt not available - hardware control will be disabled")

router = APIRouter(prefix="/simulation", tags=["simulation"])

# Store simulation process reference
_simulation_process: Optional[subprocess.Popen] = None

class SimulationStatus(BaseModel):
    running: bool
    pid: Optional[int] = None
    mode: str
    uptime_seconds: Optional[int] = None

class SimulationParams(BaseModel):
    speed_multiplier: Optional[float] = 1.0
    mode: Optional[str] = "DEMO"  # DEMO, REALISTIC, STRESS
    api_url: Optional[str] = None
    disappearance_interval: Optional[float] = 10.0  # seconds between items going missing

class ConnectionStatus(BaseModel):
    mqtt_connected: bool
    mqtt_broker: str
    mqtt_error: Optional[str] = None
    wifi_ssid: Optional[str] = None
    required_wifi_ssid: Optional[str] = None
    wifi_connected: bool
    wifi_warning: Optional[str] = None

def check_mqtt_connection(broker: str, port: int, timeout: int = 3) -> tuple[bool, Optional[str]]:
    """Check if MQTT broker is reachable"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((broker, port))
        sock.close()
        if result == 0:
            return True, None
        else:
            return False, f"Cannot connect to MQTT broker at {broker}:{port}"
    except socket.gaierror:
        return False, f"Cannot resolve MQTT broker hostname: {broker}"
    except Exception as e:
        return False, f"MQTT connection error: {str(e)}"

def get_wifi_ssid() -> Optional[str]:
    """Get current WiFi SSID (macOS specific)"""
    try:
        result = subprocess.run(
            ["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", "-I"],
            capture_output=True,
            text=True,
            timeout=2
        )
        for line in result.stdout.split('\n'):
            if ' SSID:' in line:
                return line.split('SSID:')[1].strip()
    except Exception as e:
        logger.warning(f"Could not get WiFi SSID: {e}")
    return None

@router.get("/connection-status", response_model=ConnectionStatus)
def get_connection_status():
    """Check MQTT connectivity status"""
    # Get MQTT broker from config
    mqtt_broker = os.environ["MQTT_BROKER"]
    mqtt_port = int(os.environ["MQTT_PORT"])
    
    # Check MQTT connection
    mqtt_connected, mqtt_error = check_mqtt_connection(mqtt_broker, mqtt_port)
    
    # Optionally get WiFi info for informational purposes
    current_ssid = get_wifi_ssid()
    
    return {
        "mqtt_connected": mqtt_connected,
        "mqtt_broker": mqtt_broker,
        "mqtt_error": mqtt_error,
        "wifi_ssid": current_ssid,
        "required_wifi_ssid": None,
        "wifi_connected": True,  # Don't block based on WiFi
        "wifi_warning": None
    }

def stop_simulation_process():
    """Stop the running simulation process instantly"""
    global _simulation_process
    
    # Update state IMMEDIATELY to prevent race condition with status checks
    config_state.simulation_running = False
    pid = config_state.simulation_pid
    config_state.simulation_pid = None
    
    if _simulation_process and _simulation_process.poll() is None:
        try:
            # Use SIGKILL for instant termination (no cleanup needed)
            _simulation_process.kill()
            _simulation_process.wait(timeout=1)  # Should be instant
            logger.info(f"Killed simulation process PID {_simulation_process.pid}")
        except Exception as e:
            logger.error(f"Error stopping simulation: {e}")
        finally:
            _simulation_process = None
    elif pid:
        # Try to kill by PID from state
        try:
            os.kill(pid, signal.SIGKILL)  # Instant kill
            logger.info(f"Killed simulation process PID {pid}")
        except ProcessLookupError:
            logger.warning(f"Process {pid} not found")
        except Exception as e:
            logger.error(f"Error killing process: {e}")

@router.get("/status", response_model=SimulationStatus)
def get_simulation_status():
    """Get current simulation status"""
    global _simulation_process
    
    # Check if process is actually running
    if _simulation_process and _simulation_process.poll() is not None:
        # Process died
        _simulation_process = None
        config_state.simulation_running = False
        config_state.simulation_pid = None
    
    return {
        "running": config_state.simulation_running,
        "pid": config_state.simulation_pid,
        "mode": config_state.mode.value,
        "uptime_seconds": None  # TODO: track start time
    }

@router.post("/start")
def start_simulation(params: Optional[SimulationParams] = None):
    """
    Start the simulation process
    Only works when in SIMULATION mode
    """
    global _simulation_process
    
    # Check if we're in simulation mode
    if config_state.mode != ConfigMode.SIMULATION:
        raise HTTPException(
            status_code=400,
            detail="Cannot start simulation in PRODUCTION mode. Switch to SIMULATION mode first."
        )
    
    # Check if already running
    if config_state.simulation_running and _simulation_process and _simulation_process.poll() is None:
        return {
            "success": False,
            "message": "Simulation already running",
            "pid": _simulation_process.pid
        }
    
    # Find simulation directory
    # In Docker: backend is at /app, simulation should be at /simulation (mounted separately)
    # In development: backend is at workspace/backend, simulation at workspace/simulation
    
    backend_dir = Path(__file__).parent.parent.parent.parent
    simulation_dir = backend_dir / "simulation"
    
    if not simulation_dir.exists():
        # Try container path
        simulation_dir = Path("/simulation")
        if not simulation_dir.exists():
            raise HTTPException(
                status_code=500,
                detail=f"Simulation directory not found. Checked: {backend_dir / 'simulation'} and /simulation"
            )
    
    # Build command - run as module to support relative imports
    # Use -u for unbuffered output so logs appear in real time
    cmd = [sys.executable, "-u", "-m", "simulation.main"]
    
    # Add parameters
    if params:
        if params.speed_multiplier:
            cmd.extend(["--speed", str(params.speed_multiplier)])
        if params.mode:
            cmd.extend(["--mode", params.mode.lower()])
        if params.api_url:
            cmd.extend(["--api", params.api_url])
        if params.disappearance_interval is not None:
            cmd.extend(["--disappearance", str(params.disappearance_interval)])
    
    # If no API URL specified, use localhost:8000 (works both in dev and container)
    if not params or not params.api_url:
        cmd.extend(["--api", "http://localhost:8000"])
    
    try:
        # Start simulation as subprocess
        # Set cwd to parent of simulation dir so Python can import it as a module
        # Redirect output to file to prevent buffer overflow
        output_file = simulation_dir.parent / "sim_output.txt"
        with open(output_file, "w") as f:
            f.write(f"=== Simulation started at {datetime.now()} ===\n")
        
        # Set up environment with PYTHONPATH including the simulation parent directory
        env = os.environ.copy()
        pythonpath = str(simulation_dir.parent)
        if 'PYTHONPATH' in env:
            pythonpath = f"{pythonpath}:{env['PYTHONPATH']}"
        env['PYTHONPATH'] = pythonpath
        
        _simulation_process = subprocess.Popen(
            cmd,
            cwd=str(simulation_dir.parent),
            stdout=open(output_file, "a"),
            stderr=subprocess.STDOUT,  # Merge stderr into stdout
            text=True,
            env=env
        )
        
        config_state.simulation_running = True
        config_state.simulation_pid = _simulation_process.pid
        
        logger.info(f"Started simulation process PID {_simulation_process.pid}")
        
        return {
            "success": True,
            "message": "Simulation started successfully",
            "pid": _simulation_process.pid,
            "command": " ".join(cmd)
        }
    
    except Exception as e:
        logger.error(f"Failed to start simulation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start simulation: {str(e)}"
        )

@router.get("/logs")
def get_simulation_logs():
    """Get recent simulation output logs"""
    global _simulation_process
    
    if not _simulation_process:
        return {
            "stdout": "",
            "stderr": "No simulation process found",
            "running": False
        }
    
    # Check if process is still running
    poll = _simulation_process.poll()
    
    # Read from output file
    output = ""
    try:
        backend_dir = Path(__file__).parent.parent.parent.parent
        simulation_dir = backend_dir / "simulation"
        if not simulation_dir.exists():
            simulation_dir = Path("/simulation")
        
        output_file = simulation_dir.parent / "sim_output.txt"
        if output_file.exists():
            # Read last 1000 lines
            with open(output_file, "r") as f:
                lines = f.readlines()
                output = "".join(lines[-1000:])
    except Exception as e:
        output = f"Error reading logs: {e}"
    
    return {
        "stdout": output,
        "stderr": "",
        "running": poll is None,
        "exit_code": poll
    }

@router.post("/stop")
def stop_simulation():
    """Stop the running simulation"""
    if not config_state.simulation_running:
        return {
            "success": False,
            "message": "Simulation is not running"
        }
    
    stop_simulation_process()
    
    return {
        "success": True,
        "message": "Simulation stopped successfully"
    }

@router.put("/params")
def update_simulation_params(params: SimulationParams):
    """
    Update simulation parameters
    Note: Currently requires restart to take effect
    """
    # TODO: Implement hot-reload of parameters via IPC or config file
    return {
        "success": False,
        "message": "Parameter hot-reload not yet implemented. Stop and restart simulation with new parameters."
    }


class InventoryGenerationParams(BaseModel):
    item_count: int = 1000


@router.post("/generate-inventory")
def generate_inventory(params: InventoryGenerationParams):
    """
    Generate inventory items for simulation.
    This runs the inventory generation script as a subprocess.
    
    Args:
        item_count: Number of items to generate (50-5000)
    """
    if config_state.mode != ConfigMode.SIMULATION:
        raise HTTPException(
            status_code=400,
            detail="Inventory generation is only available in SIMULATION mode"
        )
    
    if config_state.simulation_running:
        raise HTTPException(
            status_code=400,
            detail="Cannot generate inventory while simulation is running. Stop simulation first."
        )
    
    # Clamp item count
    item_count = max(50, min(5000, params.item_count))
    
    # Find simulation directory
    backend_dir = Path(__file__).parent.parent.parent.parent
    simulation_dir = backend_dir / "simulation"
    
    if not simulation_dir.exists():
        simulation_dir = Path("/simulation")
        if not simulation_dir.exists():
            raise HTTPException(
                status_code=500,
                detail="Simulation directory not found"
            )
    
    # Run generate_inventory script
    cmd = [
        sys.executable, "-m", "simulation.generate_inventory",
        "--items", str(item_count),
        "--api", "http://localhost:8000"
    ]
    
    try:
        logger.info(f"Generating {item_count} inventory items...")
        
        # Set up environment with PYTHONPATH
        env = os.environ.copy()
        pythonpath = str(simulation_dir.parent)
        if 'PYTHONPATH' in env:
            pythonpath = f"{pythonpath}:{env['PYTHONPATH']}"
        env['PYTHONPATH'] = pythonpath
        
        result = subprocess.run(
            cmd,
            cwd=str(simulation_dir.parent),
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout
            env=env
        )
        
        if result.returncode != 0:
            logger.error(f"Inventory generation failed: {result.stderr}")
            raise HTTPException(
                status_code=500,
                detail=f"Inventory generation failed: {result.stderr[-500:] if result.stderr else 'Unknown error'}"
            )
        
        logger.info(f"Successfully generated {item_count} inventory items")
        
        return {
            "success": True,
            "message": f"Generated inventory with {item_count} items",
            "items_created": item_count,
            "output": result.stdout[-1000:] if result.stdout else ""
        }
    
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=500,
            detail="Inventory generation timed out"
        )
    except Exception as e:
        logger.error(f"Inventory generation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Inventory generation failed: {str(e)}"
        )


class HardwareControlRequest(BaseModel):
    command: str  # "START" or "STOP"


class HardwareControlResponse(BaseModel):
    success: bool
    message: str
    command_sent: str


@router.post("/hardware/control", response_model=HardwareControlResponse)
def control_hardware(request: HardwareControlRequest):
    """
    Send control commands to ESP32 hardware via MQTT.
    
    Commands:
    - START: Begin polling and publishing RFID/UWB data
    - STOP: Stop polling
    """
    if not MQTT_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="MQTT library not available. Install paho-mqtt to enable hardware control."
        )
    
    command = request.command.upper()
    if command not in ["START", "STOP"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid command. Use 'START' or 'STOP'."
        )
    
    mqtt_broker = os.environ["MQTT_BROKER"]
    mqtt_port = int(os.environ["MQTT_PORT"])
    topic = "store/control"
    
    try:
        mqtt_publish.single(
            topic,
            payload=command,
            hostname=mqtt_broker,
            port=mqtt_port,
            client_id="optiflow_backend_control"
        )
        
        logger.info(f"Sent {command} command to hardware via MQTT topic {topic}")
        
        return HardwareControlResponse(
            success=True,
            message=f"Successfully sent {command} command to hardware",
            command_sent=command
        )
    
    except Exception as e:
        logger.error(f"Failed to send hardware control command: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send command to hardware: {str(e)}"
        )