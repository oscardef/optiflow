"""
Historical Data Backfill Script
Generates realistic past purchase events and stock snapshots for analytics testing
Run: python -m simulation.backfill_history --days 30 --api http://localhost:8000
"""
import argparse
import random
from datetime import datetime, timedelta, timezone
import requests
from typing import List, Dict

# Match the simulation's product catalog structure
CATEGORIES = ['Sports', 'Footwear', 'Fitness', 'Accessories']

# Density presets for fast-forward mode
DENSITY_PRESETS = {
    'sparse': {
        'daily_purchases': 20,
        'snapshot_interval': 6,  # Every 6 hours
        'description': 'Low traffic - 20 purchases/day, 4 snapshots/day'
    },
    'normal': {
        'daily_purchases': 50,
        'snapshot_interval': 3,  # Every 3 hours
        'description': 'Normal traffic - 50 purchases/day, 8 snapshots/day'
    },
    'dense': {
        'daily_purchases': 100,
        'snapshot_interval': 1,  # Every hour
        'description': 'High traffic - 100 purchases/day, 24 snapshots/day'
    },
    'stress': {
        'daily_purchases': 300,
        'snapshot_interval': 0.5,  # Every 30 minutes
        'description': 'Stress test - 300 purchases/day, 48 snapshots/day (for performance testing)'
    },
    'extreme': {
        'daily_purchases': 200,
        'snapshot_interval': 1,
        'description': 'Very high traffic - 200 purchases/day, 24 snapshots/day'
    }
}

def print_progress_bar(current: int, total: int, prefix: str = '', bar_length: int = 40):
    """Display progress bar for batch uploads"""
    filled = int(bar_length * current / total)
    bar = '█' * filled + '░' * (bar_length - filled)
    percent = 100 * (current / total)
    print(f'\r{prefix} |{bar}| {percent:.1f}% ({current}/{total})', end='', flush=True)
    if current == total:
        print()  # New line on completion

def check_simulation_mode(api_url: str) -> bool:
    """Check if system is in SIMULATION mode - backfill only works in simulation"""
    try:
        response = requests.get(f"{api_url}/config/mode", timeout=5)
        if response.status_code == 200:
            data = response.json()
            mode = data.get('mode', '').upper()
            if mode == 'PRODUCTION':
                print("""\n❌ ERROR: Cannot generate analytics data in PRODUCTION mode!\n
Backfill history is only available in SIMULATION mode.
This ensures analytics data matches simulated store inventory.\n
To switch to simulation mode:
  1. Go to the main dashboard
  2. Stop any running simulation
  3. Switch mode to SIMULATION
  4. Generate inventory items first
  5. Then run backfill again\n""")
                return False
            print(f"✅ System is in {mode} mode - proceeding...")
            return True
        else:
            print(f"⚠️  Could not verify system mode (status {response.status_code}), proceeding anyway...")
            return True
    except Exception as e:
        print(f"⚠️  Could not check system mode: {e}, proceeding anyway...")
        return True

def check_inventory_items(api_url: str) -> int:
    """Check if inventory items exist - required for realistic analytics"""
    try:
        response = requests.get(f"{api_url}/data/items", timeout=5)
        if response.status_code == 200:
            items = response.json()
            item_count = len(items)
            if item_count == 0:
                print("""\n❌ ERROR: No inventory items found in database!\n
You must generate inventory items before creating analytics data.
Analytics (purchases, stock snapshots) are based on items in your store.\n
To generate items:
  1. Ensure you're in SIMULATION mode
  2. Run: python -m simulation.generate_inventory --items 1000
     (or start the simulation from the dashboard)\n""")
                return 0
            print(f"✅ Found {item_count} inventory items in store")
            return item_count
        else:
            print(f"⚠️  Could not verify inventory items (status {response.status_code})")
            return -1
    except Exception as e:
        print(f"⚠️  Could not check inventory items: {e}")
        return -1

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



