"""
Simple Detection State Machine

Implements a simple state machine to track platform state:
- EMPTY: No item on platform
- ITEM_PRESENT: Item detected and present on platform

Duplicate prevention is handled by checking if item already exists in the bill.
"""

from enum import Enum
from typing import Optional, Tuple
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)


class PlatformState(Enum):
    """Platform state enumeration."""
    EMPTY = "empty"
    ITEM_PRESENT = "item_present"


class DetectionState:
    """
    Simple state machine for detection tracking.
    
    Tracks platform state (EMPTY/ITEM_PRESENT) based on detections.
    Duplicate prevention is handled by checking the bill, not by session logic.
    """
    
    # Time-based removal delay (seconds)
    ITEM_REMOVAL_DELAY: float = 1.5  # 1.5 seconds
    
    def __init__(self):
        # State machine
        self.state: PlatformState = PlatformState.EMPTY
        self.current_item: Optional[Tuple[str, float]] = None  # (item_name, weight)
        
        # Time-based presence tracking
        self.last_seen_time: float = 0.0  # Timestamp of last valid detection
        
        # Detection tracking
        self.min_weight_threshold: float = 100.0  # Minimum weight to consider item present
        
    def process_detection(self, detected_item_name: str, weight: float, confidence: float) -> Tuple[bool, bool]:
        """
        Process a detection and determine if item should be considered for billing.
        
        State machine logic:
        1. Check time-based removal first (ITEM_PRESENT -> EMPTY if last_seen_time expired)
        2. On valid detection: update last_seen_time
        3. Transition EMPTY -> ITEM_PRESENT when new item detected
        4. Return should_add_to_bill=True when transitioning from EMPTY to ITEM_PRESENT
        5. Duplicate prevention is handled by checking if item exists in bill (not here)
        
        Args:
            detected_item_name: Name of detected item
            weight: Weight of item (grams)
            confidence: Detection confidence (0.0-1.0)
        
        Returns:
            Tuple[bool, bool]: (state_changed, should_add_to_bill)
                - state_changed: True if state machine state changed
                - should_add_to_bill: True when transitioning from EMPTY to ITEM_PRESENT
        """
        current_time = time.time()
        previous_state = self.state
        timestamp_str = datetime.fromtimestamp(current_time).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        # Step 1: Check time-based removal (ITEM_PRESENT -> EMPTY)
        # Transition to EMPTY only if enough time has passed since last valid detection
        if self.state == PlatformState.ITEM_PRESENT:
            time_since_last_seen = current_time - self.last_seen_time
            if time_since_last_seen > self.ITEM_REMOVAL_DELAY:
                # Transition: ITEM_PRESENT -> EMPTY
                item_name, _ = self.current_item
                
                logger.info(f"🔄 [{timestamp_str}] State transition: ITEM_PRESENT -> EMPTY")
                logger.info(f"📤 [{timestamp_str}] Item '{item_name}' removed from platform (time since last seen: {time_since_last_seen:.3f}s > {self.ITEM_REMOVAL_DELAY}s)")
                print(f"📤 [{timestamp_str}] Item '{item_name}' removed - Platform is now EMPTY (timeout: {time_since_last_seen:.3f}s)")
                
                self.state = PlatformState.EMPTY
                self.current_item = None
                self.last_seen_time = 0.0
        
        # Step 2: Reject invalid detections
        if detected_item_name == "unknown" or confidence < 0.5:
            # Invalid detection - don't update last_seen_time, don't change state
            return (self.state != previous_state, False)
        
        # Step 3: Check weight threshold
        if weight < self.min_weight_threshold:
            # Weight too low - don't update last_seen_time, don't change state
            return (self.state != previous_state, False)
        
        # Step 4: Valid detection - update last_seen_time
        self.last_seen_time = current_time
        
        # Step 5: State machine logic
        if self.state == PlatformState.EMPTY:
            # Transition: EMPTY -> ITEM_PRESENT
            # This is a new item placement
            self.state = PlatformState.ITEM_PRESENT
            self.current_item = (detected_item_name, weight)
            
            logger.info(f"🔄 [{timestamp_str}] State transition: EMPTY -> ITEM_PRESENT")
            logger.info(f"📦 [{timestamp_str}] Item detected: {detected_item_name} ({weight}g, conf: {confidence:.2f})")
            print(f"✅ [{timestamp_str}] NEW ITEM DETECTED: {detected_item_name} ({weight}g)")
            
            return (True, True)  # State changed, should consider for billing
        
        elif self.state == PlatformState.ITEM_PRESENT:
            current_name, current_weight = self.current_item
            
            if detected_item_name == current_name:
                # Same item still present - update last_seen_time, ignore detection
                logger.debug(f"⏸️  [{timestamp_str}] Same item '{detected_item_name}' still present")
                return (False, False)  # No state change, no billing
            else:
                # Different item detected - this means a new item was placed
                # Treat this as a new placement: reset to EMPTY then transition to ITEM_PRESENT
                logger.info(f"🔄 [{timestamp_str}] Item changed: {current_name} -> {detected_item_name}")
                logger.info(f"🔄 [{timestamp_str}] Treating as new item placement - allowing billing")
                print(f"🔄 [{timestamp_str}] ITEM CHANGED: {current_name} -> {detected_item_name}")
                print(f"✅ [{timestamp_str}] NEW ITEM DETECTED: {detected_item_name} ({weight}g) - Allowing billing")
                
                # Update state for new item (state remains ITEM_PRESENT but item changed)
                self.current_item = (detected_item_name, weight)
                # Return True to allow billing for the new item
                return (True, True)  # State changed (item changed), should consider for billing
        
        return (False, False)
    
    def should_detect(self, current_weight: float) -> bool:
        """
        Check if detection should be performed based on weight threshold.
        
        Args:
            current_weight: Current weight from scale (grams)
        
        Returns:
            bool: True if detection should proceed
        """
        return current_weight >= self.min_weight_threshold
    
    def get_state(self) -> PlatformState:
        """Get current platform state."""
        return self.state
    
    def get_current_item(self) -> Optional[Tuple[str, float]]:
        """Get current item on platform (if any)."""
        return self.current_item
    
    def reset(self):
        """Reset state machine to EMPTY state."""
        timestamp_str = datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        self.state = PlatformState.EMPTY
        self.current_item = None
        self.last_seen_time = 0.0
        logger.info(f"🔄 [{timestamp_str}] Detection state machine reset to EMPTY")


# Global detection state instance
detection_state = DetectionState()
