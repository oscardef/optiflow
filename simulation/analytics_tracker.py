"""
Real-Time Analytics Tracker
============================
Captures stock snapshots and purchase events during simulation.
"""

import threading
import time
import requests
from datetime import datetime, timezone
from typing import List, Dict
from collections import defaultdict

from .inventory import Item


class AnalyticsTracker:
    """Tracks analytics data in real-time during simulation"""
    
    def __init__(self, api_url: str, items: List[Item], snapshot_interval: int = 3600):
        """
        Initialize analytics tracker
        
        Args:
            api_url: Backend API URL
            items: List of inventory items to track
            snapshot_interval: Seconds between snapshots (default: 3600 = 1 hour)
        """
        self.api_url = api_url
        self.items = items
        self.snapshot_interval = snapshot_interval
        
        # Threading controls
        self.running = False
        self.thread = None
        
        # Track last known state to detect changes
        self.last_item_states = {}  # rfid_tag -> missing status
        self.purchase_queue = []  # Queue of purchases to upload
        
        # Statistics
        self.snapshots_created = 0
        self.purchases_recorded = 0
        
        print(f"📊 Analytics tracker initialized (snapshots every {snapshot_interval}s)")
    
    def start(self):
        """Start background tracking thread"""
        if self.running:
            print("⚠️  Analytics tracker already running")
            return
        
        # Initialize last_item_states with current item states
        # This ensures we only detect NEW transitions, not existing states
        for item in self.items:
            self.last_item_states[item.rfid_tag] = item.missing
        
        self.running = True
        self.thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self.thread.start()
        print("✅ Analytics tracker started")
    
    def stop(self):
        """Stop background tracking thread"""
        if not self.running:
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        
        # Upload any remaining purchases
        if self.purchase_queue:
            self._upload_purchases()
        
        print(f"📊 Analytics tracker stopped (snapshots: {self.snapshots_created}, purchases: {self.purchases_recorded})")
    
    def reset_state(self):
        """
        Reset tracking state to allow fresh purchase detection.
        
        Call this after clearing analytics data to ensure purchases can be 
        detected again from the current item states. This clears the memory
        of previous item states, so transitions from present->missing will
        be detected as new purchases.
        """
        self.last_item_states.clear()
        self.purchase_queue.clear()
        self.snapshots_created = 0
        self.purchases_recorded = 0
        print("🔄 Analytics tracker state reset - ready for fresh tracking")
    
    def _tracking_loop(self):
        """Main tracking loop (runs in background thread)"""
        last_snapshot_time = time.time()
        check_interval = 1  # Check for changes every second
        
        while self.running:
            current_time = time.time()
            
            # Check for items that went missing (purchases)
            self._check_for_purchases()
            
            # Create snapshot if interval elapsed
            if current_time - last_snapshot_time >= self.snapshot_interval:
                self._create_snapshot()
                last_snapshot_time = current_time
            
            # Sleep briefly to avoid CPU spinning
            time.sleep(check_interval)
    
    def _check_for_purchases(self):
        """Check if any items went missing (indicating a purchase)"""
        for item in self.items:
            last_missing = self.last_item_states.get(item.rfid_tag, False)
            
            # Detect transition from present -> missing
            if not last_missing and item.missing:
                purchase_event = {
                    'product_id': item.product.sku,  # Use SKU as product identifier
                    'purchased_at': datetime.now(timezone.utc).isoformat()
                }
                self.purchase_queue.append(purchase_event)
                self.purchases_recorded += 1
                
                # Upload purchases in batches of 10 or every 30 seconds
                if len(self.purchase_queue) >= 10:
                    self._upload_purchases()
            
            # Update state tracking
            self.last_item_states[item.rfid_tag] = item.missing
    
    def _create_snapshot(self):
        """Create a stock snapshot for all products"""
        try:
            # Count items by product SKU
            product_counts = defaultdict(lambda: {'present': 0, 'missing': 0})
            
            for item in self.items:
                if item.missing:
                    product_counts[item.product.sku]['missing'] += 1
                else:
                    product_counts[item.product.sku]['present'] += 1
            
            # Build snapshot data
            snapshots = []
            timestamp = datetime.now(timezone.utc).isoformat()
            
            for product_sku, counts in product_counts.items():
                snapshots.append({
                    'product_id': product_sku,
                    'timestamp': timestamp,
                    'present_count': counts['present'],
                    'missing_count': counts['missing']
                })
            
            # Upload snapshot
            response = requests.post(
                f"{self.api_url}/analytics/bulk/snapshots",
                json=snapshots,
                timeout=10
            )
            
            if response.status_code == 200:
                self.snapshots_created += 1
                print(f"📸 Snapshot #{self.snapshots_created} created ({len(snapshots)} products)")
            else:
                print(f"⚠️  Snapshot upload failed: {response.status_code}")
        
        except Exception as e:
            print(f"⚠️  Error creating snapshot: {e}")
    
    def _upload_purchases(self):
        """Upload queued purchase events to backend"""
        if not self.purchase_queue:
            return
        
        try:
            # Get product IDs from backend (need numeric IDs, not SKUs)
            # First, get all products to map SKU -> ID
            products_response = requests.get(f"{self.api_url}/products", timeout=5)
            
            if products_response.status_code != 200:
                print(f"⚠️  Could not fetch products for purchase mapping")
                return
            
            products = products_response.json()
            sku_to_id = {p['sku']: p['id'] for p in products}
            
            # Convert SKUs to IDs in purchase events
            mapped_purchases = []
            for purchase in self.purchase_queue:
                product_id = sku_to_id.get(purchase['product_id'])
                if product_id:
                    mapped_purchases.append({
                        'product_id': product_id,
                        'purchased_at': purchase['purchased_at']
                    })
            
            if not mapped_purchases:
                print("⚠️  No valid purchases to upload")
                self.purchase_queue.clear()
                return
            
            # Upload purchases
            response = requests.post(
                f"{self.api_url}/analytics/bulk/purchases",
                json=mapped_purchases,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"💰 Uploaded {len(mapped_purchases)} purchase events")
                self.purchase_queue.clear()
            else:
                print(f"⚠️  Purchase upload failed: {response.status_code}")
        
        except Exception as e:
            print(f"⚠️  Error uploading purchases: {e}")
    
    def get_stats(self) -> Dict:
        """Get current tracking statistics"""
        return {
            'snapshots_created': self.snapshots_created,
            'purchases_recorded': self.purchases_recorded,
            'purchases_queued': len(self.purchase_queue),
            'running': self.running
        }
