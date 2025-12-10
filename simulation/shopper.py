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
        
        # Starting position (left edge of Aisle 1, at top)
        aisle_width = config.store.aisles[0]['width']
        # Position very close to left wall - 60cm from center (very close to shelves)
        self.x = config.store.aisles[0]['x'] - 60  # Very close to left wall
        self.y = config.store.aisles[0]['y_start'] + 20  # Small margin from top
        
        # Movement state
        self.current_aisle = 0
        self.side = 'left'  # 'left' or 'right' - which side of aisle we're on
        self.direction = 'forward'  # 'forward' = 1->4, 'backward' = 4->1
        # Phases: 'going_down_left', 'going_up_right', 'entering_cross', 'crossing', 'exiting_cross'
        self.movement_phase = 'going_down_left'
        self.target_x = self.x
        self.target_y = config.store.aisles[0]['y_end'] - 20  # Small margin from bottom
        
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
        
        # Calculate movement distance based on speed and time
        move_distance = self.speed * dt
        
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
                self.x = self.target_x
    
    def _reached_target(self):
        """Handle reaching current target, set next target"""
        aisles = self.config.store.aisles
        cross_y = self.config.store.cross_aisle_y
        
        if self.movement_phase == 'going_down_left':
            # Reached bottom of aisle on left side
            self.aisles_visited.add(self.current_aisle)
            
            # ALWAYS switch to right side and go back up on EVERY aisle
            # This ensures we walk both edges of every aisle
            self._switch_to_right_side()
        
        elif self.movement_phase == 'entering_cross':
            # Now in the cross aisle, move horizontally to next aisle
            self.movement_phase = 'crossing'
            if self.direction == 'forward':
                next_aisle = aisles[self.current_aisle + 1]
                # Target very close to left wall of next aisle (60cm from center)
                self.target_x = next_aisle['x'] - 60
            else:
                next_aisle = aisles[self.current_aisle - 1]
                # Target very close to left wall of previous aisle (60cm from center)
                self.target_x = next_aisle['x'] - 60
        
        elif self.movement_phase == 'crossing':
            # Reached the next aisle's X position, now exit cross aisle
            if self.direction == 'forward':
                self.current_aisle += 1
            else:
                self.current_aisle -= 1
            
            # Exit cross aisle by going up to the aisle start (left side)
            self.movement_phase = 'exiting_cross'
            self.target_y = aisles[self.current_aisle]['y_start'] + 20  # Small margin from top
            self.side = 'left'
        
        elif self.movement_phase == 'exiting_cross':
            # Exited cross aisle, now at top of new aisle (left side), go down
            self.movement_phase = 'going_down_left'
            self.target_y = aisles[self.current_aisle]['y_end'] - 20  # Small margin from bottom
        
        elif self.movement_phase == 'going_up_right':
            # Reached top of aisle on right side
            # Now decide: move to next aisle or complete pass
            
            # Check if we can move to next aisle
            if self.direction == 'forward' and self.current_aisle < len(aisles) - 1:
                # Move to cross aisle to go to next aisle
                self.movement_phase = 'entering_cross'
                self.target_y = cross_y
            elif self.direction == 'backward' and self.current_aisle > 0:
                # Move to cross aisle to go to previous aisle
                self.movement_phase = 'entering_cross'
                self.target_y = cross_y
            else:
                # Can't go further - we're at the end (aisle 1 or 4)
                # Complete a pass
                if not self.first_pass_complete:
                    self.first_pass_complete = True
                    print(f"✅ First pass complete! Items can now go missing randomly")
                    self._check_for_missing_items()
                else:
                    self._check_for_missing_items()
                
                self.pass_count += 1
                self.aisles_visited.clear()
                
                # Reverse direction
                if self.direction == 'forward':
                    self.direction = 'backward'
                    print(f"\n🔄 Pass {self.pass_count} complete - Reversing direction (← Backward)")
                else:
                    self.direction = 'forward'
                    print(f"\n🔄 Pass {self.pass_count} complete - Reversing direction (→ Forward)")
                
                # If we have room to move in the new direction, exit this aisle via the cross aisle
                if (self.direction == 'forward' and self.current_aisle < len(aisles) - 1) or (
                    self.direction == 'backward' and self.current_aisle > 0
                ):
                    self.movement_phase = 'entering_cross'
                    self.target_y = cross_y
                else:
                    # Single-aisle fallback: switch sides and head down again
                    self.x = aisles[self.current_aisle]['x'] - 60
                    self.side = 'left'
                    self.target_x = self.x
                    self.movement_phase = 'going_down_left'
                    self.target_y = aisles[self.current_aisle]['y_end'] - 20  # Small margin from bottom
    
    def _switch_to_right_side(self):
        """Switch from left side to right side of current aisle and go up"""
        aisles = self.config.store.aisles
        
        # Move very close to right wall - 60cm from center (very close to shelves)
        self.x = aisles[self.current_aisle]['x'] + 60  # Very close to right wall
        self.target_x = self.x
        self.side = 'right'
        
        # Go up the aisle
        self.movement_phase = 'going_up_right'
        self.target_y = aisles[self.current_aisle]['y_start'] + 20  # Small margin from top
    
    def _check_for_missing_items(self):
        """Randomly mark some items as missing based on disappearance_rate
        
        Items must be detected as 'present' first before they can go missing.
        This creates the realistic flow: item detected -> item goes missing -> restock needed
        """
        if not self.first_pass_complete:
            return
        
        # Only consider items that have been detected (marked as present first)
        # AND are not already missing
        detected_items = [item for item in self.items if item.detected and not item.missing]
        
        print(f"\n   📦 _check_for_missing_items called:")
        print(f"      Total items: {len(self.items)}")
        print(f"      Detected items: {len([i for i in self.items if i.detected])}")
        print(f"      Already missing: {len([i for i in self.items if i.missing])}")
        print(f"      Candidates for disappearance: {len(detected_items)}")
        
        if not detected_items:
            print(f"      ⚠️ No detected items to make missing!")
            return
        
        import random
        # Group items by product to ensure we don't take entire stock at once
        items_by_product = {}
        for item in detected_items:
            product_key = item.product.sku
            if product_key not in items_by_product:
                items_by_product[product_key] = []
            items_by_product[product_key].append(item)
        
        # Decide how many PRODUCT TYPES should have missing items this pass
        # Use disappearance_rate as probability that ANY items go missing this pass
        roll = random.random()
        print(f"      🎲 Disappearance roll: {roll:.4f} (threshold: {self.config.disappearance_rate:.4f})")
        if roll < self.config.disappearance_rate:
            # Pick 1-2 product types to have items go missing
            num_products_affected = random.randint(1, 2)
            products_to_affect = random.sample(list(items_by_product.keys()), 
                                              min(num_products_affected, len(items_by_product)))
            
            print(f"      🚨 MARKING ITEMS AS MISSING! Affecting {len(products_to_affect)} product types")
            for product_key in products_to_affect:
                product_items = items_by_product[product_key]
                # Take only 1-2 items per product (realistic store behavior)
                num_to_take = min(random.randint(1, 2), len(product_items))
                items_to_disappear = random.sample(product_items, num_to_take)
                
                for item in items_to_disappear:
                    item.missing = True
                    print(f"         📦❌ Item {item.rfid_tag} ({item.product.name}) at ({item.x:.1f}, {item.y:.1f}) marked as MISSING")
        else:
            print(f"      ✅ No items going missing this pass")
    
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
        }
    
    def get_position(self):
        """Return current shopper position"""
        return self.x, self.y
