"""
Historical Data Backfill Script
Generates realistic past purchase events and stock snapshots for analytics testing
Run: python -m simulation.backfill_history --days 30 --api http://localhost:8000
"""
import argparse
import random
from datetime import datetime, timedelta
import requests
from typing import List, Dict

# Match the simulation's product catalog structure
CATEGORIES = ['Sports', 'Footwear', 'Fitness', 'Accessories']

def fetch_products_from_backend(api_url: str) -> List[Dict]:
    """Fetch all products from backend"""
    try:
        response = requests.get(f"{api_url}/products", timeout=5)
        if response.status_code == 200:
            products = response.json()
            print(f"✅ Loaded {len(products)} products from backend")
            return products
        else:
            print(f"❌ Failed to fetch products: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error fetching products: {e}")
        return []

def fetch_zones_from_backend(api_url: str) -> List[Dict]:
    """Fetch all zones from backend"""
    try:
        response = requests.get(f"{api_url}/zones", timeout=5)
        if response.status_code == 200:
            zones = response.json()
            print(f"✅ Loaded {len(zones)} zones from backend")
            return zones
        else:
            print(f"❌ Failed to fetch zones: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error fetching zones: {e}")
        return []

def generate_hourly_activity_pattern() -> List[float]:
    """Generate realistic hourly activity multipliers (0-1) for a day"""
    # Simulate store traffic patterns:
    # Low: 6-9am, 1-3pm, 9pm-midnight
    # Medium: 9-11am, 3-5pm
    # High: 11am-1pm (lunch), 5-9pm (after work)
    patterns = [
        0.1, 0.1, 0.1, 0.1, 0.1, 0.1,  # 12am-6am: closed/very low
        0.2, 0.3, 0.4,                  # 6-9am: opening
        0.6, 0.7,                       # 9-11am: morning traffic
        0.9, 1.0,                       # 11am-1pm: lunch peak
        0.4, 0.5,                       # 1-3pm: afternoon dip
        0.6, 0.7,                       # 3-5pm: pickup
        0.9, 0.95, 1.0, 0.8,            # 5-9pm: evening peak
        0.4, 0.3, 0.2                   # 9pm-12am: closing
    ]
    return patterns

def generate_product_popularity(products: List[Dict]) -> Dict[int, float]:
    """Assign popularity scores to products (0-1)"""
    # Simulate realistic distribution: few very popular, many moderately popular, some slow
    popularity = {}
    for product in products:
        # Categories have different base popularity
        category = product['category']
        if category in ['Sports', 'Footwear']:
            base = random.uniform(0.5, 1.0)  # More popular
        elif category == 'Fitness':
            base = random.uniform(0.3, 0.8)  # Medium
        else:
            base = random.uniform(0.1, 0.6)  # Accessories less popular
        
        popularity[product['id']] = base
    
    return popularity

def generate_historical_purchases(
    api_url: str,
    products: List[Dict],
    zones: List[Dict],
    days: int,
    base_daily_rate: float = 50
):
    """Generate realistic historical purchase events"""
    print(f"\n📊 Generating {days} days of historical purchase data...")
    
    # Assign popularity to products
    popularity = generate_product_popularity(products)
    hourly_pattern = generate_hourly_activity_pattern()
    
    all_purchases = []
    
    # Simulate day by day
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    current_date = start_date
    
    while current_date < end_date:
        # Weekend boost (1.3x on Sat/Sun)
        day_of_week = current_date.weekday()
        weekend_multiplier = 1.3 if day_of_week >= 5 else 1.0
        
        # Random daily variation
        daily_variation = random.uniform(0.8, 1.2)
        
        # Simulate each hour
        for hour in range(24):
            hour_multiplier = hourly_pattern[hour]
            expected_purchases = (
                base_daily_rate * 
                (hour_multiplier / 24) * 
                weekend_multiplier * 
                daily_variation
            )
            
            # Poisson-like distribution for purchase count
            num_purchases = max(0, int(random.gauss(expected_purchases, expected_purchases * 0.3)))
            
            for _ in range(num_purchases):
                # Select product based on popularity
                product = random.choices(products, weights=[popularity[p['id']] for p in products])[0]
                
                # Random zone
                zone = random.choice(zones) if zones else None
                
                # Timestamp within this hour
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                timestamp = current_date.replace(hour=hour, minute=minute, second=second)
                
                # Create purchase event
                purchase_data = {
                    'product_id': product['id'],
                    'zone_id': zone['id'] if zone else None,
                    'x_position': random.uniform(100, 900) if zone else None,
                    'y_position': random.uniform(100, 700) if zone else None,
                    'purchased_at': timestamp.isoformat()
                }
                all_purchases.append(purchase_data)
        
        current_date += timedelta(days=1)
        print(f"  Generated day {(current_date - start_date).days}/{days} - {len(all_purchases)} purchases so far", end='\r')
    
    print(f"\n✅ Generated {len(all_purchases)} total purchase events")
    
    # Upload in batches
    print("📤 Uploading purchases to backend...")
    batch_size = 500
    uploaded = 0
    for i in range(0, len(all_purchases), batch_size):
        batch = all_purchases[i:i + batch_size]
        try:
            response = requests.post(
                f"{api_url}/analytics/bulk/purchases",
                json=batch,
                timeout=30
            )
            if response.status_code == 200:
                uploaded += len(batch)
                print(f"  Uploaded {uploaded}/{len(all_purchases)} purchases", end='\r')
            else:
                print(f"\n⚠️  Error uploading batch: {response.status_code}")
        except Exception as e:
            print(f"\n⚠️  Error uploading batch: {e}")
    
    print(f"\n✅ Uploaded {uploaded} purchase events")
    return uploaded

