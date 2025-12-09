"""
Regenerate inventory item positions with correct aisle alignment.
Uses direct database connection to avoid API issues.
"""
import psycopg2
import random
from typing import List, Tuple

# Store configuration matching simulation/config.py
AISLES = [
    {'x': 180, 'y_start': 120, 'y_end': 700, 'width': 180},  # Aisle 1
    {'x': 395, 'y_start': 120, 'y_end': 700, 'width': 180},  # Aisle 2
    {'x': 610, 'y_start': 120, 'y_end': 700, 'width': 180},  # Aisle 3
    {'x': 825, 'y_start': 120, 'y_end': 700, 'width': 180},  # Aisle 4
]
CROSS_AISLE_Y = 400

def generate_positions(num_items: int) -> List[Tuple[float, float]]:
    """Generate shelf positions along aisles"""
    positions = []
    
    # Generate shelf positions in all aisles
    for aisle in AISLES:
        # 4 shelves per aisle, both sides (closer to walls)
        for side_offset in [-60, 60]:  # Close to left and right walls
            for shelf_level in range(4):
                x_pos = aisle['x'] + side_offset
                
                items_per_shelf = 30
                aisle_length = aisle['y_end'] - aisle['y_start']
                
                for slot in range(items_per_shelf):
                    y_pos = aisle['y_start'] + (aisle_length * (slot + 0.5) / items_per_shelf)
                    positions.append((round(x_pos, 2), round(y_pos, 2)))
    
    # Add positions in cross-aisle
    for x_pos in range(200, 900, 30):
        for side_offset in [-30, 30]:
            y_pos = CROSS_AISLE_Y + side_offset
            positions.append((round(x_pos, 2), round(y_pos, 2)))
    
    # Shuffle and select required number
    random.shuffle(positions)
    
    if len(positions) > num_items:
        positions = positions[:num_items]
    elif len(positions) < num_items:
        # If we need more positions, duplicate existing ones with small offsets
        while len(positions) < num_items:
            base_pos = random.choice(positions[:len(positions)])
            x_offset = random.uniform(-2, 2)
            y_offset = random.uniform(-2, 2)
            positions.append((round(base_pos[0] + x_offset, 2), round(base_pos[1] + y_offset, 2)))
    
    return positions

def main():
    # Connect to database (simulation database on port 5432)
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="optiflow_simulation",
        user="optiflow",
        password="optiflow_dev"
    )
    cursor = conn.cursor()
    
    try:
        # Get all products
        cursor.execute("SELECT sku FROM products ORDER BY sku")
        skus = [row[0] for row in cursor.fetchall()]
        print(f"Found {len(skus)} products")
        
        # Generate 3000 items (roughly 2 per SKU on average)
        num_items = 3000
        positions = generate_positions(num_items)
        print(f"Generated {len(positions)} positions")
        
        # Assign items to products
        items_per_product = num_items // len(skus)
        extra_items = num_items % len(skus)
        
        item_num = 1
        pos_idx = 0
        
        for sku in skus:
            # Number of items for this SKU
            count = items_per_product + (1 if item_num <= extra_items else 0)
            
            for _ in range(count):
                rfid_tag = f"RFID{str(item_num).zfill(8)}"
                x, y = positions[pos_idx]
                
                cursor.execute("""
                    INSERT INTO inventory_items (rfid_tag, sku, status, x_position, y_position)
                    VALUES (%s, %s, 'present', %s, %s)
                """, (rfid_tag, sku, x, y))
                
                item_num += 1
                pos_idx += 1
                
                if pos_idx >= len(positions):
                    break
            
            if pos_idx >= len(positions):
                break
        
        conn.commit()
        print(f"✅ Successfully created {item_num - 1} inventory items with aisle-aligned positions")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()
