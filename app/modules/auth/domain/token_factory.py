# app/modules/auth/domain/token_factory.py
"""
Token factory domain logic.
Creates and manages token pairs (access + refresh).
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from uuid import UUID

from app.modules.auth.domain.jwt_manager import JWTManager
from app.modules.auth.enums import TokenType
from app.modules.auth.constants import AuthConstants


class TokenFactory:
    """
    Domain service for creating token pairs.
    Handles access/refresh token generation and rotation.
    """
    
    def __init__(self, jwt_manager: Optional[JWTManager] = None):
        self.jwt_manager = jwt_manager or JWTManager()
    
    def create_token_pair(
        self,
        user_id: UUID,
        session_id: UUID,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a pair of access and refresh tokens.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            extra_data: Additional data to include
            
        Returns:
            Dictionary with token data
        """
        user_id_str = str(user_id)
        session_id_str = str(session_id)
        extra_data = extra_data or {}
        
        # Create access token
        access_token, access_jti, access_expires = self.jwt_manager.create_access_token(
            user_id_str,
            session_id_str,
            extra_data
        )
        
        # Create refresh token
        refresh_token, refresh_jti, refresh_expires = self.jwt_manager.create_refresh_token(
            user_id_str,
            session_id_str,
            extra_data
        )
        
        return {
            "access_token": access_token,
            "access_jti": access_jti,
            "access_expires_at": access_expires,
            "refresh_token": refresh_token,
            "refresh_jti": refresh_jti,
            "refresh_expires_at": refresh_expires,
        }
    
    def refresh_token_pair(
        self,
        refresh_token: str,
        user_id: UUID,
        session_id: UUID,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Rotate token pair using a refresh token.
        
        Args:
            refresh_token: Existing refresh token
            user_id: User identifier
            session_id: Session identifier
            extra_data: Additional data to include
            
        Returns:
            Dictionary with new token data
            
        Raises:
            ValueError: If refresh token is invalid or doesn't match
        """
        # Validate refresh token
        payload = self.jwt_manager.validate_token(refresh_token, expected_type=TokenType.REFRESH)
        
        # Verify it matches the user
        if str(user_id) != payload.get("sub"):
            raise ValueError("Refresh token does not belong to this user")
        
        # Verify it matches the session
        if str(session_id) != payload.get("session_id"):
            raise ValueError("Refresh token does not belong to this session")
        
        return self.create_token_pair(user_id, session_id, extra_data)
    
    def create_reset_token(
        self,
        user_id: UUID,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a password reset token.
        
        Args:
            user_id: User identifier
            extra_data: Additional data to include
            
        Returns:
            Dictionary with token data
        """
        user_id_str = str(user_id)
        extra_data = extra_data or {}
        
        token, jti, expires_at = self.jwt_manager.create_reset_token(
            user_id_str,
            extra_data
        )
        
        return {
            "token": token,
            "jti": jti,
            "expires_at": expires_at,
        }
    
    def create_verification_token(
        self,
        user_id: UUID,
        email: str,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create an email verification token.
        
        Args:
            user_id: User identifier
            email: Email to verify
            extra_data: Additional data to include
            
        Returns:
            Dictionary with token data
        """
        user_id_str = str(user_id)
        extra_data = extra_data or {}
        
        token, jti, expires_at = self.jwt_manager.create_verification_token(
            user_id_str,
            email,
            extra_data
        )
        
        return {
            "token": token,
            "jti": jti,
            "expires_at": expires_at,
        }
    
    def create_api_token(
        self,
        user_id: UUID,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create an API token (long-lived).
        
        Args:
            user_id: User identifier
            extra_data: Additional data to include
            
        Returns:
            Dictionary with token data
        """
        user_id_str = str(user_id)
        extra_data = extra_data or {}
        
        # Use longer expiry for API Token
        expiry = timedelta(seconds=AuthConstants.TOKEN_EXPIRY[AuthConstants.TOKEN_TYPE_API])
        
        token, jti, expires_at = self.jwt_manager.create_token(
            data={"user_id": user_id_str, **extra_data},
            token_type=TokenType.API,
            expires_delta=expiry
        )
        
        return {
            "token": token,
            "jti": jti,
            "expires_at": expires_at,
        }
    
    def get_token_expiry_info(
        self,
        access_token: str,
        refresh_token: str
    ) -> Dict[str, Any]:
        """
        Get expiry information for token pair.
        
        Args:
            access_token: Access token string
            refresh_token: Refresh token string
            
        Returns:
            Dictionary with expiry information
        """
        access_expiry = self.jwt_manager.get_token_expiry(access_token)
        refresh_expiry = self.jwt_manager.get_token_expiry(refresh_token)
        
        now = datetime.utcnow()
        
        return {
            "access_token_expires_at": access_expiry.isoformat() if access_expiry else None,
            "access_token_expires_in": int((access_expiry - now).total_seconds()) if access_expiry else 0,
            "refresh_token_expires_at": refresh_expiry.isoformat() if refresh_expiry else None,
            "refresh_token_expires_in": int((refresh_expiry - now).total_seconds()) if refresh_expiry else 0,
            "is_access_expired": access_expiry is not None and access_expiry <= now,
            "is_refresh_expired": refresh_expiry is not None and refresh_expiry <= now,
        }


__all__ = ['TokenFactory']