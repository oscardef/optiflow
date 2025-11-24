"""
Shopper Movement Simulation
============================
Simulates tag movement through store with back-and-forth navigation.
"""

import time
import math
from typing import Tuple, List
from .config import SimulationConfig
from .inventory import Item


class ShopperSimulator:
    """Simulates a shopper (tag) moving through the store"""
    
    def __init__(self, config: SimulationConfig, items: List[Item]):
        self.config = config
        self.items = items
        
        # Starting position (top of Aisle 1)
        self.x = config.store.aisles[0]['x']
        self.y = config.store.aisles[0]['y_start']
        
        # Movement state
        self.current_aisle = 0
        self.direction = 'forward'  # 'forward' = 1->4, 'backward' = 4->1
        self.movement_phase = 'going_down'  # 'going_down', 'going_up', 'at_cross'
        self.target_x = self.x
        self.target_y = config.store.aisles[0]['y_end']
        
        # Navigation tracking
        self.first_pass_complete = False
        self.pass_count = 0
        self.aisles_visited = set()
    
    @property
    def speed(self) -> float:
        """Get current speed with multiplier"""
        return self.config.tag.speed * self.config.speed_multiplier
    
    def update_position(self, dt: float):
        """Update position based on time delta"""
        # Calculate distance to target
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        distance = math.sqrt(dx*dx + dy*dy)
        
        if distance < 5:  # Close enough to target
            self._reached_target()
            return
        
        # Move toward target
        move_distance = self.speed * dt
        if move_distance >= distance:
            self.x = self.target_x
            self.y = self.target_y
        else:
            ratio = move_distance / distance
            self.x += dx * ratio
            self.y += dy * ratio
    
    def _reached_target(self):
        """Handle reaching current target, set next target"""
        aisles = self.config.store.aisles
        
        if self.movement_phase == 'going_down':
            # Reached bottom of aisle
            self.aisles_visited.add(self.current_aisle)
            
            # Check if we can move to cross aisle
            if self.direction == 'forward' and self.current_aisle < len(aisles) - 1:
                # Go to cross aisle to move to next aisle
                self.movement_phase = 'at_cross'
                self.target_x = aisles[self.current_aisle + 1]['x']
                self.target_y = self.config.store.cross_aisle_y
            elif self.direction == 'backward' and self.current_aisle > 0:
                # Go to cross aisle to move to previous aisle
                self.movement_phase = 'at_cross'
                self.target_x = aisles[self.current_aisle - 1]['x']
                self.target_y = self.config.store.cross_aisle_y
            else:
                # Can't go further, reverse direction
                self._reverse_direction()
        
        elif self.movement_phase == 'going_up':
            # Reached top of aisle
            self.movement_phase = 'going_down'
            self.target_y = aisles[self.current_aisle]['y_end']
        
        elif self.movement_phase == 'at_cross':
            # Reached next aisle via cross aisle
            if self.direction == 'forward':
                self.current_aisle += 1
            else:
                self.current_aisle -= 1
            
            # Go up the new aisle
            self.movement_phase = 'going_up'
            self.target_y = aisles[self.current_aisle]['y_start']
    
    def _reverse_direction(self):
        """Reverse direction when reaching end of store"""
        # Complete a pass
        if not self.first_pass_complete:
            self.first_pass_complete = True
            print(f"✅ First pass complete! Items can now go missing randomly")
            self._check_for_missing_items()
        else:
            self._check_for_missing_items()
        
        self.pass_count += 1
        self.aisles_visited.clear()
        
        # Switch direction
        if self.direction == 'forward':
            self.direction = 'backward'
            print(f"\n🔄 Pass {self.pass_count} complete - Reversing direction (← Backward)")
        else:
            self.direction = 'forward'
            print(f"\n🔄 Pass {self.pass_count} complete - Reversing direction (→ Forward)")
        
        # Start going up current aisle
        self.movement_phase = 'going_up'
        aisles = self.config.store.aisles
        self.target_y = aisles[self.current_aisle]['y_start']
    
    def _check_for_missing_items(self):
        """Randomly mark some items as missing (1-2% per pass)"""
        if not self.first_pass_complete:
            return
        
        detected_items = [item for item in self.items if item.detected and not item.missing]
        if not detected_items:
            return
        
        import random
        num_to_mark = int(len(detected_items) * random.uniform(0.01, 0.02))
        
        if num_to_mark > 0:
            import random
            items_to_mark = random.sample(detected_items, min(num_to_mark, len(detected_items)))
            
            for item in items_to_mark:
                item.missing = True
                item.detected = False
                print(f"⚠️  Item went missing: {item.product.name} ({item.rfid_tag})")
    
    def get_position(self) -> Tuple[float, float]:
        """Get current position"""
        return (self.x, self.y)
    
    def get_status_info(self) -> dict:
        """Get current status for display"""
        aisles = self.config.store.aisles
        
        aisle_info = f"Aisle {self.current_aisle + 1}" if self.current_aisle < len(aisles) else "Transit"
        
        if self.movement_phase == 'going_down':
            direction_info = "↓ Down"
        elif self.movement_phase == 'going_up':
            direction_info = "↑ Up"
        else:
            direction_info = "→ Cross"
        
        dir_arrow = "→" if self.direction == 'forward' else "←"
        
        return {
            "pass": self.pass_count + 1,
            "direction_arrow": dir_arrow,
            "aisle": aisle_info,
            "movement": direction_info,
            "position": (self.x, self.y)
        }
