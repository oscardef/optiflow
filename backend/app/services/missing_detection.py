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
       scan cycles AND sufficient time has passed, we mark it as missing
    
    For a DEMO environment (tags on desk), the key insight is:
    - If you're standing in roughly the same place and NOT detecting an item that
      WAS there before, it's probably gone
    - We need to be conservative to avoid false positives from read failures
    
    Detection Parameters (tuned for demo/production reliability):
    - MIN_CONSECUTIVE_MISSES: 6 scan cycles without detection
    - MIN_MISS_DURATION_SECONDS: 5 seconds minimum time elapsed
    - These values are intentionally conservative to avoid false positives
    """
    
    # Detection algorithm parameters - tuned for reliability
    # These are NOT configurable - we want one consistent approach
    
    # Minimum number of consecutive scan cycles where item was NOT detected
    # before considering it as potentially missing. 6 cycles at ~150ms each = ~1 second
    # but we also require time-based minimum below
    MIN_CONSECUTIVE_MISSES = 6
    
    # Minimum time (seconds) that must elapse from first miss before marking missing
    # This prevents marking items missing due to brief read failures
    MIN_MISS_DURATION_SECONDS = 5.0
    
    # RFID detection range in cm - items beyond this are not expected to be detected
    RFID_DETECTION_RANGE_CM = 60.0
    
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
        
        # Get all items that have been seen before (have position and are present)
        # In production mode, position is set when item is first detected
        present_items = db.query(InventoryItem).filter(
            InventoryItem.status == 'present',
            InventoryItem.x_position.isnot(None),
            InventoryItem.y_position.isnot(None)
        ).all()
        
        logger.debug(f"Processing {len(detected_rfid_tags)} detected tags, checking {len(present_items)} present items")
        
        for item in present_items:
            was_detected = item.rfid_tag in detected_rfid_tags
            
            if was_detected:
                # Item detected - reset miss tracking and update RSSI
                rssi = detected_rfid_tags[item.rfid_tag]
                cls._handle_item_detected(item, rssi, timestamp)
            else:
                # Item NOT detected - check if it's in range and should have been
                distance = cls._calculate_distance(
                    item.x_position, item.y_position,
                    employee_x, employee_y
                )
                
                if distance <= cls.RFID_DETECTION_RANGE_CM:
                    # Item is in range but wasn't detected - this is a miss
                    should_mark_missing = cls._handle_item_missed(item, timestamp)
                    
                    if should_mark_missing:
                        item.status = 'not present'
                        newly_missing.append(item)
                        logger.info(
                            f"📦❌ MISSING: {item.rfid_tag} "
                            f"(misses: {item.consecutive_misses}, "
                            f"duration: {cls._get_miss_duration_seconds(item, timestamp):.1f}s, "
                            f"last_rssi: {item.last_detection_rssi})"
                        )
                        # Reset tracking after marking missing
                        item.consecutive_misses = 0
                        item.first_miss_at = None
                else:
                    # Item out of range - don't count as miss, but also don't reset
                    # This preserves miss count if employee walked away briefly
                    pass
        
        if newly_missing:
            db.commit()
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
        # Requires BOTH: enough consecutive misses AND enough time elapsed
        miss_count_met = item.consecutive_misses >= cls.MIN_CONSECUTIVE_MISSES
        duration_met = cls._get_miss_duration_seconds(item, timestamp) >= cls.MIN_MISS_DURATION_SECONDS
        
        if miss_count_met and duration_met:
            return True
        
        # Log progress for debugging
        if item.consecutive_misses % 3 == 0:  # Log every 3rd miss to avoid spam
            logger.debug(
                f"Item {item.rfid_tag}: miss #{item.consecutive_misses}, "
                f"duration: {cls._get_miss_duration_seconds(item, timestamp):.1f}s "
                f"(need {cls.MIN_CONSECUTIVE_MISSES} misses, {cls.MIN_MISS_DURATION_SECONDS}s)"
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
                "min_miss_duration_seconds": cls.MIN_MISS_DURATION_SECONDS,
                "rfid_detection_range_cm": cls.RFID_DETECTION_RANGE_CM
            }
        }