def generate_hourly_activity_pattern(is_weekend: bool = False) -> List[float]:
    """Generate realistic hourly activity multipliers (0-1) for a day
    
    Decathlon store patterns:
    - Weekdays: Lunch peak (12-2pm) and evening peak (5-8pm)
    - Weekends: Strong morning-afternoon traffic (10am-6pm) with 2-3x volume
    - Sports stores see more weekend activity vs weekday
    """
    if is_weekend:
        # Weekend: busy all day from 10am-7pm
        patterns = [
            0.05, 0.05, 0.05, 0.05, 0.05, 0.05,  # 12am-6am: closed
            0.1, 0.15, 0.2,                      # 6-9am: opening
            0.7, 0.85,                           # 9-11am: morning rush
            0.95, 1.0,                           # 11am-1pm: peak shopping
            1.0, 0.95,                           # 1-3pm: sustained high traffic
            0.9, 0.85,                           # 3-5pm: afternoon shopping
            0.8, 0.75, 0.6, 0.4,                 # 5-9pm: winding down
            0.2, 0.15, 0.1                       # 9pm-12am: closing
        ]
    else:
        # Weekday: lunch and after-work peaks
        patterns = [
            0.05, 0.05, 0.05, 0.05, 0.05, 0.05,  # 12am-6am: closed
            0.1, 0.15, 0.2,                      # 6-9am: opening
            0.3, 0.4,                            # 9-11am: morning shoppers
            0.7, 0.8,                            # 11am-1pm: lunch peak
            0.4, 0.3,                            # 1-3pm: afternoon dip
            0.5, 0.6,                            # 3-5pm: building up
            0.8, 0.9, 1.0, 0.7,                  # 5-9pm: after-work peak
            0.3, 0.2, 0.1                        # 9pm-12am: closing
        ]
    return patterns

