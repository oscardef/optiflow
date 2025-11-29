"""
Simulation Service
==================
Manages simulation process lifecycle, configuration, and monitoring.
Handles subprocess management, output redirection, and status tracking.
"""
import subprocess
import signal
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from .base import BaseService
from ..config import config_state, ConfigMode
from ..core import logger


class SimulationService(BaseService):
    """
    Service for managing simulation processes.
    
    Handles:
    - Starting and stopping simulation processes
    - Process lifecycle management
    - Output redirection and log management
    - Status monitoring
    """
    
    def __init__(self, db: Session):
        """Initialize simulation service."""
        super().__init__(db)
        self._process: Optional[subprocess.Popen] = None
        self._output_file: Optional[Path] = None
    
    def start_simulation(
        self,
        mode: str = "REALISTIC",
        speed_multiplier: float = 1.0,
        disappearance_rate: float = 0.015,
        api_url: str = "http://localhost:8000"
    ) -> Dict[str, Any]:
        """
        Start a new simulation process.
        
        Args:
            mode: Simulation mode (DEMO/REALISTIC/STRESS)
            speed_multiplier: Speed multiplier (0.5-5.0)
            disappearance_rate: Item disappearance rate (0.0-0.1)
            api_url: Backend API URL
            
        Returns:
            Dict with success status, message, and process details
            
        Raises:
            ValueError: If invalid parameters or mode
            RuntimeError: If simulation is already running or cannot be started
        """
        self._log_operation("start_simulation", {
            "mode": mode,
            "speed": speed_multiplier,
            "disappearance_rate": disappearance_rate
        })
        
        # Validate system mode
        if config_state.mode != ConfigMode.SIMULATION:
            raise ValueError(
                "Cannot start simulation in REAL mode. Switch to SIMULATION mode first."
            )
        
        # Check if already running
        if self.is_running():
            raise RuntimeError(
                f"Simulation already running (PID: {self._process.pid})"
            )
        
        # Validate parameters
        self._validate_parameters(mode, speed_multiplier, disappearance_rate)
        
        # Find simulation directory
        simulation_dir = self._locate_simulation_directory()
        
        # Build command
        cmd = self._build_command(
            mode=mode,
            speed_multiplier=speed_multiplier,
            disappearance_rate=disappearance_rate,
            api_url=api_url
        )
        
        # Setup output redirection
        self._output_file = simulation_dir.parent / "sim_output.txt"
        self._prepare_output_file()
        
        try:
            # Start process
            self._process = subprocess.Popen(
                cmd,
                cwd=str(simulation_dir.parent),
                stdout=open(self._output_file, "a"),
                stderr=subprocess.STDOUT,
                text=True
            )
            
            # Update state
            config_state.simulation_running = True
            config_state.simulation_pid = self._process.pid
            
            self._log_operation("simulation_started", {
                "pid": self._process.pid,
                "command": " ".join(cmd)
            })
            
            return {
                "success": True,
                "message": "Simulation started successfully",
                "pid": self._process.pid,
                "mode": mode,
                "speed_multiplier": speed_multiplier,
                "disappearance_rate": disappearance_rate
            }
            
        except Exception as e:
            self._log_error("start_simulation", e)
            self._cleanup_failed_start()
            raise RuntimeError(f"Failed to start simulation: {str(e)}") from e
    
    def stop_simulation(self, timeout: int = 5) -> Dict[str, Any]:
        """
        Stop the running simulation process.
        
        Args:
            timeout: Seconds to wait for graceful shutdown
            
        Returns:
            Dict with success status and message
            
        Raises:
            RuntimeError: If no simulation is running
        """
        self._log_operation("stop_simulation")
        
        if not self.is_running():
            raise RuntimeError("No simulation is currently running")
        
        try:
            # Try graceful termination
            self._process.terminate()
            
            try:
                self._process.wait(timeout=timeout)
                self._log_operation("simulation_terminated_gracefully", {
                    "pid": self._process.pid
                })
            except subprocess.TimeoutExpired:
                # Force kill if graceful failed
                self._process.kill()
                self._process.wait()
                self.logger.warning(
                    f"Simulation process {self._process.pid} force killed"
                )
            
            return {
                "success": True,
                "message": "Simulation stopped successfully"
            }
            
        except Exception as e:
            self._log_error("stop_simulation", e)
            raise RuntimeError(f"Failed to stop simulation: {str(e)}") from e
        
        finally:
            self._cleanup_process()
    
    def is_running(self) -> bool:
        """
        Check if simulation process is running.
        
        Returns:
            True if simulation is running, False otherwise
        """
        if self._process is None:
            return False
        
        # Check if process is still alive
        if self._process.poll() is not None:
            # Process died
            self._cleanup_process()
            return False
        
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current simulation status.
        
        Returns:
            Dict with running status, PID, and mode
        """
        is_running = self.is_running()
        
        return {
            "running": is_running,
            "pid": self._process.pid if is_running else None,
            "mode": config_state.mode.value,
            "output_file": str(self._output_file) if self._output_file else None
        }
    
    def get_logs(self, lines: int = 1000) -> str:
        """
        Get recent simulation logs.
        
        Args:
            lines: Number of lines to retrieve
            
        Returns:
            Log content as string
        """
        if not self._output_file or not self._output_file.exists():
            return ""
        
        try:
            with open(self._output_file, "r") as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:]
                return "".join(recent_lines)
        except Exception as e:
            self._log_error("get_logs", e)
            return f"Error reading logs: {str(e)}"
    
    def _validate_parameters(
        self,
        mode: str,
        speed_multiplier: float,
        disappearance_rate: float
    ):
        """Validate simulation parameters."""
        valid_modes = ["DEMO", "REALISTIC", "STRESS"]
        if mode.upper() not in valid_modes:
            raise ValueError(
                f"Invalid mode '{mode}'. Must be one of: {valid_modes}"
            )
        
        if not 0.5 <= speed_multiplier <= 5.0:
            raise ValueError(
                f"Speed multiplier must be between 0.5 and 5.0, got {speed_multiplier}"
            )
        
        if not 0.0 <= disappearance_rate <= 0.1:
            raise ValueError(
                f"Disappearance rate must be between 0.0 and 0.1, got {disappearance_rate}"
            )
    
    def _locate_simulation_directory(self) -> Path:
        """Find simulation directory."""
        # Try relative path from backend
        backend_dir = Path(__file__).parent.parent.parent.parent
        simulation_dir = backend_dir / "simulation"
        
        if simulation_dir.exists():
            return simulation_dir
        
        # Try container path
        simulation_dir = Path("/simulation")
        if simulation_dir.exists():
            return simulation_dir
        
        raise FileNotFoundError(
            f"Simulation directory not found. Checked: "
            f"{backend_dir / 'simulation'} and /simulation"
        )
    
    def _build_command(
        self,
        mode: str,
        speed_multiplier: float,
        disappearance_rate: float,
        api_url: str
    ) -> list:
        """Build simulation command with parameters."""
        cmd = [sys.executable, "-m", "simulation.main"]
        cmd.extend(["--mode", mode.lower()])
        cmd.extend(["--speed", str(speed_multiplier)])
        cmd.extend(["--disappearance", str(disappearance_rate)])
        cmd.extend(["--api", api_url])
        
        return cmd
    
    def _prepare_output_file(self):
        """Prepare output file for simulation logs."""
        with open(self._output_file, "w") as f:
            f.write(f"=== Simulation started at {datetime.now()} ===\n")
    
    def _cleanup_process(self):
        """Clean up process state."""
        self._process = None
        config_state.simulation_running = False
        config_state.simulation_pid = None
    
    def _cleanup_failed_start(self):
        """Clean up after failed start attempt."""
        if self._process and self._process.poll() is None:
            try:
                self._process.kill()
            except Exception:
                pass
        
        self._cleanup_process()
