"""
Bill Manager Service

This service manages bill sessions in memory.
It stores all scanned items for each session and calculates totals.

Note: This is temporary in-memory storage.
In the future, this will be replaced with a database.
"""

from typing import Dict, Optional
from app.models.schemas import BillSession, BillItem
import uuid


class BillManager:
    """
    Manages bill sessions in memory.
    
    This class stores all bill sessions temporarily.
    Each session has a unique ID and contains a list of items.
    """
    
    def __init__(self):
        """
        Initialize the bill manager.
        
        Creates an empty dictionary to store bill sessions.
        Key: session_id (string)
        Value: BillSession object
        """
        self.sessions: Dict[str, BillSession] = {}
    
    def get_or_create_session(self, session_id: Optional[str] = None) -> BillSession:
        """
        Get an existing session or create a new one.
        
        If session_id is provided and exists, return that session.
        Otherwise, create a new session with a unique ID.
        
        Args:
            session_id: Optional session ID. If None, creates a new session.
            
        Returns:
            BillSession: The bill session object
        """
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]
        
        # Create new session with unique ID
        new_session_id = session_id or str(uuid.uuid4())
        new_session = BillSession(session_id=new_session_id)
        self.sessions[new_session_id] = new_session
        return new_session
    
    def add_item_to_session(self, session_id: str, item: BillItem):
        """
        Add an item to a bill session.
        
        Args:
            session_id: The session ID to add the item to
            item: The BillItem to add
        """
        session = self.get_or_create_session(session_id)
        session.add_item(item)
    
    def get_session(self, session_id: str) -> BillSession:
        """
        Get a bill session by ID.
        
        Args:
            session_id: The session ID
            
        Returns:
            BillSession: The bill session object
        """
        return self.get_or_create_session(session_id)
    
    def clear_session(self, session_id: str):
        """
        Clear all items from a session (but keep the session).
        
        Args:
            session_id: The session ID to clear
        """
        if session_id in self.sessions:
            self.sessions[session_id].items.clear()
    
    def remove_item_from_session(self, session_id: str, item_index: int) -> bool:
        """
        Remove an item from a session by index.
        
        Args:
            session_id: Session ID
            item_index: Index of item to remove (0-based)
        
        Returns:
            bool: True if item was removed, False if index invalid
        """
        session = self.get_or_create_session(session_id)
        if 0 <= item_index < len(session.items):
            removed_item = session.items.pop(item_index)
            return True
        return False
    
    def update_item_in_session(self, session_id: str, item_index: int, weight_grams: float) -> bool:
        """
        Update an item's weight in a session and recalculate price.
        
        Args:
            session_id: Session ID
            item_index: Index of item to update (0-based)
            weight_grams: New weight in grams
        
        Returns:
            bool: True if item was updated, False if index invalid
        """
        from app.services.item_detection import get_item_info
        
        session = self.get_or_create_session(session_id)
        if 0 <= item_index < len(session.items):
            item = session.items[item_index]
            # Recalculate price with new weight
            item_info = get_item_info(item.item_name, weight_grams)
            item.weight_grams = item_info.weight_grams
            item.total_price = item_info.total_price
            return True
        return False


# Create a global instance of BillManager
# This will be used throughout the application
bill_manager = BillManager()

