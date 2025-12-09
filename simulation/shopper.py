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
        
        # Starting position (left side of Aisle 1, at top)
        aisle_width = config.store.aisles[0]['width']
        self.x = config.store.aisles[0]['x'] - aisle_width / 4  # Left side of aisle
        self.y = config.store.aisles[0]['y_start']
        
        # Movement state
        self.current_aisle = 0
        self.side = 'left'  # 'left' or 'right' - which side of aisle we're on
        self.direction = 'forward'  # 'forward' = 1->4, 'backward' = 4->1
        # Phases: 'going_down_left', 'going_up_right', 'entering_cross', 'crossing', 'exiting_cross'
        self.movement_phase = 'going_down_left'
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
        
        # Move toward target (only one axis at a time for grid-like movement)
        # For entering/exiting cross aisle, move vertically first
        # For crossing, move horizontally
        if self.movement_phase in ['entering_cross', 'exiting_cross', 'going_down_left', 'going_up_right']:
            # Vertical movement only
            if abs(dy) > 1:
                if move_distance >= abs(dy):
                    self.y = self.target_y
                else:
                    self.y += math.copysign(move_distance, dy)
            else:
                self.y = self.target_y
        elif self.movement_phase == 'crossing':
            # Horizontal movement only
            if abs(dx) > 1:
                if move_distance >= abs(dx):
                    self.x = self.target_x
                else:
                    self.x += math.copysign(move_distance, dx)
            else:
                self.x = self.target_xysign(move_distance, dx)
            else:
                self.x = self.target_x
    
    def _reached_target(self):
        """Handle reaching current target, set next target"""
        aisles = self.config.store.aisles
        cross_y = self.config.store.cross_aisle_y
        
        if self.movement_phase == 'going_down_left':
            # Reached bottom of aisle on left side
            self.aisles_visited.add(self.current_aisle)
            
            # Check if we can move to next aisle
            if self.direction == 'forward' and self.current_aisle < len(aisles) - 1:
                # Move to cross aisle
                self.movement_phase = 'entering_cross'
                self.target_y = cross_y
            elif self.direction == 'backward' and self.current_aisle > 0:
                # Move to cross aisle
                self.movement_phase = 'entering_cross'
                self.target_y = cross_y
            else:
                # Can't go further, switch to right side and go up
                self._switch_to_right_side()
        
        elif self.movement_phase == 'entering_cross':
            # Now in the cross aisle, move horizontally to next aisle
            self.movement_phase = 'crossing'
            if self.direction == 'forward':
                next_aisle = aisles[self.current_aisle + 1]
                # Target left side of next aisle
                self.target_x = next_aisle['x'] - next_aisle['width'] / 4
            else:
                next_aisle = aisles[self.current_aisle - 1]
                # Target left side of previous aisle
                self.target_x = next_aisle['x'] - next_aisle['width'] / 4
        
        elif self.movement_phase == 'crossing':
            # Reached the next aisle's X position, now exit cross aisle
            if self.direction == 'forward':
                self.current_aisle += 1
            else:
                self.current_aisle -= 1
            
            # Exit cross aisle by going up to the aisle start (left side)
            self.movement_phase = 'exiting_cross'
            self.target_y = aisles[self.current_aisle]['y_start']
            self.side = 'left'
        
        elif self.movement_phase == 'exiting_cross':
            # Exited cross aisle, now at top of new aisle (left side), go down
            self.movement_phase = 'going_down_left'
            self.target_y = aisles[self.current_aisle]['y_end']
        
        elif self.movement_phase == 'going_up_right':
            # Reached top of aisle on right side
            # Complete a pass
            if not self.first_pass_complete:
                self.first_pass_complete = True
                print(f"✅ First pass complete! Items can now go missing randomly")
                self._check_for_missing_items()
            else:
                self._check_for_missing_items()
            
            self.pass_count += 1
            self.aisles_visited.clear()
            
            # Check if we need to reverse direction
            if self.direction == 'forward' and self.current_aisle == len(aisles) - 1:
                # At last aisle going forward, reverse
                self.direction = 'backward'
                print(f"\n🔄 Pass {self.pass_count} complete - Reversing direction (← Backward)")
            elif self.direction == 'backward' and self.current_aisle == 0:
                # At first aisle going backward, reverse
                self.direction = 'forward'
                print(f"\n🔄 Pass {self.pass_count} complete - Reversing direction (→ Forward)")
            
            # Switch to left side and go down
            aisle_width = aisles[self.current_aisle]['width']
            self.x = aisles[self.current_aisle]['x'] - aisle_width / 4
            self.side = 'left'
            self.movement_phase = 'going_down_left'
            self.target_x = self.x
            self.target_y = aisles[self.current_aisle]['y_end']
    
    def _switch_to_right_side(self):
        """Switch from left side to right side of current aisle and go up"""
        aisles = self.config.store.aisles
        aisle_width = aisles[self.current_aisle]['width']
        
        # Move to right side
        self.x = aisles[self.current_aisle]['x'] + aisle_width / 4
        self.target_x = self.x
        self.side = 'right'
        
        # Go up the aisle
        self.movement_phase = 'going_up_right'
        self.target_y = aisles[self.current_aisle]['y_start']
    
    def _check_for_missing_items(self):
        """Randomly mark some items as missing based on disappearance_rate"""
        if not self.first_pass_complete:
            return
        
        detected_items = [item for item in self.items if item.detected and not item.missing]
        if not detected_items:
            return
        
        import random
        # Use disappearance_rate from config (varies from rate/2 to rate*1.5)
        rate_min = self.config.disappearance_rate * 0.5
    def get_status_info(self) -> dict:
        """Get current status for display"""
        aisles = self.config.store.aisles
        
        aisle_info = f"Aisle {self.current_aisle + 1}" if self.current_aisle < len(aisles) else "Transit"
        
        if self.movement_phase == 'going_down_left':
            direction_info = "↓ Down (Left)"
        elif self.movement_phase == 'going_up_right':
            direction_info = "↑ Up (Right)"
        elif self.movement_phase == 'entering_cross':
            direction_info = "↓ Enter Cross"
        elif self.movement_phase == 'crossing':
            direction_info = "→ Cross" if self.direction == 'forward' else "← Cross"
        elif self.movement_phase == 'exiting_cross':
            direction_info = "↑ Exit Cross"
        else:
            direction_info = "→ Cross"
        
        dir_arrow = "→" if self.direction == 'forward' else "←"
        
        return {
            "pass": self.pass_count + 1,
            "direction_arrow": dir_arrow,
            "aisle": aisle_info,
            "movement": direction_info,
            "position": (self.x, self.y),
            "side": self.side
        }   direction_info = "↓ Enter Cross"
        elif self.movement_phase == 'crossing':
            direction_info = "→ Cross" if self.direction == 'forward' else "← Cross"
        elif self.movement_phase == 'exiting_cross':
            direction_info = "↑ Exit Cross"
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
