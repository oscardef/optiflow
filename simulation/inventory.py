"""
Inventory Management Module
============================
Product catalog and item generation with configurable duplication.
"""

import random
from dataclasses import dataclass
from typing import List, Dict
from .config import SimulationConfig, SimulationMode


@dataclass
class Product:
    """Product SKU definition"""
    sku: str
    name: str
    category: str


@dataclass
class Item:
    """Physical item with RFID tag"""
    rfid_tag: str
    product: Product
    x: float
    y: float
    detected: bool = False
    last_seen: float = None
    missing: bool = False
    reported_status: str = None  # Track last reported status


# Product catalog - base SKUs
PRODUCT_CATALOG = [
    # Sports Equipment (10 SKUs)
    Product("SPT-001", "Basketball", "Sports"),
    Product("SPT-002", "Soccer Ball", "Sports"),
    Product("SPT-003", "Tennis Ball", "Sports"),
    Product("SPT-004", "Baseball", "Sports"),
    Product("SPT-005", "Volleyball", "Sports"),
    Product("SPT-006", "Football", "Sports"),
    Product("SPT-007", "Tennis Racket", "Sports"),
    Product("SPT-008", "Badminton Set", "Sports"),
    Product("SPT-009", "Table Tennis Paddle", "Sports"),
    Product("SPT-010", "Golf Balls", "Sports"),
    
    # Footwear (30 SKUs with size variations)
    Product("FOT-001", "Running Shoes - Size 8", "Footwear"),
    Product("FOT-002", "Running Shoes - Size 9", "Footwear"),
    Product("FOT-003", "Running Shoes - Size 10", "Footwear"),
    Product("FOT-004", "Training Shoes - Size 8", "Footwear"),
    Product("FOT-005", "Training Shoes - Size 9", "Footwear"),
    Product("FOT-006", "Training Shoes - Size 10", "Footwear"),
    Product("FOT-007", "Basketball Shoes - Size 9", "Footwear"),
    Product("FOT-008", "Basketball Shoes - Size 10", "Footwear"),
    Product("FOT-009", "Basketball Shoes - Size 11", "Footwear"),
    Product("FOT-010", "Soccer Cleats - Size 8", "Footwear"),
    Product("FOT-011", "Soccer Cleats - Size 9", "Footwear"),
    Product("FOT-012", "Soccer Cleats - Size 10", "Footwear"),
    Product("FOT-013", "Tennis Shoes - Size 8", "Footwear"),
    Product("FOT-014", "Tennis Shoes - Size 9", "Footwear"),
    Product("FOT-015", "Tennis Shoes - Size 10", "Footwear"),
    Product("FOT-016", "Hiking Boots - Size 9", "Footwear"),
    Product("FOT-017", "Hiking Boots - Size 10", "Footwear"),
    Product("FOT-018", "Hiking Boots - Size 11", "Footwear"),
    Product("FOT-019", "Casual Sneakers - Black", "Footwear"),
    Product("FOT-020", "Casual Sneakers - White", "Footwear"),
    Product("FOT-021", "Casual Sneakers - Grey", "Footwear"),
    Product("FOT-022", "Sandals - Size 8", "Footwear"),
    Product("FOT-023", "Sandals - Size 9", "Footwear"),
    Product("FOT-024", "Sandals - Size 10", "Footwear"),
    Product("FOT-025", "Flip Flops - Small", "Footwear"),
    Product("FOT-026", "Flip Flops - Medium", "Footwear"),
    Product("FOT-027", "Flip Flops - Large", "Footwear"),
    Product("FOT-028", "Water Shoes - Size 8", "Footwear"),
    Product("FOT-029", "Water Shoes - Size 9", "Footwear"),
    Product("FOT-030", "Water Shoes - Size 10", "Footwear"),
    
    # Fitness Equipment (15 SKUs)
    Product("FIT-001", "Yoga Mat", "Fitness"),
    Product("FIT-002", "Resistance Bands", "Fitness"),
    Product("FIT-003", "Jump Rope", "Cardio"),
    Product("FIT-004", "Dumbbells 5lb", "Weights"),
    Product("FIT-005", "Dumbbells 10lb", "Weights"),
    Product("FIT-006", "Dumbbells 15lb", "Weights"),
    Product("FIT-007", "Kettlebell", "Weights"),
    Product("FIT-008", "Exercise Ball", "Fitness"),
    Product("FIT-009", "Foam Roller", "Fitness"),
    Product("FIT-010", "Pull-up Bar", "Fitness"),
    Product("FIT-011", "Ab Wheel", "Fitness"),
    Product("FIT-012", "Ankle Weights", "Fitness"),
    Product("FIT-013", "Medicine Ball", "Fitness"),
    Product("FIT-014", "Balance Board", "Fitness"),
    Product("FIT-015", "Suspension Trainer", "Fitness"),
    
    # Accessories (25 SKUs with variations)
    Product("ACC-001", "Water Bottle - Black", "Accessories"),
    Product("ACC-002", "Water Bottle - Blue", "Accessories"),
    Product("ACC-003", "Water Bottle - Red", "Accessories"),
    Product("ACC-004", "Gym Bag - Small", "Accessories"),
    Product("ACC-005", "Gym Bag - Large", "Accessories"),
    Product("ACC-006", "Sports Backpack - Black", "Accessories"),
    Product("ACC-007", "Sports Backpack - Navy", "Accessories"),
    Product("ACC-008", "Gym Towel - White", "Accessories"),
    Product("ACC-009", "Gym Towel - Grey", "Accessories"),
    Product("ACC-010", "Sweatband - White", "Accessories"),
    Product("ACC-011", "Sweatband - Black", "Accessories"),
    Product("ACC-012", "Sports Watch - Black", "Accessories"),
    Product("ACC-013", "Sports Watch - Silver", "Accessories"),
    Product("ACC-014", "Sports Watch - Blue", "Accessories"),
    Product("ACC-015", "Fitness Tracker - Black", "Accessories"),
    Product("ACC-016", "Fitness Tracker - Pink", "Accessories"),
    Product("ACC-017", "Headphones - Black", "Electronics"),
    Product("ACC-018", "Headphones - White", "Electronics"),
    Product("ACC-019", "Headphones - Red", "Electronics"),
    Product("ACC-020", "Armband - Small", "Accessories"),
    Product("ACC-021", "Armband - Large", "Accessories"),
    Product("ACC-022", "Yoga Strap - Purple", "Accessories"),
    Product("ACC-023", "Yoga Strap - Blue", "Accessories"),
    Product("ACC-024", "Resistance Band - Light", "Accessories"),
    Product("ACC-025", "Resistance Band - Heavy", "Accessories"),
    
    # Apparel (30 SKUs with size/color variations)
    Product("APP-001", "Sports Jersey - Red M", "Apparel"),
    Product("APP-002", "Sports Jersey - Red L", "Apparel"),
    Product("APP-003", "Sports Jersey - Blue M", "Apparel"),
    Product("APP-004", "Sports Jersey - Blue L", "Apparel"),
    Product("APP-005", "Athletic Shorts - Black M", "Apparel"),
    Product("APP-006", "Athletic Shorts - Black L", "Apparel"),
    Product("APP-007", "Athletic Shorts - Navy M", "Apparel"),
    Product("APP-008", "Athletic Shorts - Navy L", "Apparel"),
    Product("APP-009", "Track Pants - Black M", "Apparel"),
    Product("APP-010", "Track Pants - Black L", "Apparel"),
    Product("APP-011", "Track Pants - Grey M", "Apparel"),
    Product("APP-012", "Track Pants - Grey L", "Apparel"),
    Product("APP-013", "Athletic Socks - White", "Apparel"),
    Product("APP-014", "Athletic Socks - Black", "Apparel"),
    Product("APP-015", "Athletic Socks - Grey", "Apparel"),
    Product("APP-016", "Compression Shorts - M", "Apparel"),
    Product("APP-017", "Compression Shorts - L", "Apparel"),
    Product("APP-018", "Compression Shorts - XL", "Apparel"),
    Product("APP-019", "Tank Top - White M", "Apparel"),
    Product("APP-020", "Tank Top - White L", "Apparel"),
    Product("APP-021", "Tank Top - Black M", "Apparel"),
    Product("APP-022", "Tank Top - Black L", "Apparel"),
    Product("APP-023", "Hoodie - Grey M", "Apparel"),
    Product("APP-024", "Hoodie - Grey L", "Apparel"),
    Product("APP-025", "Hoodie - Black M", "Apparel"),
    Product("APP-026", "Hoodie - Black L", "Apparel"),
    Product("APP-027", "Windbreaker - Blue M", "Apparel"),
    Product("APP-028", "Windbreaker - Blue L", "Apparel"),
    Product("APP-029", "Sports Bra - S", "Apparel"),
    Product("APP-030", "Sports Bra - M", "Apparel"),
    
    # Swimming (6 SKUs)
    Product("SWM-001", "Swimming Goggles", "Swimming"),
    Product("SWM-002", "Swim Cap", "Swimming"),
    Product("SWM-003", "Kickboard", "Swimming"),
    Product("SWM-004", "Pull Buoy", "Swimming"),
    Product("SWM-005", "Swim Fins", "Swimming"),
    Product("SWM-006", "Nose Clip", "Swimming"),
    
    # Cycling (6 SKUs)
    Product("CYC-001", "Bicycle Helmet", "Cycling"),
    Product("CYC-002", "Bike Gloves", "Cycling"),
    Product("CYC-003", "Cycling Jersey", "Cycling"),
    Product("CYC-004", "Bike Lock", "Cycling"),
    Product("CYC-005", "Water Bottle Holder", "Cycling"),
    Product("CYC-006", "Bike Light", "Cycling"),
    
    # Nutrition (10 SKUs)
    Product("NUT-001", "Protein Powder", "Nutrition"),
    Product("NUT-002", "Energy Bar", "Nutrition"),
    Product("NUT-003", "Protein Bar", "Nutrition"),
    Product("NUT-004", "Sports Drink", "Nutrition"),
    Product("NUT-005", "Electrolyte Mix", "Nutrition"),
    Product("NUT-006", "Pre-Workout", "Nutrition"),
    Product("NUT-007", "BCAA", "Nutrition"),
    Product("NUT-008", "Creatine", "Nutrition"),
    Product("NUT-009", "Multivitamin", "Nutrition"),
    Product("NUT-010", "Fish Oil", "Nutrition"),
]