def generate_stock_snapshots(
    api_url: str,
    products: List[Dict],
    days: int,
    snapshot_interval_hours: int = 1
):
    """Generate hourly stock snapshots for time-series analysis"""
    print(f"\n📸 Generating stock snapshots (every {snapshot_interval_hours}h for {days} days)...")
    
    # Initialize stock levels for each product
    product_stocks = {}
    for product in products:
        # Random initial stock (5-20 items per product)
        product_stocks[product['id']] = random.randint(8, 20)
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    current_date = start_date
    
    snapshots = []
    snapshot_count = 0
    
    while current_date < end_date:
        for product in products:
            # Simulate stock changes (gradual depletion, occasional restocks)
            current_stock = product_stocks[product['id']]
            
            # Small chance of restock
            if random.random() < 0.05:  # 5% chance per snapshot
                restock_amount = random.randint(10, 20)
                current_stock += restock_amount
            
            # Gradual depletion (simulate sales)
            depletion = max(0, int(random.gauss(0.3, 0.2)))  # Average 0.3 items sold per hour
            current_stock = max(0, current_stock - depletion)
            
            product_stocks[product['id']] = current_stock
            
            # Create snapshot
            snapshot = {
                'product_id': product['id'],
                'timestamp': current_date.isoformat(),
                'present_count': current_stock,
                'missing_count': max(0, random.randint(0, 3)),  # Some items might be misplaced
                'zone_id': None  # Simplified - could add zone-specific snapshots
            }
            snapshots.append(snapshot)
            snapshot_count += 1
        
        current_date += timedelta(hours=snapshot_interval_hours)
        print(f"  Generated {snapshot_count} snapshots...", end='\r')
    
    print(f"\n✅ Generated {snapshot_count} stock snapshots")
    
    # Batch insert snapshots via API
    print("📤 Uploading snapshots to backend...")
    batch_size = 1000
    uploaded = 0
    for i in range(0, len(snapshots), batch_size):
        batch = snapshots[i:i + batch_size]
        try:
            response = requests.post(
                f"{api_url}/analytics/bulk/snapshots",
                json=batch,
                timeout=60
            )
            if response.status_code == 200:
                uploaded += len(batch)
                print(f"  Uploaded {uploaded}/{len(snapshots)} snapshots", end='\r')
            else:
                print(f"\n⚠️  Error uploading batch: {response.status_code}")
        except Exception as e:
            print(f"\n⚠️  Error uploading batch: {e}")
    
    print(f"\n✅ Uploaded {uploaded} stock snapshots")
    return uploaded

def main():
    parser = argparse.ArgumentParser(description="Backfill historical analytics data")
    parser.add_argument("--days", type=int, default=30, help="Days of history to generate")
    parser.add_argument("--api", default="http://localhost:8000", help="Backend API URL")
    parser.add_argument("--daily-purchases", type=float, default=50, help="Average daily purchase rate")
    parser.add_argument("--snapshot-interval", type=int, default=1, help="Hours between snapshots")
    
    args = parser.parse_args()
    
    print(f"""
╔══════════════════════════════════════════════════════════╗
║     OptiFlow Historical Data Backfill                    ║
║     Generating {args.days} days of analytics data                ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    # Fetch current products and zones
    products = fetch_products_from_backend(args.api)
    zones = fetch_zones_from_backend(args.api)
    
    if not products:
        print("❌ No products found. Please run the simulation first to create products.")
        return
    
    # Generate historical purchases
    total_purchases = generate_historical_purchases(
        args.api,
        products,
        zones,
        args.days,
        args.daily_purchases
    )
    
    # Generate stock snapshots
    total_snapshots = generate_stock_snapshots(
        args.api,
        products,
        args.days,
        args.snapshot_interval
    )
    
    print(f"""
✅ Backfill complete!

Summary:
  - Days generated: {args.days}
  - Products: {len(products)}
  - Zones: {len(zones)}
  - Purchases uploaded: {total_purchases}
  - Snapshots uploaded: {total_snapshots}

Next steps:
  1. View analytics at http://localhost:3000/analytics
  2. Verify data in database
  3. Start simulation to generate real-time data
    """)

if __name__ == "__main__":
    main()
