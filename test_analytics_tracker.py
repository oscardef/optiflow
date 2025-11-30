"""
Test Analytics Tracker
=======================
Quick test to verify analytics tracker functionality without running full simulation.
"""

import time
from datetime import datetime, timezone
from simulation.inventory import Product, Item
from simulation.analytics_tracker import AnalyticsTracker

# Create mock items
products = [
    Product("TEST-001", "Test Product 1", "Test"),
    Product("TEST-002", "Test Product 2", "Test"),
    Product("TEST-003", "Test Product 3", "Test"),
]

items = []
for i, product in enumerate(products):
    for j in range(3):  # 3 items per product
        item = Item(
            rfid_tag=f"TEST_{i}_{j}",
            product=product,
            x=100.0,
            y=100.0,
            missing=False
        )
        items.append(item)

print(f"Created {len(items)} test items")

# Initialize tracker with short snapshot interval for testing
tracker = AnalyticsTracker(
    api_url="http://localhost:8000",
    items=items,
    snapshot_interval=10  # 10 seconds for testing
)

print("\n🧪 Testing analytics tracker...")
print("   - Initial snapshot will be created in 10 seconds")
print("   - Simulating purchases by marking items as missing")
print("   - Press Ctrl+C to stop\n")

tracker.start()

try:
    # Simulate some purchases over time
    for i in range(5):
        time.sleep(3)
        
        # Mark an item as missing (simulating purchase)
        if i < len(items) and not items[i].missing:
            items[i].missing = True
            print(f"⚠️  Marked {items[i].product.name} as missing (purchase simulation)")
        
        # Show stats
        stats = tracker.get_stats()
        print(f"📊 Stats: {stats['snapshots_created']} snapshots, "
              f"{stats['purchases_recorded']} purchases, "
              f"{stats['purchases_queued']} queued")
    
    # Wait a bit more to ensure snapshot is captured
    print("\n⏳ Waiting for final snapshot...")
    time.sleep(12)
    
    stats = tracker.get_stats()
    print(f"\n✅ Test complete!")
    print(f"   Final stats: {stats['snapshots_created']} snapshots, "
          f"{stats['purchases_recorded']} purchases recorded")

except KeyboardInterrupt:
    print("\n⏹️  Test interrupted")
finally:
    tracker.stop()
    print("👋 Tracker stopped")
