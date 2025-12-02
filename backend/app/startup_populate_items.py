"""
Backend startup script to auto-populate inventory_items if empty
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import InventoryItem, Product
from app.config import DATABASE_URL_SIMULATION
from simulation.regenerate_positions import generate_positions

# Use the same database URL as backend
engine = create_engine(DATABASE_URL_SIMULATION)
SessionLocal = sessionmaker(bind=engine)

def populate_items_if_needed():
    session = SessionLocal()
    try:
        item_count = session.query(InventoryItem).count()
        if item_count == 0:
            print("No inventory items found. Populating...")
            products = session.query(Product).order_by(Product.id).all()
            num_items = 2285 if len(products) > 0 else 0
            positions = generate_positions(num_items)
            item_num = 1
            pos_idx = 0
            for product in products:
                rfid_tag = f"RFID{str(item_num).zfill(8)}"
                x, y = positions[pos_idx]
                item = InventoryItem(
                    rfid_tag=rfid_tag,
                    product_id=product.id,
                    status="present",
                    x_position=x,
                    y_position=y
                )
                session.add(item)
                item_num += 1
                pos_idx += 1
                if pos_idx >= len(positions):
                    break
            session.commit()
            print(f"Created {item_num-1} inventory items.")
        else:
            print(f"Inventory already populated: {item_count} items.")
    except Exception as e:
        print(f"Error populating items: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    populate_items_if_needed()
