"""
Missing Item Detection Service
==============================
Mode-aware algorithm for detecting missing RFID items.

This service implements TWO different detection algorithms based on operating mode:

SIMULATION MODE (distance-based):
- Items have fixed shelf positions that don't change
- Only items within RFID detection range (50cm) of employee can be marked missing
- Employee walks around the store, and items near their path are checked
- Prevents random items across the store from being marked missing

PRODUCTION MODE (tag-matching):
- Item positions update to employee location when detected
- Distance checking doesn't work (all detected items are at same location)
- Uses simpler tag-matching: if item in detection list = present
- Missing items are automatically restored when detected again

Key principles:
- An item with RSSI=0 or not in detection list is considered "not detected"
- An item with negative RSSI (e.g., -45 dBm) IS detected with that signal strength
- Items are only marked missing after multiple misses to avoid false positives
- State is persisted to database, not memory, for reliability
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Set
from sqlalchemy.orm import Session
import math

from ..models import InventoryItem, Product
from ..core import logger
from ..config import config_state, ConfigMode


class MissingItemDetector:
    """
    Mode-aware missing item detection for RFID systems.
    
    SIMULATION MODE Algorithm:
    --------------------------
    Items have fixed shelf positions. Employee walks around the store.
    1. Hardware packet arrives with RFID + UWB data
    2. Calculate employee position via triangulation
    3. Query all present items with known positions
    4. For each item:
       - Was it detected? → Reset miss counter
       - Distance > RFID_DETECTION_RANGE? → Don't check (out of range)
       - Within range but not detected? → Increment miss counter
       - Consecutive misses >= threshold? → Mark as missing
    
    PRODUCTION MODE Algorithm:
    --------------------------
    Items positions update to employee location when detected.
    1. Hardware packet arrives with RFID + UWB data
    2. Check if we're "actively scanning" (detected 2+ items)
    3. For each present item in database:
       - If in detection list → Reset miss counter
       - If NOT in detection list → Increment miss counter
       - After threshold misses → Mark as missing
    """
    
    # === SHARED PARAMETERS ===
    # Minimum number of consecutive scan cycles where item was NOT detected
    MIN_CONSECUTIVE_MISSES_SIMULATION = 4  # For simulation mode
    MIN_CONSECUTIVE_MISSES_PRODUCTION = 6  # For production mode (more conservative)
    
    # Maximum number of items that can be marked missing in a single scan cycle
    MAX_MISSING_PER_SCAN_SIMULATION = 2  # Simulation can handle more
    MAX_MISSING_PER_SCAN_PRODUCTION = 1  # Production is more conservative
    
    # === SIMULATION-SPECIFIC PARAMETERS ===
    # RFID detection range in cm - items beyond this are not expected to be detected
    RFID_DETECTION_RANGE_CM = 50.0
    
    # === PRODUCTION-SPECIFIC PARAMETERS ===
    # Minimum number of items that must be detected before we check for missing items
    # This prevents false positives when RFID reader only catches some tags
    MIN_DETECTED_TO_CHECK_MISSING = 2
    
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
        Dispatches to mode-specific algorithm.
        """
        current_mode = config_state.mode
        
        if current_mode == ConfigMode.SIMULATION:
            return cls._process_detections_simulation(
                db, detected_rfid_tags, employee_x, employee_y, timestamp
            )
        else:
            return cls._process_detections_production(
                db, detected_rfid_tags, employee_x, employee_y, timestamp
            )
    
    @classmethod
    def _process_detections_simulation(
        cls,
        db: Session,
        detected_rfid_tags: Dict[str, float],
        employee_x: float,
        employee_y: float,
        timestamp: datetime
    ) -> List[InventoryItem]:
        """
        SIMULATION MODE: Distance-based missing detection.
        
        Only items within RFID_DETECTION_RANGE_CM of the employee can be 
        marked as missing. This prevents random items across the store
        from being flagged when the employee is nowhere near them.
        """
        newly_missing = []
        detected_tags_set = set(detected_rfid_tags.keys())
        
        # Query all present items WITH positions (simulation items have fixed positions)
        present_items = db.query(InventoryItem).filter(
            InventoryItem.status == 'present',
            InventoryItem.x_position.isnot(None),
            InventoryItem.y_position.isnot(None)
        ).all()
        
        logger.info(f"🔍 [SIMULATION] Processing {len(detected_rfid_tags)} detected tags, {len(present_items)} present items")
        logger.info(f"   📍 Employee at: ({employee_x:.1f}, {employee_y:.1f})")
        
        # Find items within detection range
        items_in_range = []
        for item in present_items:
            distance = cls._calculate_distance(
                item.x_position, item.y_position,
                employee_x, employee_y
            )
            if distance <= cls.RFID_DETECTION_RANGE_CM:
                items_in_range.append((item, distance))
        
        logger.info(f"   📡 {len(items_in_range)} items within {cls.RFID_DETECTION_RANGE_CM}cm detection range")
        
        # Process ALL present items
        for item in present_items:
            tag_short = item.rfid_tag[-8:]
            
            # Calculate distance to employee
            distance = cls._calculate_distance(
                item.x_position, item.y_position,
                employee_x, employee_y
            )
            
            if item.rfid_tag in detected_tags_set:
                # Item was detected - reset miss tracking
                rssi = detected_rfid_tags[item.rfid_tag]
                old_misses = item.consecutive_misses or 0
                cls._handle_item_detected(item, rssi, timestamp)
                if old_misses > 0:
                    logger.info(f"   ✅ {tag_short}: DETECTED at {distance:.1f}cm (RSSI={rssi:.0f}dBm) - reset misses from {old_misses} to 0")
            elif distance <= cls.RFID_DETECTION_RANGE_CM:
                # Item is within range but NOT detected - this is a miss
                old_misses = item.consecutive_misses or 0
                should_mark_missing = cls._handle_item_missed_simulation(item, timestamp)
                
                logger.info(f"   ❌ {tag_short}: NOT DETECTED at {distance:.1f}cm - miss count: {old_misses} → {item.consecutive_misses}/{cls.MIN_CONSECUTIVE_MISSES_SIMULATION}")
                
                if should_mark_missing:
                    if len(newly_missing) >= cls.MAX_MISSING_PER_SCAN_SIMULATION:
                        logger.info(f"   ⚠️  {tag_short}: Would be marked missing but max per scan reached")
                        continue
                    
                    item.status = 'not present'
                    newly_missing.append(item)
                    logger.info(f"   📦❌ {tag_short}: MARKED AS MISSING after {item.consecutive_misses} consecutive misses")
                    item.consecutive_misses = 0
                    item.first_miss_at = None
            else:
                # Item is out of range - don't count as miss (employee not near it)
                # But also don't reset miss counter (preserve state for when employee returns)
                pass
        
        db.commit()
        
        if newly_missing:
            logger.info(f"🧮 [SIMULATION] Marked {len(newly_missing)} item(s) as 'not present'")
        
        return newly_missing
    
    @classmethod
    def _process_detections_production(
        cls,
        db: Session,
        detected_rfid_tags: Dict[str, float],
        employee_x: float,
        employee_y: float,
        timestamp: datetime
    ) -> List[InventoryItem]:
        """
        PRODUCTION MODE: Tag-matching based missing detection.
        
        In production, item positions update to employee location when detected,
        so distance checking is unreliable. Instead, we use simple tag matching:
        - If we detect 2+ items, we're "actively scanning"
        - Any present item NOT in the detection list accumulates misses
        - After threshold misses, mark as missing
        """
        newly_missing = []
        detected_tags_set = set(detected_rfid_tags.keys())
        
        # Query ALL present items (no position filter - positions change in production)
        present_items = db.query(InventoryItem).filter(
            InventoryItem.status == 'present'
        ).all()
        
        present_rfid_tags = {item.rfid_tag for item in present_items}
        
        logger.info(f"🔍 [PRODUCTION] Processing {len(detected_rfid_tags)} detected tags, {len(present_items)} present items")
        logger.info(f"   📋 Detected RFIDs: {[tag[-8:] for tag in detected_tags_set]}")
        logger.info(f"   📦 Present in DB: {[tag[-8:] for tag in present_rfid_tags]}")
        
        # SAFETY CHECK: Must detect at least MIN_DETECTED_TO_CHECK_MISSING items
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
        
        # Process each present item
        for item in present_items:
            tag_short = item.rfid_tag[-8:]
            
            if item.rfid_tag in detected_tags_set:
                # Item was detected - reset miss tracking
                rssi = detected_rfid_tags[item.rfid_tag]
                old_misses = item.consecutive_misses or 0
                cls._handle_item_detected(item, rssi, timestamp)
                if old_misses > 0:
                    logger.info(f"   ✅ {tag_short}: DETECTED (RSSI={rssi:.0f}dBm) - reset misses from {old_misses} to 0")
            else:
                # Item NOT detected - increment miss counter
                old_misses = item.consecutive_misses or 0
                should_mark_missing = cls._handle_item_missed_production(item, timestamp)
                
                logger.info(f"   ❌ {tag_short}: NOT DETECTED - miss count: {old_misses} → {item.consecutive_misses}/{cls.MIN_CONSECUTIVE_MISSES_PRODUCTION}")
                
                if should_mark_missing:
                    if len(newly_missing) >= cls.MAX_MISSING_PER_SCAN_PRODUCTION:
                        logger.info(f"   ⚠️  {tag_short}: Would be marked missing but max per scan reached")
                        continue
                    
                    item.status = 'not present'
                    newly_missing.append(item)
                    logger.info(f"   📦❌ {tag_short}: MARKED AS MISSING after {item.consecutive_misses} consecutive misses")
                    item.consecutive_misses = 0
                    item.first_miss_at = None
        
        db.commit()
        
        if newly_missing:
            logger.info(f"🧮 [PRODUCTION] Marked {len(newly_missing)} item(s) as 'not present'")
        
        return newly_missing
    
    @classmethod
    def _handle_item_detected(cls, item: InventoryItem, rssi: float, timestamp: datetime):
        """Handle when an item IS detected - reset miss tracking."""
        item.last_detection_rssi = rssi
        item.last_seen_at = timestamp
        item.consecutive_misses = 0
        item.first_miss_at = None
    
    @classmethod
    def _handle_item_missed_simulation(cls, item: InventoryItem, timestamp: datetime) -> bool:
        """
        Handle missed item in SIMULATION mode.
        Returns True if item should be marked as missing.
        """
        item.consecutive_misses = (item.consecutive_misses or 0) + 1
        if item.first_miss_at is None:
            item.first_miss_at = timestamp
        
        return item.consecutive_misses >= cls.MIN_CONSECUTIVE_MISSES_SIMULATION
    
    @classmethod
    def _handle_item_missed_production(cls, item: InventoryItem, timestamp: datetime) -> bool:
        """
        Handle missed item in PRODUCTION mode.
        Returns True if item should be marked as missing.
        """
        item.consecutive_misses = (item.consecutive_misses or 0) + 1
        if item.first_miss_at is None:
            item.first_miss_at = timestamp
        
        return item.consecutive_misses >= cls.MIN_CONSECUTIVE_MISSES_PRODUCTION
    
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
        In production, items are detected at the employee's current location.
        """
        item.x_position = employee_x
        item.y_position = employee_y
        item.last_detection_rssi = rssi
        item.last_seen_at = timestamp
        item.consecutive_misses = 0
        item.first_miss_at = None
    
    @classmethod
    def get_detection_stats(cls, db: Session) -> Dict:
        """Get statistics about the current detection state."""
        current_mode = config_state.mode
        
        pending = db.query(InventoryItem).filter(
            InventoryItem.status == 'present',
            InventoryItem.consecutive_misses > 0
        ).all()
        
        missing = db.query(InventoryItem).filter(
            InventoryItem.status == 'not present'
        ).count()
        
        present = db.query(InventoryItem).filter(
            InventoryItem.status == 'present'
        ).count()
        
        # Mode-specific parameters
        if current_mode == ConfigMode.SIMULATION:
            params = {
                "mode": "SIMULATION",
                "min_consecutive_misses": cls.MIN_CONSECUTIVE_MISSES_SIMULATION,
                "rfid_detection_range_cm": cls.RFID_DETECTION_RANGE_CM,
                "max_missing_per_scan": cls.MAX_MISSING_PER_SCAN_SIMULATION
            }
        else:
            params = {
                "mode": "PRODUCTION",
                "min_consecutive_misses": cls.MIN_CONSECUTIVE_MISSES_PRODUCTION,
                "min_detected_to_check_missing": cls.MIN_DETECTED_TO_CHECK_MISSING,
                "max_missing_per_scan": cls.MAX_MISSING_PER_SCAN_PRODUCTION
            }
        
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
                for item in pending[:20]
            ],
            "algorithm_params": params
        }
