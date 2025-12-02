"""
Inventory Generation Script
============================
Generates thousands of realistic products with variants (sizes, colors, styles)
and their associated RFID-tagged items for a realistic store simulation.

Run: python -m simulation.generate_inventory --items 3000 --api http://localhost:8000
"""
import argparse
import random
import requests
from typing import List, Dict, Tuple
from datetime import datetime

# Realistic product templates with variations
PRODUCT_TEMPLATES = {
    'Running Shoes': {
        'category': 'Footwear',
        'base_sku': 'RUN',
        'base_price': 89.99,
        'sizes': ['6', '6.5', '7', '7.5', '8', '8.5', '9', '9.5', '10', '10.5', '11', '11.5', '12'],
        'colors': ['Black', 'White', 'Navy', 'Grey', 'Red', 'Blue', 'Green'],
        'styles': ['Classic', 'Pro', 'Elite', 'Sport', 'Comfort'],
        'items_per_variant': (3, 8)
    },
    'Training Shoes': {
        'category': 'Footwear',
        'base_sku': 'TRN',
        'base_price': 79.99,
        'sizes': ['6', '7', '8', '9', '10', '11', '12'],
        'colors': ['Black', 'White', 'Grey', 'Navy'],
        'styles': ['Basic', 'Pro', 'CrossFit'],
        'items_per_variant': (2, 6)
    },
    'Basketball Shoes': {
        'category': 'Footwear',
        'base_sku': 'BBL',
        'base_price': 119.99,
        'sizes': ['7', '8', '9', '10', '11', '12', '13'],
        'colors': ['Black', 'White', 'Red', 'Blue'],
        'styles': ['Court', 'Street', 'Pro'],
        'items_per_variant': (2, 5)
    },
    'Athletic T-Shirt': {
        'category': 'Apparel',
        'base_sku': 'TSH',
        'base_price': 24.99,
        'sizes': ['XS', 'S', 'M', 'L', 'XL', 'XXL'],
        'colors': ['Black', 'White', 'Navy', 'Grey', 'Red', 'Blue', 'Green', 'Yellow'],
        'styles': ['Basic', 'Performance', 'Dri-Fit'],
        'items_per_variant': (5, 15)
    },
    'Athletic Shorts': {
        'category': 'Apparel',
        'base_sku': 'SHT',
        'base_price': 29.99,
        'sizes': ['XS', 'S', 'M', 'L', 'XL', 'XXL'],
        'colors': ['Black', 'Navy', 'Grey', 'Red', 'Blue'],
        'styles': ['Training', 'Running', 'Basketball'],
        'items_per_variant': (4, 12)
    },
    'Hoodie': {
        'category': 'Apparel',
        'base_sku': 'HDI',
        'base_price': 49.99,
        'sizes': ['S', 'M', 'L', 'XL', 'XXL'],
        'colors': ['Black', 'Grey', 'Navy', 'Charcoal'],
        'styles': ['Pullover', 'Zip-Up'],
        'items_per_variant': (3, 8)
    },
    'Yoga Pants': {
        'category': 'Apparel',
        'base_sku': 'YGP',
        'base_price': 54.99,
        'sizes': ['XS', 'S', 'M', 'L', 'XL'],
        'colors': ['Black', 'Navy', 'Grey', 'Purple', 'Teal'],
        'styles': ['Classic', 'High-Waist', 'Capri'],
        'items_per_variant': (4, 10)
    },
    'Sports Bra': {
        'category': 'Apparel',
        'base_sku': 'BRA',
        'base_price': 34.99,
        'sizes': ['XS', 'S', 'M', 'L', 'XL'],
        'colors': ['Black', 'White', 'Navy', 'Pink', 'Purple'],
        'styles': ['Low Support', 'Medium Support', 'High Support'],
        'items_per_variant': (3, 9)
    },
    'Basketball': {
        'category': 'Sports Equipment',
        'base_sku': 'BKB',
        'base_price': 29.99,
        'sizes': ['Youth', 'Intermediate', 'Official'],
        'colors': ['Orange', 'Orange/Black'],
        'styles': ['Indoor', 'Outdoor', 'Composite'],
        'items_per_variant': (3, 8)
    },
    'Soccer Ball': {
        'category': 'Sports Equipment',
        'base_sku': 'SCR',
        'base_price': 24.99,
        'sizes': ['Size 3', 'Size 4', 'Size 5'],
        'colors': ['White/Black', 'White/Blue'],
        'styles': ['Training', 'Match', 'Street'],
        'items_per_variant': (3, 7)
    },
    'Yoga Mat': {
        'category': 'Fitness',
        'base_sku': 'YGM',
        'base_price': 19.99,
        'sizes': ['Standard', 'Extra Long', 'Extra Wide'],
        'colors': ['Purple', 'Blue', 'Pink', 'Black', 'Green', 'Grey'],
        'styles': ['Basic', 'Premium', 'Eco'],
        'items_per_variant': (4, 10)
    },
    'Dumbbells': {
        'category': 'Fitness',
        'base_sku': 'DMB',
        'base_price': 19.99,
        'sizes': ['5lb', '10lb', '15lb', '20lb', '25lb', '30lb', '35lb', '40lb', '45lb', '50lb'],
        'colors': ['Black', 'Rubber Coated'],
        'styles': ['Hex', 'Round', 'Adjustable'],
        'items_per_variant': (2, 6)
    },
    'Resistance Bands': {
        'category': 'Fitness',
        'base_sku': 'RSB',
        'base_price': 12.99,
        'sizes': ['Light', 'Medium', 'Heavy', 'X-Heavy'],
        'colors': ['Yellow', 'Red', 'Green', 'Blue', 'Black'],
        'styles': ['Loop', 'Tube', 'Therapy'],
        'items_per_variant': (5, 12)
    },
    'Water Bottle': {
        'category': 'Accessories',
        'base_sku': 'WTR',
        'base_price': 14.99,
        'sizes': ['20oz', '32oz', '40oz', '64oz'],
        'colors': ['Black', 'Blue', 'Red', 'Green', 'Pink', 'White', 'Stainless'],
        'styles': ['Standard', 'Insulated', 'Sport Top'],
        'items_per_variant': (6, 15)
    },
    'Gym Bag': {
        'category': 'Accessories',
        'base_sku': 'GYM',
        'base_price': 39.99,
        'sizes': ['Small', 'Medium', 'Large'],
        'colors': ['Black', 'Navy', 'Grey', 'Red'],
        'styles': ['Duffel', 'Backpack', 'Tote'],
        'items_per_variant': (2, 6)
    },
    'Jump Rope': {
        'category': 'Cardio',
        'base_sku': 'JMP',
        'base_price': 9.99,
        'sizes': ['Adjustable', '8ft', '9ft', '10ft'],
        'colors': ['Black', 'Blue', 'Red'],
        'styles': ['Speed', 'Weighted', 'Basic'],
        'items_per_variant': (4, 10)
    },
    'Foam Roller': {
        'category': 'Recovery',
        'base_sku': 'FMR',
        'base_price': 24.99,
        'sizes': ['12 inch', '18 inch', '24 inch', '36 inch'],
        'colors': ['Black', 'Blue', 'Pink', 'Green'],
        'styles': ['Smooth', 'Textured', 'Vibrating'],
        'items_per_variant': (3, 8)
    },
    'Protein Powder': {
        'category': 'Nutrition',
        'base_sku': 'PRO',
        'base_price': 49.99,
        'sizes': ['1lb', '2lb', '5lb'],
        'colors': ['Vanilla', 'Chocolate', 'Strawberry', 'Unflavored'],
        'styles': ['Whey', 'Plant-Based', 'Isolate'],
        'items_per_variant': (3, 10)
    },
    'Energy Bar': {
        'category': 'Nutrition',
        'base_sku': 'NRG',
        'base_price': 2.49,
        'sizes': ['Single', '6-Pack', '12-Pack'],
        'colors': ['Chocolate', 'Peanut Butter', 'Berry', 'Vanilla'],
        'styles': ['Protein', 'Energy', 'Meal Replacement'],
        'items_per_variant': (8, 20)
    },
    'Fitness Tracker': {
        'category': 'Electronics',
        'base_sku': 'TRK',
        'base_price': 79.99,
        'sizes': ['Small', 'Medium', 'Large'],
        'colors': ['Black', 'Blue', 'Pink', 'White'],
        'styles': ['Basic', 'GPS', 'Heart Rate'],
        'items_per_variant': (2, 5)
    },
}

