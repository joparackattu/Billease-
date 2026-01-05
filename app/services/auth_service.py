"""
Authentication Service for BILLESE

Handles shopkeeper authentication and session management.
"""

import secrets
from typing import Optional, Dict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class AuthService:
    """
    Manages shopkeeper authentication and sessions.
    """
    
    def __init__(self):
        """Initialize auth service."""
        # In-memory session storage (token -> shopkeeper_id)
        # In production, use Redis or database
        self.sessions: Dict[str, Dict] = {}
        self.session_timeout = timedelta(hours=24)  # Sessions expire after 24 hours
    
    def login(self, username: str, password: str) -> Optional[Dict]:
        """
        Authenticate shopkeeper and create session.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            dict: Session info with token, or None if authentication failed
        """
        try:
            from app.services.database import db
            
            if not username or not password:
                logger.warning("Login attempt with empty username or password")
                return None
            
            shopkeeper = db.authenticate_shopkeeper(username, password)
            if not shopkeeper:
                logger.warning(f"Failed login attempt for username: {username}")
                return None
            
            # Generate session token
            token = secrets.token_urlsafe(32)
            
            # Store session
            self.sessions[token] = {
                "shopkeeper_id": shopkeeper["id"],
                "username": shopkeeper["username"],
                "shop_name": shopkeeper["shop_name"],
                "created_at": datetime.now(),
                "expires_at": datetime.now() + self.session_timeout
            }
            
            logger.info(f"Shopkeeper logged in: {username} (ID: {shopkeeper['id']})")
            
            return {
                "token": token,
                "shopkeeper": shopkeeper
            }
        except Exception as e:
            logger.error(f"Error in login method: {str(e)}", exc_info=True)
            return None
    
    def validate_token(self, token: str) -> Optional[Dict]:
        """
        Validate session token.
        
        Args:
            token: Session token
            
        Returns:
            dict: Session info if valid, None otherwise
        """
        if token not in self.sessions:
            return None
        
        session = self.sessions[token]
        
        # Check if session expired
        if datetime.now() > session["expires_at"]:
            del self.sessions[token]
            logger.debug(f"Session expired for token: {token[:8]}...")
            return None
        
        # Extend session
        session["expires_at"] = datetime.now() + self.session_timeout
        
        return session
    
    def logout(self, token: str):
        """
        Logout and invalidate session.
        
        Args:
            token: Session token
        """
        if token in self.sessions:
            shopkeeper_id = self.sessions[token]["shopkeeper_id"]
            del self.sessions[token]
            logger.info(f"Shopkeeper logged out: ID {shopkeeper_id}")
    
    def get_shopkeeper_id(self, token: str) -> Optional[int]:
        """
        Get shopkeeper ID from token.
        
        Args:
            token: Session token
            
        Returns:
            int: Shopkeeper ID or None
        """
        session = self.validate_token(token)
        return session["shopkeeper_id"] if session else None


# Global auth service instance
auth_service = AuthService()


