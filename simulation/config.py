"""
Simulation Configuration
========================
Central configuration for simulation modes and parameters.
"""

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
    
    # Aisle configuration (vertical aisles)
    aisles: List[dict] = None
    
    # Cross aisle (horizontal)
    cross_aisle_y: int = 400
    cross_aisle_height: int = 80
    
    def __post_init__(self):
        if self.aisles is None:
            self.aisles = [
                {'x': 200, 'y_start': 150, 'y_end': 700, 'width': 80},  # Aisle 1
                {'x': 400, 'y_start': 120, 'y_end': 700, 'width': 80},  # Aisle 2
                {'x': 600, 'y_start': 120, 'y_end': 700, 'width': 80},  # Aisle 3
                {'x': 800, 'y_start': 120, 'y_end': 700, 'width': 80},  # Aisle 4
            ]


@dataclass
class MQTTConfig:
    """MQTT broker configuration"""
    broker: str = "172.20.10.3"
    port: int = 1883
    topic_data: str = "store/aisle1"
    topic_status: str = "store/status"
    topic_control: str = "store/control"
    topic_restock: str = "store/restock"  # New topic for restock commands


@dataclass
class TagConfig:
    """Tag movement and detection configuration"""
    tag_id: str = "tag_0x42"
    speed: float = 100.0  # cm/s (slower for more realistic effect)
    rfid_detection_range: float = 80.0  # cm (0.8 meters - more realistic RFID range)
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
    disappearance_rate: float = 0.015  # Rate at which items go missing (default: 1.5% per pass)
    
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
