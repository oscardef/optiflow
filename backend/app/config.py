"""
Configuration management for OptiFlow
Handles mode switching and system state persistence
"""
from enum import Enum
from pathlib import Path
import json
import os

class ConfigMode(str, Enum):
    """Operating mode for the system"""
    SIMULATION = "SIMULATION"
    REAL = "REAL"

class ConfigState:
    """Manages persistent configuration state"""
    
    def __init__(self):
        self.state_file = Path("/tmp/optiflow_state.json")
        self._state = self._load_state()
    
    def _load_state(self) -> dict:
        """Load state from file or initialize defaults"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Default state
        return {
            "mode": ConfigMode.SIMULATION.value,
            "store_width": 1000,
            "store_height": 800,
            "simulation_running": False,
            "simulation_pid": None
        }
    
    def _save_state(self):
        """Persist state to file"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self._state, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save state: {e}")
    
    @property
    def mode(self) -> ConfigMode:
        """Get current operating mode"""
        return ConfigMode(self._state.get("mode", ConfigMode.SIMULATION.value))
    
    @mode.setter
    def mode(self, value: ConfigMode):
        """Set operating mode"""
        self._state["mode"] = value.value
        self._save_state()
    
    @property
    def store_width(self) -> int:
        """Get store width in cm"""
        return self._state.get("store_width", 1000)
    
    @store_width.setter
    def store_width(self, value: int):
        """Set store width in cm"""
        self._state["store_width"] = value
        self._save_state()
    
    @property
    def store_height(self) -> int:
        """Get store height in cm"""
        return self._state.get("store_height", 800)
    
    @store_height.setter
    def store_height(self, value: int):
        """Set store height in cm"""
        self._state["store_height"] = value
        self._save_state()
    
    @property
    def max_display_items(self) -> int:
        """Get max items to display on map"""
        return self._state.get("max_display_items", 500)
    
    @max_display_items.setter
    def max_display_items(self, value: int):
        """Set max items to display on map"""
        self._state["max_display_items"] = min(max(value, 100), 5000)  # Clamp between 100-5000
        self._save_state()
    
    @property
    def simulation_running(self) -> bool:
        """Check if simulation is running"""
        return self._state.get("simulation_running", False)
    
    @simulation_running.setter
    def simulation_running(self, value: bool):
        """Set simulation running state"""
        self._state["simulation_running"] = value
        self._save_state()
    
    @property
    def simulation_pid(self) -> int:
        """Get simulation process ID"""
        return self._state.get("simulation_pid")
    
    @simulation_pid.setter
    def simulation_pid(self, value: int):
        """Set simulation process ID"""
        self._state["simulation_pid"] = value
        self._save_state()

# Global configuration state
config_state = ConfigState()
