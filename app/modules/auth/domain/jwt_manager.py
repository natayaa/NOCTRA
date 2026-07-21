# app/modules/auth/domain/jwt_manager.py
"""
JWT management domain logic.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple

from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError

from app.core.config import settings
from app.modules.auth.constants import AuthConstants
from app.modules.auth.enums import TokenType


class JWTManager:
    """
    Domain service for JWT Token management.
    Handle token creation, validation and decoding.
    """
    
    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        
    def create_token(
        self,
        data: Dict[str, Any],
        token_type: TokenType = TokenType.ACCESS,
        expires_delta: Optional[timedelta] = None,
        **kwargs
    ) -> Tuple[str, str, datetime]:
        """
        Create a JWT Token.
        
        Args:
            data: Payload data
            token_type: Type of token (access, refresh, etc)
            expires_delta: Custom expiration delta
            **kwargs: Additional claims to include
            
        Returns:
            Tuple of (token_string, jti, expiration_datetime)
        """
        jti = str(uuid.uuid4())
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expiry_seconds = AuthConstants.TOKEN_EXPIRY.get(
                token_type.value,
                AuthConstants.TOKEN_EXPIRY[AuthConstants.TOKEN_TYPE_ACCESS]
            )
            expire = datetime.utcnow() + timedelta(seconds=expiry_seconds)
        
        payload = {
            "sub": str(data.get("user_id", "")),
            "jti": jti,
            "type": token_type.value,
            "iat": datetime.utcnow(),
            "exp": expire,
            **data,
            **kwargs
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, jti, expire
    
    def create_access_token(
        self,
        user_id: str,
        session_id: str,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str, datetime]:
        """
        Create an access token.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            extra_data: Additional data to include
            
        Returns:
            Tuple of (token_string, jti, expiration_datetime)
        """
        data = {
            "user_id": str(user_id),
            "session_id": str(session_id),
            **(extra_data or {})
        }
        
        return self.create_token(data, TokenType.ACCESS)
    
    def create_refresh_token(
        self,
        user_id: str,
        session_id: str,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str, datetime]:
        """
        Create a refresh token.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            extra_data: Additional data to include
            
        Returns:
            Tuple of (token_string, jti, expiration_datetime)
        """
        data = {
            "user_id": str(user_id),
            "session_id": str(session_id),
            **(extra_data or {})
        }
        return self.create_token(data, TokenType.REFRESH)
    
    def create_reset_token(
        self,
        user_id: str,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str, datetime]:
        """
        Create a password reset token.
        
        Args:
            user_id: User identifier
            extra_data: Additional data to include
            
        Returns:
            Tuple of (token_string, jti, expiration_datetime)
        """
        data = {
            "user_id": str(user_id),
            "purpose": "reset_password",
            **(extra_data or {})
        }
        return self.create_token(data, TokenType.RESET)
    
    def create_verification_token(
        self,
        user_id: str,
        email: str,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str, datetime]:
        """
        Create an email verification token.
        
        Args:
            user_id: User identifier
            email: Email to verify
            extra_data: Additional data to include
            
        Returns:
            Tuple of (token_string, jti, expiration_datetime)
        """
        data = {
            "user_id": str(user_id),
            "email": email,
            "purpose": "verify_email",
            **(extra_data or {})
        }
        return self.create_token(data, TokenType.VERIFICATION)
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        Decode and validate a JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded payload
            
        Raises:
            ExpiredSignatureError: If token is expired
            JWTError: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except ExpiredSignatureError:
            raise ExpiredSignatureError("Token has expired")
        except JWTError as e:
            raise JWTError(f"Invalid token: {str(e)}")
    
    def validate_token(
        self,
        token: str,
        expected_type: Optional[TokenType] = None
    ) -> Dict[str, Any]:
        """
        Validate a token and optionally check its type.
        
        Args:
            token: JWT token string
            expected_type: Expected token type
            
        Returns:
            Validated payload
            
        Raises:
            ExpiredSignatureError: If token is expired
            JWTError: If token is invalid or wrong type
        """
        payload = self.decode_token(token)
        
        # Check token type
        if expected_type:
            token_type = payload.get("type")
            if token_type != expected_type.value:
                raise JWTError(
                    f"Invalid token type. Expected: {expected_type.value}, Got: {token_type}"
                )
        
        return payload
    
    def get_token_type(self, token: str) -> Optional[str]:
        """
        Get token type without full validation.
        
        Args:
            token: JWT token string
            
        Returns:
            Token type or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False}
            )
            return payload.get("type")
        except JWTError:
            return None
    
    def get_token_data(
        self,
        token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get token data without validation (for debugging).
        
        Args:
            token: JWT token string
            
        Returns:
            Token payload or None if invalid
        """
        try:
            return jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False, "verify_signature": False}
            )
        except JWTError:
            return None
    
    def is_token_expired(self, token: str) -> bool:
        """
        Check if token is expired.
        
        Args:
            token: JWT token string
            
        Returns:
            True if token is expired
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False}
            )
            exp = payload.get("exp")
            if exp:
                return datetime.utcnow() > datetime.fromtimestamp(exp)
            return False
        except JWTError:
            return True
    
    def get_token_expiry(self, token: str) -> Optional[datetime]:
        """
        Get token expiration time.
        
        Args:
            token: JWT token string
            
        Returns:
            Expiration datetime or None
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False}
            )
            exp = payload.get("exp")
            if exp:
                return datetime.fromtimestamp(exp)
            return None
        except JWTError:
            return None
    
    def get_user_id_from_token(self, token: str) -> Optional[str]:
        """
        Extract user ID from token.
        
        Args:
            token: JWT token string
            
        Returns:
            User ID or None
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False}
            )
            return payload.get("sub") or payload.get("user_id")
        except JWTError:
            return None
    
    def get_jti_from_token(self, token: str) -> Optional[str]:
        """
        Extract JTI from token.
        
        Args:
            token: JWT token string
            
        Returns:
            JTI or None
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False}
            )
            return payload.get("jti")
        except JWTError:
            return None


__all__ = ['JWTManager']