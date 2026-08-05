import secrets
import hashlib
import random
import logging

from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta

from passlib.context import CryptContext
from jose import jwt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .config import settings


logger = logging.getLogger(__name__)

# ==================== PASSWORD HASHING ====================

class PasswordHandler:
    """Handles password hashing and verification"""
    
    def __init__(self):
        self._pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=settings.PASSWORD_HASH_ROUNDS
        )
    
    def hash(self, password: str) -> str:
        """Hash a password"""
        return self._pwd_context.hash(password)
    
    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        try:
            return self._pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False
    
    def needs_rehash(self, hashed_password: str) -> bool:
        """Check if password needs rehashing"""
        return self._pwd_context.needs_update(hashed_password)

# ==================== JWT HANDLER ====================

class JWTManager:
    """Handles JWT token creation and validation"""
    
    @staticmethod
    def create_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None,
        token_type: str = "access"
    ) -> str:
        """Create a JWT token"""
        to_encode = data.copy()
        
        # Set expiration
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            if token_type == "access":
                expire = datetime.utcnow() + timedelta(
                    minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
                )
            elif token_type == "refresh":
                expire = datetime.utcnow() + timedelta(
                    days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
                )
            else:
                expire = datetime.utcnow() + timedelta(hours=1)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": token_type
        })
        
        return jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
    
    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """Decode and validate a JWT token"""
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=401,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )
    
    @staticmethod
    def validate_token(token: str, token_type: str = "access") -> Dict[str, Any]:
        """Validate token and check its type"""
        payload = JWTManager.decode_token(token)
        
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=401,
                detail=f"Invalid token type. Expected: {token_type}"
            )
        
        return payload
    
    @staticmethod
    def get_token_data(token: str) -> Optional[Dict[str, Any]]:
        """Get data from token without validation (for debugging)"""
        try:
            return jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                options={"verify_exp": False}
            )
        except jwt.InvalidTokenError:
            return None

# ==================== API KEY HANDLER ====================

class APIKeyManager:
    """Handles API key generation and validation"""
    
    @staticmethod
    def generate_pair() -> Tuple[str, str]:
        """
        Generate API key pair (key_id, secret)
        Returns: (key_id, secret)
        """
        key_id = f"ak_{secrets.token_urlsafe(16)}"
        secret = secrets.token_urlsafe(32)
        return key_id, secret
    
    @staticmethod
    def hash_secret(secret: str) -> str:
        """Hash API key secret for storage"""
        return hashlib.sha256(secret.encode()).hexdigest()
    
    @staticmethod
    def verify_secret(secret: str, hashed: str) -> bool:
        """Verify API key secret against hash"""
        return APIKeyManager.hash_secret(secret) == hashed

# ==================== SECURITY SCHEMES ====================

# HTTP Bearer token scheme
security_scheme = HTTPBearer(auto_error=False)

# ==================== DEPENDENCIES ====================

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
) -> Dict[str, Any]:
    """
    Get current user from JWT token.
    Returns token payload.
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = credentials.credentials
    payload = JWTManager.validate_token(token, token_type="access")
    
    # Ensure subject exists
    if not payload.get("sub"):
        raise HTTPException(
            status_code=401,
            detail="Invalid token payload"
        )
    
    return payload

async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current active user.
    Extends get_current_user with active status check.
    """
    # Check if user is active
    if not current_user.get("is_active", True):
        raise HTTPException(
            status_code=400,
            detail="Inactive user"
        )
    
    return current_user

async def get_token_from_header(
    authorization: Optional[str] = None
) -> Optional[str]:
    """Extract token from Authorization header"""
    if not authorization:
        return None
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    
    return parts[1]

# ==================== UTILITY FUNCTIONS ====================

def generate_random_token(length: int = 32) -> str:
    """Generate a random token"""
    return secrets.token_urlsafe(length)

def generate_verification_code(length: int = 6) -> str:
    """Generate a numeric verification code"""
    return ''.join([str(random.randint(0, 9)) for _ in range(length)])

def generate_salt() -> str:
    """Generate a random salt"""
    return secrets.token_hex(16)

# ==================== EXPORTS ====================

__all__ = [
    # Handlers
    "PasswordHandler",
    "JWTManager",
    "APIKeyManager",
    
    # Security schemes
    "security_scheme",
    
    # Dependencies
    "get_current_user",
    "get_current_active_user",
    "get_token_from_header",
    
    # Utilities
    "generate_random_token",
    "generate_verification_code",
    "generate_salt",
]