class InventoryGenerator:
    """Generate inventory items based on configuration"""
    
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.items: List[Item] = []
        self.rfid_counter = 1
    
    def generate_items(self) -> List[Item]:
        """
        Generate items with appropriate duplication based on mode
        Distributes items evenly across store shelves
        """
        target_count = self.config.target_item_count
        min_dup, max_dup = self.config.duplicates_per_sku
        
        # Calculate how many SKUs we need to reach target count (with buffer)
        avg_duplicates = (min_dup + max_dup) / 2
        # Add 20% buffer to ensure we have enough SKUs
        num_skus_needed = int(target_count / avg_duplicates * 1.2)
        
        # Select SKUs to use (cycle through catalog if needed)
        selected_products = []
        for i in range(num_skus_needed):
            product = PRODUCT_CATALOG[i % len(PRODUCT_CATALOG)]
            selected_products.append(product)
        
        # Generate items with random duplication within range, but stop at target
        items = []
        for product in selected_products:
            if len(items) >= target_count:
                break
                
            num_duplicates = random.randint(min_dup, max_dup)
            # Don't exceed target count
            num_duplicates = min(num_duplicates, target_count - len(items))
            
            # Only generate if we need items
            if num_duplicates > 0:
                for _ in range(num_duplicates):
                    # We'll assign positions later in distribute_items()
                    item = Item(
                        rfid_tag=f"RFID_{self.rfid_counter:04d}",
                        product=product,
                        x=0,  # Placeholder
                        y=0   # Placeholder
                    )
                    items.append(item)
                    self.rfid_counter += 1
        
        # Pad to reach exact target count if needed
        while len(items) < target_count:
            product = random.choice(PRODUCT_CATALOG)
            item = Item(
                rfid_tag=f"RFID_{self.rfid_counter:04d}",
                product=product,
                x=0,
                y=0
            )
            items.append(item)
            self.rfid_counter += 1
        
        # Distribute items across store shelves
        self.distribute_items(items)
        
        self.items = items
        print(f"📦 Generated {len(items)} items ({len(set(i.product.sku for i in items))} unique SKUs)")
        print(f"   Mode: {self.config.mode.value}")
        print(f"   Duplicates per SKU: {min_dup}-{max_dup}")
        
        return items
    
    def distribute_items(self, items: List[Item]):
        """Distribute items across store shelves, grouping duplicates together"""
        store = self.config.store
        
        # Generate shelf positions in all aisles (stay within RFID detection range of path)
        shelf_positions = []
        detection_range = self.config.tag.rfid_detection_range
        for aisle in store.aisles:
            # Offset shelves toward the walls but within detection radius of shopper paths
            max_offset = aisle['width'] / 2 - 10
            shelf_offset = min(max_offset, detection_range - 5)
            for side_offset in [-shelf_offset, shelf_offset]:
                for shelf_level in range(4):
                    x_pos = aisle['x'] + side_offset
                    
                    items_per_shelf = 30
                    aisle_length = aisle['y_end'] - aisle['y_start']
                    
                    for slot in range(items_per_shelf):
                        y_pos = aisle['y_start'] + (aisle_length * (slot + 0.5) / items_per_shelf)
                        shelf_positions.append((x_pos, y_pos))
        
        # Add positions in cross-aisle within detection radius
        cross_offset = min(detection_range - 5, store.cross_aisle_height / 2 - 5)
        for x_pos in range(int(store.cross_aisle_x_start - 40), int(store.cross_aisle_x_end + 40), 30):
            for side_offset in [-cross_offset, cross_offset]:
                y_pos = store.cross_aisle_y + side_offset
                shelf_positions.append((x_pos, y_pos))
        
        random.shuffle(shelf_positions)
        
        # Group items by SKU to place duplicates together
        items_by_sku = {}
        for item in items:
            sku = item.product.sku
            if sku not in items_by_sku:
                items_by_sku[sku] = []
            items_by_sku[sku].append(item)
        
        # Assign positions - all items of same SKU get same base position
        position_idx = 0
        for sku, sku_items in items_by_sku.items():
            if position_idx >= len(shelf_positions):
                position_idx = 0  # Wrap around if we run out
            
            # Get base position for this SKU
            base_x, base_y = shelf_positions[position_idx]
            position_idx += 1
            
            # Place all duplicates at same base position with tiny offset
            for item in sku_items:
                # Stack duplicates with minimal offset (±2cm)
                item.x = base_x + random.uniform(-2, 2)
                item.y = base_y + random.uniform(-2, 2)
    

    
    def get_inventory_summary(self) -> Dict[str, int]:
        """Get count of items per SKU"""
        summary = {}
        for item in self.items:
            sku = item.product.sku
            summary[sku] = summary.get(sku, 0) + 1
        return summary
