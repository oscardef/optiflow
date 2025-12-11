"""
Simulation Configuration
========================
Central configuration for simulation modes and parameters.
"""

import os
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple


class SimulationMode(Enum):
    """Simulation modes with different item densities"""
    DEMO = "demo"           # 100 items, 1-2 duplicates per SKU
    REALISTIC = "realistic"  # 500 items, 5-10 duplicates per SKU
    STRESS = "stress"        # 1000 items, 10-20 duplicates per SKU


@dataclass
class StoreLayout:
    """Store physical layout configuration"""
    width: int = 1000  # cm (10 meters)
    height: int = 800  # cm (8 meters)
    
    # Aisle configuration (vertical aisles) - wider aisles, almost touching
    aisles: List[dict] = None
    
    # Cross aisle (horizontal) - open walkway connecting aisles, no walls
    cross_aisle_y: int = 400
    cross_aisle_height: int = 120  # Wider central aisle
    cross_aisle_x_start: int = 180  # Center of first aisle
    cross_aisle_x_end: int = 825    # Center of last aisle
    
    def __post_init__(self):
        if self.aisles is None:
            # All aisles same length - single unified store shape, no border crossing
            # Aisles wider (180cm each) matching frontend visualization
            # Person walks very close to walls (±60cm from center), maximum RFID coverage
            self.aisles = [
                {'x': 180, 'y_start': 120, 'y_end': 700, 'width': 180},  # Aisle 1
                {'x': 395, 'y_start': 120, 'y_end': 700, 'width': 180},  # Aisle 2
                {'x': 610, 'y_start': 120, 'y_end': 700, 'width': 180},  # Aisle 3
                {'x': 825, 'y_start': 120, 'y_end': 700, 'width': 180},  # Aisle 4
            ]


@dataclass
class MQTTConfig:
    """MQTT broker configuration"""
    broker: str = os.environ.get("MQTT_BROKER")
    port: int = int(os.environ.get("MQTT_PORT"))
    topic_data: str = "store/simulation"  # Simulation-specific topic
    topic_status: str = "store/simulation/status"
    topic_control: str = "store/simulation/control"
    topic_restock: str = "store/simulation/restock"  # New topic for restock commands


@dataclass
class TagConfig:
    """Tag movement and detection configuration"""
    tag_id: str = "tag_0x42"
    speed: float = 100.0  # cm/s (slower for more realistic effect)
    rfid_detection_range: float = 100.0  # cm (1 meter - RFID detection range, must match backend)
    update_interval: float = 0.15  # seconds between updates


@dataclass
class SimulationConfig:
    """Complete simulation configuration"""
    mode: SimulationMode = SimulationMode.REALISTIC
    store: StoreLayout = None
    mqtt: MQTTConfig = None
    tag: TagConfig = None
    api_url: str = "http://localhost:8000"
    speed_multiplier: float = 1.0  # Speed adjustment (1.0 = normal, 2.0 = 2x speed)
    disappearance_interval: float = 10.0  # Seconds between items going missing (configurable via slider)
    
    def __post_init__(self):
        if self.store is None:
            self.store = StoreLayout()
        if self.mqtt is None:
            self.mqtt = MQTTConfig()
        if self.tag is None:
            self.tag = TagConfig()
    
    @property
    def target_item_count(self) -> int:
        """Get target item count based on mode"""
        if self.mode == SimulationMode.DEMO:
            return 100
        elif self.mode == SimulationMode.REALISTIC:
            return 1000  # Reduced for 5-10 items per SKU with expanded catalog
        elif self.mode == SimulationMode.STRESS:
            return 2000  # Reduced accordingly
        return 1000
    
    @property
    def duplicates_per_sku(self) -> Tuple[int, int]:
        """Get duplicate range (min, max) based on mode"""
        if self.mode == SimulationMode.DEMO:
            return (1, 2)
        elif self.mode == SimulationMode.REALISTIC:
            return (5, 10)
        elif self.mode == SimulationMode.STRESS:
            return (10, 20)
        return (5, 10)


# Default configuration instance
DEFAULT_CONFIG = SimulationConfig()
