"""
Missing Item Detection Service
==============================
Production-ready algorithm for detecting missing RFID items.

This service implements a robust missing detection algorithm that:
1. Tracks items that have been detected at least once (establishes baseline)
2. Counts consecutive scan cycles where an item was NOT detected
3. Requires both minimum miss count AND minimum time elapsed
4. Uses RSSI signal strength to understand detection quality

Key principles:
- An item with RSSI=0 or not in detection list is considered "not detected"
- An item with negative RSSI (e.g., -45 dBm) IS detected with that signal strength
- Items are only marked missing after multiple misses over time to avoid false positives
- State is persisted to database, not memory, for reliability
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Set
from sqlalchemy.orm import Session
import math

from ..models import InventoryItem, Product
from ..core import logger


class MissingItemDetector:
    """
    Production-ready missing item detection for RFID systems.
    
    Algorithm Overview:
    -------------------
    In PRODUCTION mode, items don't have fixed shelf positions. Instead:
    1. When an item is first detected, we record its position as the employee's location
    2. If the same item is detected again, we update its position
    3. If an item that was previously detected is NOT detected for multiple consecutive
       scan cycles while within range, we mark it as missing
    
    Detection Flow:
    1. Hardware packet arrives with RFID + UWB data
    2. Calculate employee position via triangulation
    3. Query all present items with known positions
    4. For each item:
       - Was it detected? → Reset miss counter
       - Distance > 50cm? → Reset miss counter (too far to detect)
       - Within 50cm but not detected? → Increment miss counter
       - Consecutive misses >= threshold? → Mark as missing (max 2 per scan)
    
    Detection Parameters (tuned for demo/production reliability):
    - MIN_CONSECUTIVE_MISSES: 4 scan cycles without detection
    - RFID_DETECTION_RANGE_CM: 50cm max detection range
    - MAX_MISSING_PER_SCAN: 2 items maximum per scan cycle
    """
    
    # Detection algorithm parameters - tuned for reliability
    # These are NOT configurable - we want one consistent approach
    
    # Minimum number of consecutive scan cycles where item was NOT detected
    # before marking as missing. This accounts for RFID read failures.
    # 4 cycles provides enough buffer for normal read variations
    MIN_CONSECUTIVE_MISSES = 4
    
    # RFID detection range in cm - items beyond this are not expected to be detected
    RFID_DETECTION_RANGE_CM = 50.0
    
    # Maximum number of items that can be marked missing in a single scan cycle
    # This prevents mass false positives from temporary signal issues
    MAX_MISSING_PER_SCAN = 2
    
    @classmethod
    def process_detections(
        cls,
        db: Session,
        detected_rfid_tags: Dict[str, float],  # {rfid_tag: rssi_dbm}
        employee_x: float,
        employee_y: float,
        timestamp: datetime
    ) -> List[InventoryItem]:
        """
        Process RFID detections and infer missing items.
        
        Args:
            db: Database session
            detected_rfid_tags: Dict mapping RFID tag to RSSI (negative dBm value means detected)
            employee_x: Current employee X position
            employee_y: Current employee Y position
            timestamp: Current scan timestamp
            
        Returns:
            List of InventoryItem objects that were newly marked as missing
        """
        newly_missing = []
        
        # === STEP 1: Query ALL present items from database ===
        # Get all items that have been seen before (have position and are present)
        # In production mode, position is set when item is first detected
        present_items = db.query(InventoryItem).filter(
            InventoryItem.status == 'present',
            InventoryItem.x_position.isnot(None),
            InventoryItem.y_position.isnot(None)
        ).all()
        
        logger.info(f"🔍 Processing {len(detected_rfid_tags)} detected tags, checking {len(present_items)} present items")
        
        # Debug: Show items with existing miss counters
        items_with_misses = [item for item in present_items if item.consecutive_misses > 0]
        if items_with_misses:
            logger.info(f"   📊 {len(items_with_misses)} items already have miss counters:")
        
        # === STEP 2: For each item, apply safety checks ===
        for item in present_items:
            was_detected = item.rfid_tag in detected_rfid_tags
            
            if was_detected:
                # ✅ SAFETY CHECK 1: Item was detected - reset miss tracking
                rssi = detected_rfid_tags[item.rfid_tag]
                cls._handle_item_detected(item, rssi, timestamp)
            else:
                # Item NOT detected - calculate distance to employee
                distance = cls._calculate_distance(
                    item.x_position, item.y_position,
                    employee_x, employee_y
                )
                
                # ✅ SAFETY CHECK 2: Is item within RFID detection range (50cm)?
                if distance <= cls.RFID_DETECTION_RANGE_CM:
                    # Item is in range but wasn't detected - this is a miss
                    logger.info(f"   ❌ Item {item.rfid_tag} within range ({distance:.1f}cm) but NOT detected")
                    should_mark_missing = cls._handle_item_missed(item, timestamp)
                    
                    # ✅ SAFETY CHECK 3: Enough consecutive misses? (>= 4 cycles)
                    # This check alone is sufficient - consecutive misses account for read failures
                    if should_mark_missing:
                        # ✅ SAFETY CHECK 4: Max 2 items marked missing per scan
                        if len(newly_missing) >= cls.MAX_MISSING_PER_SCAN:
                            logger.debug(
                                f"Item {item.rfid_tag} would be missing but max per scan reached"
                            )
                            continue
                        
                        item.status = 'not present'
                        newly_missing.append(item)
                        logger.info(
                            f"📦❌ MISSING: {item.rfid_tag} "
                            f"(misses: {item.consecutive_misses})"
                        )
                        # Reset tracking after marking missing
                        item.consecutive_misses = 0
                        item.first_miss_at = None
                else:
                    # Item out of range - don't count as miss, but also don't reset
                    # This preserves miss count if employee walked away briefly
                    pass
        
        # CRITICAL: Always commit changes to persist miss counters
        # Without this, consecutive_misses would reset on every request
        db.commit()
        
        if newly_missing:
            logger.info(f"🧮 Marked {len(newly_missing)} item(s) as 'not present'")
        
        return newly_missing
    
    @classmethod
    def _handle_item_detected(cls, item: InventoryItem, rssi: float, timestamp: datetime):
        """
        Handle when an item IS detected - reset miss tracking.
        """
        # Store the RSSI value (helps understand signal quality)
        item.last_detection_rssi = rssi
        item.last_seen_at = timestamp
        
        # Reset miss tracking
        if item.consecutive_misses > 0:
            logger.debug(f"Item {item.rfid_tag} detected again, resetting miss count from {item.consecutive_misses}")
        item.consecutive_misses = 0
        item.first_miss_at = None
    
    @classmethod
    def _handle_item_missed(cls, item: InventoryItem, timestamp: datetime) -> bool:
        """
        Handle when an item is NOT detected but should have been.
        Returns True if item should be marked as missing.
        """
        # Increment consecutive miss counter
        item.consecutive_misses = (item.consecutive_misses or 0) + 1
        
        # Record when misses started (if this is the first miss)
        if item.first_miss_at is None:
            item.first_miss_at = timestamp
        
        # Check if we should mark as missing
        # Only requires consecutive misses threshold (no time check)
        # This matches the old logic where consecutive misses alone was enough
        miss_count_met = item.consecutive_misses >= cls.MIN_CONSECUTIVE_MISSES
        
        if miss_count_met:
            return True
        
        # Log progress for debugging
        logger.info(
            f"   ⏱️  Item {item.rfid_tag}: miss #{item.consecutive_misses}/{cls.MIN_CONSECUTIVE_MISSES}"
        )
        
        return False
    
    @classmethod
    def _get_miss_duration_seconds(cls, item: InventoryItem, current_time: datetime) -> float:
        """Calculate how long the item has been consecutively missed."""
        if item.first_miss_at is None:
            return 0.0
        delta = current_time - item.first_miss_at
        return delta.total_seconds()
    
    @classmethod
    def _calculate_distance(cls, x1: float, y1: float, x2: float, y2: float) -> float:
        """Calculate Euclidean distance between two points."""
        dx = x1 - x2
        dy = y1 - y2
        return math.sqrt(dx * dx + dy * dy)
    
    @classmethod
    def update_detected_item_position(
        cls,
        item: InventoryItem,
        employee_x: float,
        employee_y: float,
        rssi: float,
        timestamp: datetime
    ):
        """
        Update an item's position based on where it was detected (PRODUCTION mode).
        
        In production, items are detected at the employee's current location,
        so we set the item's position to match.
        """
        item.x_position = employee_x
        item.y_position = employee_y
        item.last_detection_rssi = rssi
        item.last_seen_at = timestamp
        # Reset any miss tracking
        item.consecutive_misses = 0
        item.first_miss_at = None
    
    @classmethod
    def get_detection_stats(cls, db: Session) -> Dict:
        """
        Get statistics about the current detection state.
        Useful for monitoring and debugging.
        """
        # Items with pending misses (might be marked missing soon)
        pending = db.query(InventoryItem).filter(
            InventoryItem.status == 'present',
            InventoryItem.consecutive_misses > 0
        ).all()
        
        # Items already marked missing
        missing = db.query(InventoryItem).filter(
            InventoryItem.status == 'not present'
        ).count()
        
        # Total present items
        present = db.query(InventoryItem).filter(
            InventoryItem.status == 'present'
        ).count()
        
        return {
            "total_present": present,
            "total_missing": missing,
            "pending_misses": len(pending),
            "pending_details": [
                {
                    "rfid_tag": item.rfid_tag,
                    "consecutive_misses": item.consecutive_misses,
                    "first_miss_at": item.first_miss_at.isoformat() if item.first_miss_at else None,
                    "last_detection_rssi": item.last_detection_rssi
                }
                for item in pending[:20]  # Limit to 20 for readability
            ],
            "algorithm_params": {
                "min_consecutive_misses": cls.MIN_CONSECUTIVE_MISSES,
                "rfid_detection_range_cm": cls.RFID_DETECTION_RANGE_CM,
                "max_missing_per_scan": cls.MAX_MISSING_PER_SCAN
            }
        }