def generate_product_variants(template_name: str, template: Dict, sku_counter: Dict[str, int]) -> List[Dict]:
    """Generate all variants for a product template"""
    variants = []
    base_sku = template['base_sku']
    
    # Generate variants for each combination
    for style in template['styles']:
        for color in template['colors']:
            for size in template['sizes']:
                # Generate unique SKU
                sku_num = sku_counter.get(base_sku, 1)
                sku = f"{base_sku}-{sku_num:04d}"
                sku_counter[base_sku] = sku_num + 1
                
                # Create product name
                name = f"{template_name} - {style} {color} {size}"
                
                # Vary price slightly for different variants
                price_variance = random.uniform(-5, 5)
                price = round(template['base_price'] + price_variance, 2)
                
                # Calculate optimal stock level based on template
                min_items, max_items = template['items_per_variant']
                optimal_stock = random.randint(min_items, max_items)
                
                variants.append({
                    'sku': sku,
                    'name': name,
                    'category': template['category'],
                    'unit_price': price,
                    'optimal_stock_level': optimal_stock,
                    'reorder_threshold': max(1, optimal_stock // 3)
                })
    
    return variants

def generate_store_layout_positions(num_items: int) -> List[Tuple[float, float]]:
    """Generate realistic shelf positions for items in a store layout
    Matches the simulation's aisle configuration for proper visualization
    """
    positions = []
    
    # Store configuration matching simulation/config.py
    aisles = [
        {'x': 200, 'y_start': 150, 'y_end': 700, 'width': 80},  # Aisle 1
        {'x': 400, 'y_start': 120, 'y_end': 700, 'width': 80},  # Aisle 2
        {'x': 600, 'y_start': 120, 'y_end': 700, 'width': 80},  # Aisle 3
        {'x': 800, 'y_start': 120, 'y_end': 700, 'width': 80},  # Aisle 4
    ]
    cross_aisle_y = 400
    
    # Generate shelf positions in all aisles
    for aisle in aisles:
        # 4 shelves per aisle, both sides
        for side_offset in [-25, 25]:  # Left and right of aisle center
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
            y_pos = cross_aisle_y + side_offset
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

def create_products_batch(api_url: str, products: List[Dict]) -> List[Dict]:
    """Create products in database via API"""
    created_products = []
    
    print(f"\n📦 Creating {len(products)} products...")
    
    for i, product in enumerate(products, 1):
        try:
            response = requests.post(
                f"{api_url}/products",
                json=product,
                timeout=5
            )
            
            if response.status_code in [200, 201]:
                created_products.append(response.json())
            else:
                print(f"\n⚠️  Failed to create {product['sku']}: {response.status_code}")
        
        except Exception as e:
            print(f"\n❌ Error creating {product['sku']}: {e}")
        
        # Progress indicator
        if i % 50 == 0 or i == len(products):
            print(f"\r   Progress: {i}/{len(products)} ({100*i//len(products)}%)", end='')
    
    print()  # New line after progress
    return created_products

def create_inventory_items_batch(api_url: str, items: List[Dict]) -> int:
    """Create inventory items in database via API"""
    created_count = 0
    batch_size = 100
    
    print(f"\n🏷️  Creating {len(items)} RFID-tagged items...")
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        
        for item in batch:
            try:
                response = requests.post(
                    f"{api_url}/items",
                    json=item,
                    timeout=5
                )
                
                if response.status_code in [200, 201]:
                    created_count += 1
            
            except Exception as e:
                if created_count == 0 and i == 0:
                    print(f"\n❌ Error creating items: {e}")
                    print("   This might be expected if the /items endpoint doesn't exist yet.")
                    return 0
        
        # Progress indicator
        current = min(i + batch_size, len(items))
        print(f"\r   Progress: {current}/{len(items)} ({100*current//len(items)}%)", end='')
    
    print()  # New line after progress
    return created_count

def main():
    parser = argparse.ArgumentParser(description='Generate realistic store inventory')
    parser.add_argument('--items', type=int, default=3000, help='Target number of inventory items')
    parser.add_argument('--api', type=str, default='http://localhost:8000', help='Backend API URL')
    parser.add_argument('--templates', type=str, nargs='*', help='Specific templates to use (default: all)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be generated without creating')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🏪 OptiFlow Inventory Generator")
    print("=" * 60)
    
    # Select templates
    if args.templates:
        templates = {k: v for k, v in PRODUCT_TEMPLATES.items() if k in args.templates}
    else:
        templates = PRODUCT_TEMPLATES
    
    print(f"\n📋 Configuration:")
    print(f"   Target items: {args.items}")
    print(f"   Product templates: {len(templates)}")
    print(f"   API: {args.api}")
    
    # Generate all product variants
    print(f"\n🔧 Generating product variants...")
    all_products = []
    sku_counter = {}
    
    for template_name, template in templates.items():
        variants = generate_product_variants(template_name, template, sku_counter)
        all_products.extend(variants)
    
    print(f"   ✅ Generated {len(all_products)} unique product variants")
    
    # Calculate how many items per product
    items_per_product = args.items / len(all_products)
    print(f"   📊 Average {items_per_product:.1f} items per product variant")
    
    # Generate RFID-tagged inventory items
    print(f"\n🏷️  Generating RFID-tagged items...")
    all_items = []
    rfid_counter = 1
    positions = generate_store_layout_positions(args.items)
    position_idx = 0
    
    for product in all_products:
        # Number of physical items for this product
        num_items = max(1, round(product['optimal_stock_level']))
        
        for _ in range(num_items):
            if position_idx >= len(positions):
                break
            
            x, y = positions[position_idx]
            position_idx += 1
            
            all_items.append({
                'rfid_tag': f"RFID-{rfid_counter:08d}",
                'product_sku': product['sku'],  # Will need to map to product_id after creation
                'status': 'present',
                'x_position': x,
                'y_position': y
            })
            rfid_counter += 1
            
            if len(all_items) >= args.items:
                break
        
        if len(all_items) >= args.items:
            break
    
    print(f"   ✅ Generated {len(all_items)} RFID-tagged items")
    
    # Summary
    print(f"\n📊 Generation Summary:")
    print(f"   Products: {len(all_products)}")
    print(f"   Items: {len(all_items)}")
    
    categories = {}
    for p in all_products:
        categories[p['category']] = categories.get(p['category'], 0) + 1
    
    print(f"\n   Categories:")
    for cat, count in sorted(categories.items()):
        print(f"     • {cat}: {count} products")
    
    if args.dry_run:
        print(f"\n   🔍 DRY RUN - No data created")
        print(f"\n   Sample products:")
        for i, p in enumerate(all_products[:5], 1):
            print(f"     {i}. {p['sku']}: {p['name']} (${p['unit_price']})")
        return
    
    # Create in database
    print(f"\n" + "=" * 60)
    print("💾 Creating inventory in database...")
    print("=" * 60)
    
    try:
        # Test API connection
        response = requests.get(f"{args.api}/products", timeout=5)
        if response.status_code != 200:
            print(f"❌ Cannot connect to API at {args.api}")
            return
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        return
    
    # Create products
    created_products = create_products_batch(args.api, all_products)
    
    if len(created_products) == 0:
        print("❌ No products were created. Check API connection and logs.")
        return
    
    print(f"✅ Created {len(created_products)} products")
    
    # Map SKUs to product IDs
    sku_to_id = {p['sku']: p['id'] for p in created_products}
    
    # Update items with product_id
    for item in all_items:
        sku = item.pop('product_sku')
        item['product_id'] = sku_to_id.get(sku)
    
    # Filter out items with no product_id
    valid_items = [item for item in all_items if item['product_id'] is not None]
    
    # Create inventory items
    created_items = create_inventory_items_batch(args.api, valid_items)
    
    print(f"\n" + "=" * 60)
    print("✅ Inventory Generation Complete!")
    print("=" * 60)
    print(f"   Products created: {len(created_products)}")
    print(f"   Items created: {created_items}")
    print(f"\n💡 You can now:")
    print(f"   • Run simulation with: python -m simulation.main --analytics")
    print(f"   • Generate analytics data: Visit Analytics → Generate Data")
    print("=" * 60)

if __name__ == "__main__":
    main()