def generate_product_popularity(products: List[Dict]) -> Dict[int, Dict]:
    """Assign popularity profiles to products with trends and special events
    
    Realistic Decathlon store patterns:
    - Dead stock: 15-20% of products (unpopular sizes, niche items, seasonal mismatch)
    - Fast movers: Popular items like running shoes, protein bars, water bottles
    - Seasonal: Swimming gear slower in winter, running gear higher in spring
    - Price-based: Expensive items (€80+) sell rarely, cheap items (<€20) sell frequently
    
    Returns dict with:
    - base_popularity: baseline sales rate (0-1), with many low values for dead stock
    - trend: gradual change over time (-0.02 to +0.02 per day)
    - has_spike: whether product will have a sudden spike (promotions)
    - spike_day: which day the spike occurs (if has_spike)
    - has_shortage: whether product runs out of stock
    - shortage_start: day when shortage begins
    - is_dead_stock: product with very low/zero sales
    """
    popularity = {}
    
    # Dead stock: 15-20% of products with near-zero sales
    num_dead_stock = int(len(products) * random.uniform(0.15, 0.20))
    dead_stock_products = random.sample(products, num_dead_stock)
    
    # Select 5-7 products for trending up (viral/seasonal)
    remaining = [p for p in products if p not in dead_stock_products]
    trending_up = random.sample(remaining, min(7, len(remaining) // 10))
    
    # Select 5-7 products for trending down (going out of season)
    trending_down = random.sample(
        [p for p in remaining if p not in trending_up], 
        min(7, len(remaining) // 10)
    )
    
    # Select 15-20 products for sudden spikes (promotions are common in Decathlon)
    spike_products = random.sample(
        [p for p in remaining if p not in trending_up + trending_down], 
        min(20, len(remaining) // 6)
    )
    
    # Select 5-8 products that will experience shortages
    shortage_products = random.sample(remaining, min(8, len(remaining) // 15))
    
    for product in products:
        category = product['category']
        unit_price = product.get('unit_price', 25.0)
        
        # Dead stock: very low base popularity
        if product in dead_stock_products:
            base = random.uniform(0.0, 0.05)  # 0-5% of average, essentially zero sales
            is_dead_stock = True
        else:
            is_dead_stock = False
            
            # Base popularity by category (Decathlon-specific)
            if category in ['Nutrition']:  # Fast-moving consumables
                base = random.uniform(0.7, 1.0)
            elif category in ['Sports', 'Accessories']:  # Popular mid-range items
                base = random.uniform(0.5, 0.9)
            elif category in ['Footwear']:  # High variation (size dependent)
                base = random.uniform(0.3, 0.8)
            elif category in ['Fitness', 'Cardio', 'Weights']:  # Moderate demand
                base = random.uniform(0.4, 0.7)
            elif category in ['Apparel']:  # Fashion-dependent
                base = random.uniform(0.3, 0.7)
            elif category in ['Swimming']:  # Seasonal (low in winter)
                base = random.uniform(0.2, 0.5)
            elif category in ['Cycling']:  # Seasonal (higher in spring/summer)
                base = random.uniform(0.3, 0.6)
            elif category in ['Electronics']:  # Higher price = lower volume
                base = random.uniform(0.2, 0.5)
            else:
                base = random.uniform(0.2, 0.6)
            
            # Price-based adjustment: expensive items sell less frequently
            if unit_price > 80:  # Premium items (bikes, premium shoes)
                base *= random.uniform(0.2, 0.4)  # 20-40% of base rate
            elif unit_price > 40:  # Mid-range
                base *= random.uniform(0.5, 0.8)
            # Cheap items (<€40) keep full base rate or higher
        
        # Determine trend
        if product in trending_up:
            trend = random.uniform(0.01, 0.03)  # 1-3% increase per day
        elif product in trending_down:
            trend = random.uniform(-0.03, -0.01)  # 1-3% decrease per day
        else:
            trend = random.uniform(-0.005, 0.005)  # Slight random walk
        
        # Spike configuration
        has_spike = product in spike_products
        spike_day = random.randint(5, 25) if has_spike else None
        spike_magnitude = random.uniform(3, 8) if has_spike else 1  # 3-8x normal sales
        
        # Shortage configuration
        has_shortage = product in shortage_products
        shortage_start = random.randint(10, 20) if has_shortage else None
        shortage_duration = random.randint(3, 7) if has_shortage else 0
        
        popularity[product['id']] = {
            'base_popularity': base,
            'trend': trend,
            'has_spike': has_spike,
            'spike_day': spike_day,
            'spike_magnitude': spike_magnitude,
            'has_shortage': has_shortage,
            'shortage_start': shortage_start,
            'shortage_duration': shortage_duration,
            'category': category,
            'is_dead_stock': is_dead_stock
        }
    
    return popularity

def generate_historical_purchases(
    api_url: str,
    products: List[Dict],
    days: int,
    base_daily_rate: float = 50,
    fast_forward: bool = True
):
    """Generate realistic historical purchase events
    
    Args:
        fast_forward: If True, generates all data instantly in memory.
                     If False, uses the old day-by-day approach.
    """
    print(f"\n📊 Generating {days} days of historical purchase data...")
    if fast_forward:
        print("⚡ Fast-forward mode: Generating all data instantly...")
    
    # Assign popularity to products
    popularity = generate_product_popularity(products)
    hourly_pattern = generate_hourly_activity_pattern()
    
    all_purchases = []
    
    # Simulate day by day
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    current_date = start_date
    
    while current_date < end_date:
        # Strong weekend boost for sports store (2-3x on Sat/Sun)
        day_of_week = current_date.weekday()
        is_weekend = day_of_week >= 5
        weekend_multiplier = random.uniform(2.2, 2.8) if is_weekend else 1.0
        
        # Random daily variation
        daily_variation = random.uniform(0.85, 1.15)
        
        # Get appropriate hourly pattern for day type
        hourly_pattern_today = generate_hourly_activity_pattern(is_weekend)
        
        # Simulate each hour
        for hour in range(24):
            hour_multiplier = hourly_pattern_today[hour]
            expected_purchases = (
                base_daily_rate * 
                (hour_multiplier / 24) * 
                weekend_multiplier * 
                daily_variation
            )
            
            # Poisson-like distribution for purchase count
            num_purchases = max(0, int(random.gauss(expected_purchases, expected_purchases * 0.3)))
            
            for _ in range(num_purchases):
                # Calculate day number for trend/spike calculations
                day_num = (current_date - start_date).days
                
                # Calculate adjusted popularity for each product based on trends, spikes, shortages
                adjusted_weights = []
                available_products = []
                
                for product in products:
                    profile = popularity[product['id']]
                    
                    # Check if product is in shortage period
                    if profile['has_shortage']:
                        if profile['shortage_start'] <= day_num < profile['shortage_start'] + profile['shortage_duration']:
                            continue  # Skip this product, it's out of stock
                    
                    # Base popularity
                    weight = profile['base_popularity']
                    
                    # Apply trend (compounds daily)
                    trend_multiplier = 1 + (profile['trend'] * day_num)
                    weight *= max(0.1, trend_multiplier)  # Don't go below 0.1
                    
                    # Apply spike if this is spike day (±1 day window for realism)
                    if profile['has_spike'] and abs(day_num - profile['spike_day']) <= 1:
                        weight *= profile['spike_magnitude']
                    
                    # Category-specific patterns for Decathlon store
                    # Weekend boost for Sports/Fitness/Cycling (people have free time)
                    if is_weekend and profile['category'] in ['Sports', 'Fitness', 'Cycling', 'Cardio']:
                        weight *= 1.3
                    
                    # Weekday lunch boost for Nutrition (office workers buying snacks)
                    if not is_weekend and 11 <= hour <= 13 and profile['category'] == 'Nutrition':
                        weight *= 1.4
                    
                    # Morning boost for Fitness equipment (people shopping before gym)
                    if 7 <= hour <= 9 and profile['category'] in ['Fitness', 'Weights']:
                        weight *= 1.2
                    
                    adjusted_weights.append(max(0.01, weight))
                    available_products.append(product)
                
                if not available_products:
                    continue  # All products out of stock (unlikely)
                
                # Select product based on adjusted popularity
                product = random.choices(available_products, weights=adjusted_weights)[0]
                
                # Timestamp within this hour
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                timestamp = current_date.replace(hour=hour, minute=minute, second=second)
                
                # Create purchase event
                purchase_data = {
                    'product_id': product['id'],
                    'purchased_at': timestamp.isoformat()
                }
                all_purchases.append(purchase_data)
        
        current_date += timedelta(days=1)
        if fast_forward:
            # Show progress every 10% in fast-forward mode
            progress = (current_date - start_date).days
            if progress % max(1, days // 10) == 0 or progress == days:
                print_progress_bar(progress, days, '  Progress')
        else:
            print(f"  Generated day {(current_date - start_date).days}/{days} - {len(all_purchases)} purchases so far", end='\r')
    
    if not fast_forward:
        print()  # New line if not using progress bar
    print(f"✅ Generated {len(all_purchases)} total purchase events")
    
    # Upload in batches
    print("\n📤 Uploading purchases to backend...")
    batch_size = 500
    uploaded = 0
    total_batches = (len(all_purchases) + batch_size - 1) // batch_size
    
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
                current_batch = i // batch_size + 1
                print_progress_bar(current_batch, total_batches, '  Upload')
            else:
                print(f"\n⚠️  Error uploading batch: {response.status_code}")
        except Exception as e:
            print(f"\n⚠️  Error uploading batch: {e}")
    
    print(f"✅ Uploaded {uploaded} purchase events")
    return uploaded

def generate_stock_snapshots(
    api_url: str,
    products: List[Dict],
    days: int,
    snapshot_interval_hours: int = 1,
    fast_forward: bool = True
):
    """Generate hourly stock snapshots for time-series analysis"""
    print(f"\n📸 Generating stock snapshots (every {snapshot_interval_hours}h for {days} days)...")
    if fast_forward:
        print("⚡ Fast-forward mode: Generating all snapshots instantly...")
    
    # Initialize stock levels for each product
    product_stocks = {}
    last_restock_day = {}
    
    for product in products:
        # Random initial stock (10-30 items per product)
        product_stocks[product['id']] = random.randint(15, 30)
        last_restock_day[product['id']] = -10  # Last restocked 10 days before start
    
    # Fetch popularity profiles (needed for realistic depletion rates)
    popularity = generate_product_popularity(products)
    
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    current_date = start_date
    
    snapshots = []
    snapshot_count = 0
    
    while current_date < end_date:
        day_num = (current_date - start_date).days
        
        for product in products:
            profile = popularity[product['id']]
            current_stock = product_stocks[product['id']]
            
            # Calculate realistic depletion based on product popularity and trends
            base_depletion_rate = profile['base_popularity'] * snapshot_interval_hours * 0.5
            
            # Apply trend
            trend_multiplier = 1 + (profile['trend'] * day_num)
            depletion_rate = base_depletion_rate * max(0.1, trend_multiplier)
            
            # Spike causes faster depletion
            if profile['has_spike'] and abs(day_num - profile['spike_day']) <= 1:
                depletion_rate *= profile['spike_magnitude']
            
            # Simulate depletion with variance
            depletion = max(0, int(random.gauss(depletion_rate, depletion_rate * 0.3)))
            current_stock = max(0, current_stock - depletion)
            
            # Intelligent restocking logic
            days_since_restock = day_num - last_restock_day[product['id']]
            restock_threshold = 5  # Restock when below 5 items
            
            # Restock if low AND it's been at least 3 days since last restock
            if current_stock <= restock_threshold and days_since_restock >= 3:
                # Don't restock during shortage period
                if not (profile['has_shortage'] and 
                       profile['shortage_start'] <= day_num < profile['shortage_start'] + profile['shortage_duration']):
                    # Restock amount based on popularity
                    if profile['base_popularity'] > 0.7:
                        restock_amount = random.randint(20, 35)  # Popular items get more stock
                    elif profile['base_popularity'] > 0.4:
                        restock_amount = random.randint(15, 25)
                    else:
                        restock_amount = random.randint(10, 20)  # Slow movers get less
                    
                    current_stock += restock_amount
                    last_restock_day[product['id']] = day_num
            
            # If in shortage period, force stock to 0
            if profile['has_shortage']:
                if profile['shortage_start'] <= day_num < profile['shortage_start'] + profile['shortage_duration']:
                    current_stock = 0
            
            product_stocks[product['id']] = current_stock
            
            # Create snapshot
            snapshot = {
                'product_id': product['id'],
                'timestamp': current_date.isoformat(),
                'present_count': current_stock,
                'missing_count': max(0, random.randint(0, 3))  # Some items might be misplaced
            }
            snapshots.append(snapshot)
            snapshot_count += 1
        
        current_date += timedelta(hours=snapshot_interval_hours)
        if not fast_forward and snapshot_count % 100 == 0:
            print(f"  Generated {snapshot_count} snapshots...", end='\r')
    
    if fast_forward:
        print(f"  Generated {snapshot_count} snapshots")
    else:
        print()  # New line
    print(f"✅ Generated {len(snapshots)} stock snapshots")
    
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
    parser = argparse.ArgumentParser(
        description="Backfill historical analytics data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Density Presets:
  sparse:  Low traffic (20 purchases/day, 4 snapshots/day)
  normal:  Normal traffic (50 purchases/day, 8 snapshots/day) [default]
  dense:   High traffic (100 purchases/day, 24 snapshots/day)
  extreme: Very high traffic (200 purchases/day, 24 snapshots/day)

Examples:
  # Generate 7 days with normal density (fast)
  python -m simulation.backfill_history --days 7
  
  # Generate 30 days with high density
  python -m simulation.backfill_history --days 30 --density dense
  
  # Generate 90 days with sparse data quickly
  python -m simulation.backfill_history --days 90 --density sparse
        """
    )
    parser.add_argument("--days", type=int, default=7, help="Days of history to generate (default: 7)")
    parser.add_argument("--api", default="http://localhost:8000", help="Backend API URL")
    parser.add_argument("--density", choices=['sparse', 'normal', 'dense', 'stress', 'extreme'], 
                       default='normal', help="Data density preset (default: normal)")
    parser.add_argument("--daily-purchases", type=float, help="Override: Average daily purchase rate")
    parser.add_argument("--snapshot-interval", type=int, help="Override: Hours between snapshots")
    parser.add_argument("--no-fast-forward", action='store_true', 
                       help="Disable fast-forward mode (slower, shows day-by-day progress)")
    
    args = parser.parse_args()
    
    # Apply density preset
    preset = DENSITY_PRESETS[args.density]
    daily_purchases = args.daily_purchases if args.daily_purchases else preset['daily_purchases']
    snapshot_interval = args.snapshot_interval if args.snapshot_interval else preset['snapshot_interval']
    fast_forward = not args.no_fast_forward
    
    # Calculate estimates
    estimated_purchases = int(args.days * daily_purchases)
    estimated_snapshots = int(args.days * (24 / snapshot_interval))
    
    print(f"""
╔══════════════════════════════════════════════════════════╗
║     OptiFlow Historical Data Backfill                    ║
║     Mode: {'Fast-Forward ⚡' if fast_forward else 'Standard'}                               ║
╚══════════════════════════════════════════════════════════╝

Configuration:
  Days: {args.days}
  Density: {args.density} - {preset['description']}
  Estimated purchases: ~{estimated_purchases:,}
  Estimated snapshots: ~{estimated_snapshots:,} (per product)
    """)
    
    # Step 1: Check system is in SIMULATION mode
    if not check_simulation_mode(args.api):
        return
    
    # Step 2: Verify inventory items exist
    item_count = check_inventory_items(args.api)
    if item_count == 0:
        return
    
    # Step 3: Fetch current products
    products = fetch_products_from_backend(args.api)
    
    if not products:
        print("❌ No products found. Please sync products from simulation catalog first.")
        print("   Run: curl -X POST http://localhost:8000/products/sync-from-catalog")
        return
    
    start_time = datetime.now()
    
    # Generate historical purchases
    total_purchases = generate_historical_purchases(
        args.api,
        products,
        args.days,
        daily_purchases,
        fast_forward
    )
    
    # Generate stock snapshots
    total_snapshots = generate_stock_snapshots(
        args.api,
        products,
        args.days,
        snapshot_interval,
        fast_forward
    )
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    # Generate pattern summary report
    popularity = generate_product_popularity(products)
    
    trending_up = [p for p in products if popularity[p['id']]['trend'] > 0.01]
    trending_down = [p for p in products if popularity[p['id']]['trend'] < -0.01]
    spike_products = [p for p in products if popularity[p['id']]['has_spike']]
    shortage_products = [p for p in products if popularity[p['id']]['has_shortage']]
    
    print(f"""
╔══════════════════════════════════════════════════════════╗
║     ✅ Backfill Complete!                                ║
╚══════════════════════════════════════════════════════════╝

Summary:
  - Time elapsed: {elapsed:.1f}s
  - Days generated: {args.days}
  - Density: {args.density}
  - Products: {len(products)}
  - Purchases uploaded: {total_purchases:,}
  - Snapshots uploaded: {total_snapshots:,}
  - Rate: {(total_purchases + total_snapshots) / elapsed:.0f} records/sec

📈 Generated Patterns:
  🔥 Trending UP: {len(trending_up)} products (growing 1-3% daily)""")
    
    if trending_up[:3]:
        for p in trending_up[:3]:
            print(f"     - {p['name']} ({p['category']})")
    
    print(f"""  📉 Trending DOWN: {len(trending_down)} products (declining 1-3% daily)""")
    if trending_down[:3]:
        for p in trending_down[:3]:
            print(f"     - {p['name']} ({p['category']})")
    
    print(f"""  ⚡ Spike Events: {len(spike_products)} products (3-8x sales surge)""")
    if spike_products[:3]:
        for p in spike_products:
            profile = popularity[p['id']]
            print(f"     - {p['name']} on day {profile['spike_day']} ({profile['spike_magnitude']:.1f}x normal)")
    
    print(f"""  🚫 Shortages: {len(shortage_products)} products (stockouts)""")
    if shortage_products[:3]:
        for p in shortage_products:
            profile = popularity[p['id']]
            print(f"     - {p['name']} days {profile['shortage_start']}-{profile['shortage_start'] + profile['shortage_duration']}")
    
    print(f"""
Next steps:
  1. View analytics at http://localhost:3000/analytics
  2. Check KPIs to see trending/shortage impacts
  3. Look for spike patterns in the AI Insights tab
  4. Start simulation to generate real-time data
    """)

if __name__ == "__main__":
    main()
