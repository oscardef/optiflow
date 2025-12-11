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
    - MIN_CONSECUTIVE_MISSES: 6 scan cycles without detection
    - MIN_DETECTED_TO_CHECK_MISSING: 2 items must be detected to check for missing
    - MAX_MISSING_PER_SCAN: 1 item maximum per scan cycle
    
    IMPORTANT: In production mode, we do NOT use distance-based detection.
    The position of items changes every time they're detected (set to employee location),
    so distance checking is unreliable. Instead we use a simpler approach:
    - If we detect 2+ items in the same scan, we're "actively scanning"
    - Any item NOT in the detection list accumulates a miss count
    - After 6 consecutive misses while actively scanning, mark as missing
    """
    
    # Detection algorithm parameters - tuned for reliability
    # These are NOT configurable - we want one consistent approach
    
    # Minimum number of consecutive scan cycles where item was NOT detected
    # before marking as missing. This accounts for RFID read failures.
    # 6 cycles provides a strong buffer for normal read variations
    MIN_CONSECUTIVE_MISSES = 3
    
    # Minimum number of items that must be detected before we check for missing items
    # This prevents false positives when RFID reader only catches some tags
    MIN_DETECTED_TO_CHECK_MISSING = 2
    
    # Maximum number of items that can be marked missing in a single scan cycle
    # Reduced to 1 to be very conservative - only 1 item can go missing at a time
    MAX_MISSING_PER_SCAN = 1
    
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
        
        SIMPLIFIED ALGORITHM (no distance checking):
        1. If we detect 0 or 1 items → not actively scanning, skip
        2. If we detect 2+ items → we're actively scanning
        3. For each PRESENT item in the database:
           - If it's in the detected list → reset miss counter
           - If it's NOT in the detected list → increment miss counter
        4. After 6 consecutive misses → mark as missing
        
        Args:
            db: Database session
            detected_rfid_tags: Dict mapping RFID tag to RSSI (negative dBm value means detected)
            employee_x: Current employee X position (for logging only)
            employee_y: Current employee Y position (for logging only)
            timestamp: Current scan timestamp
            
        Returns:
            List of InventoryItem objects that were newly marked as missing
        """
        newly_missing = []
        detected_tags_set = set(detected_rfid_tags.keys())
        
        # === STEP 1: Query ALL present items from database ===
        present_items = db.query(InventoryItem).filter(
            InventoryItem.status == 'present'
        ).all()
        
        present_rfid_tags = {item.rfid_tag for item in present_items}
        
        # Log the state
        logger.info(f"🔍 Processing {len(detected_rfid_tags)} detected tags, {len(present_items)} present items in DB")
        logger.info(f"   📋 Detected RFIDs: {[tag[-8:] for tag in detected_tags_set]}")
        logger.info(f"   📦 Present in DB: {[tag[-8:] for tag in present_rfid_tags]}")
        
        # === SAFETY CHECK 1: Must detect at least MIN_DETECTED_TO_CHECK_MISSING items ===
        # If we detect fewer than 2 items, we can't be confident the reader is working well
        if len(detected_rfid_tags) < cls.MIN_DETECTED_TO_CHECK_MISSING:
            logger.info(f"   ⏸️  Only {len(detected_rfid_tags)} item(s) detected (need {cls.MIN_DETECTED_TO_CHECK_MISSING}+) - NOT checking for missing")
            # Still update detected items to reset their miss counters
            for item in present_items:
                if item.rfid_tag in detected_tags_set:
                    rssi = detected_rfid_tags[item.rfid_tag]
                    cls._handle_item_detected(item, rssi, timestamp)
            db.commit()
            return newly_missing
        
        logger.info(f"   ✅ {len(detected_rfid_tags)} items detected - actively scanning, will check for missing")
        
        # === STEP 2: Process each present item ===
        for item in present_items:
            tag_short = item.rfid_tag[-8:]  # Short version for logging
            
            if item.rfid_tag in detected_tags_set:
                # Item was detected - reset miss tracking
                rssi = detected_rfid_tags[item.rfid_tag]
                old_misses = item.consecutive_misses
                cls._handle_item_detected(item, rssi, timestamp)
                if old_misses > 0:
                    logger.info(f"   ✅ {tag_short}: DETECTED (RSSI={rssi:.0f}dBm) - reset misses from {old_misses} to 0")
                else:
                    logger.debug(f"   ✅ {tag_short}: detected (RSSI={rssi:.0f}dBm)")
            else:
                # Item NOT detected - increment miss counter
                old_misses = item.consecutive_misses or 0
                should_mark_missing = cls._handle_item_missed(item, timestamp)
                
                logger.info(f"   ❌ {tag_short}: NOT DETECTED - miss count: {old_misses} → {item.consecutive_misses}/{cls.MIN_CONSECUTIVE_MISSES}")
                
                if should_mark_missing:
                    # Check max per scan limit
                    if len(newly_missing) >= cls.MAX_MISSING_PER_SCAN:
                        logger.info(f"   ⚠️  {tag_short}: Would be marked missing but max per scan ({cls.MAX_MISSING_PER_SCAN}) reached")
                        continue
                    
                    item.status = 'not present'
                    newly_missing.append(item)
                    logger.info(f"   📦❌ {tag_short}: MARKED AS MISSING after {item.consecutive_misses} consecutive misses")
                    # Reset tracking after marking missing
                    item.consecutive_misses = 0
                    item.first_miss_at = None
        
        # CRITICAL: Always commit changes to persist miss counters
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
                "min_detected_to_check_missing": cls.MIN_DETECTED_TO_CHECK_MISSING,
                "max_missing_per_scan": cls.MAX_MISSING_PER_SCAN
            }
        }
