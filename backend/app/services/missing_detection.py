"""
Missing Item Detection Service
==============================
Mode-aware algorithm for detecting missing RFID items.

This service implements TWO different detection algorithms based on operating mode:

SIMULATION MODE (immediate):
- Items have fixed shelf positions that don't change
- When an item within range is NOT in the RFID packet, it's immediately marked missing
- No consecutive miss counting needed (simulation controls when items disappear)
- Simple and predictable for demo purposes

PRODUCTION MODE (tag-matching with safety):
- Item positions update to employee location when detected
- Uses consecutive miss counting to avoid false positives from RFID read failures
- Requires multiple consecutive misses before marking an item as missing
- Missing items are automatically restored when detected again

Key principles:
- An item with RSSI=0 or not in detection list is considered "not detected"
- An item with negative RSSI (e.g., -45 dBm) IS detected with that signal strength
- Production mode: Items marked missing after multiple misses (hardware reliability)
- Simulation mode: Items marked missing immediately when not detected (simulation controls disappearance)
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
    The simulation controls when items go missing via a time-based mechanism.
    Backend's job is to detect when simulation has marked an item as missing.
    
    Key insight: Simulation sends ALL items within range that are NOT missing.
    So if an item that WAS being detected (has recent last_seen_at) suddenly
    stops appearing in packets, the simulation has marked it as missing.
    
    We use consecutive miss counting but with a SHORT threshold since
    simulation is deterministic (no RFID read failures to account for).
    
    PRODUCTION MODE Algorithm:
    --------------------------
    Hardware can have intermittent read failures - need consecutive miss counting.
    Uses a LONGER threshold to avoid false positives from hardware glitches.
    """
    
    # === SIMULATION-SPECIFIC PARAMETERS ===
    # RFID detection range - SMALLER than simulation's range (75cm)
    # The simulation sends items within 75cm. We only mark items as missing
    # if they're within 50cm (well inside simulation's range). This avoids
    # false positives at the boundary due to floating point differences.
    RFID_DETECTION_RANGE_CM = 50.0  # 50cm - inner zone for reliable detection
    
    # === PRODUCTION-SPECIFIC PARAMETERS ===
    # Consecutive misses needed (longer - hardware can be flaky)
    MIN_CONSECUTIVE_MISSES_PRODUCTION = 6
    
    # Minimum items detected before checking for missing (production only)
    MIN_DETECTED_TO_CHECK_MISSING = 2
    
    # === SHARED PARAMETERS ===
    # Maximum items that can be marked missing per scan cycle
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
        SIMULATION MODE: INSTANT missing detection for previously-seen items.
        
        Workflow:
        1. Simulation pre-generates items throughout the store
        2. Employee walks through detecting items as present (sets last_seen_at)
        3. Simulation marks items as 'missing' internally every X seconds
        4. Simulation EXCLUDES missing items from packets sent to backend
        5. If a PREVIOUSLY-SEEN item is within range but NOT in packet, mark INSTANTLY missing
        
        Key insight: Only items with last_seen_at can be "discovered" as missing.
        Items that have never been detected cannot be known to be missing yet.
        """
        newly_missing = []
        detected_tags_set = set(detected_rfid_tags.keys())
        
        # Query present items that have been seen before (have last_seen_at)
        # These are items we KNOW about and can detect as missing
        present_items = db.query(InventoryItem).filter(
            InventoryItem.status == 'present',
            InventoryItem.x_position.isnot(None),
            InventoryItem.y_position.isnot(None),
            InventoryItem.last_seen_at.isnot(None)  # Only check previously-seen items!
        ).all()
        
        items_in_range = 0
        items_detected = 0
        
        # First, update any detected items (this sets last_seen_at for new detections)
        all_present_items = db.query(InventoryItem).filter(
            InventoryItem.status == 'present'
        ).all()
        
        for item in all_present_items:
            if item.rfid_tag in detected_tags_set:
                rssi = detected_rfid_tags[item.rfid_tag]
                cls._handle_item_detected(item, rssi, timestamp)
                items_detected += 1
        
        # Now check previously-seen items for missing status
        for item in present_items:
            tag_short = item.rfid_tag[-8:]
            
            # Skip if already detected above
            if item.rfid_tag in detected_tags_set:
                continue
            
            # Calculate distance to employee
            distance = cls._calculate_distance(
                item.x_position, item.y_position,
                employee_x, employee_y
            )
            
            if distance <= cls.RFID_DETECTION_RANGE_CM:
                # Item was seen before, is within range, but NOT in packet = MISSING
                items_in_range += 1
                
                # Rate limit: only mark 1 item missing per scan cycle
                if len(newly_missing) >= cls.MAX_MISSING_PER_SCAN:
                    continue
                
                item.status = 'not present'
                item.consecutive_misses = 0
                item.first_miss_at = None
                newly_missing.append(item)
                logger.info(f"   📦❌ {tag_short}: MISSING (not in packet at {distance:.1f}cm)")
        
        db.commit()
        
        # Periodic logging
        import random
        if random.random() < 0.05 or newly_missing:
            logger.info(f"🔍 [SIMULATION] Employee at ({employee_x:.1f}, {employee_y:.1f}): "
                       f"{len(detected_tags_set)} in packet, {items_in_range} previously-seen in range (not detected)")
        
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
                    if len(newly_missing) >= cls.MAX_MISSING_PER_SCAN:
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
                "detection_type": "immediate",
                "rfid_detection_range_cm": cls.RFID_DETECTION_RANGE_CM,
                "max_missing_per_scan": cls.MAX_MISSING_PER_SCAN
            }
        else:
            params = {
                "mode": "PRODUCTION",
                "detection_type": "consecutive_misses",
                "min_consecutive_misses": cls.MIN_CONSECUTIVE_MISSES_PRODUCTION,
                "min_detected_to_check_missing": cls.MIN_DETECTED_TO_CHECK_MISSING,
                "max_missing_per_scan": cls.MAX_MISSING_PER_SCAN
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
