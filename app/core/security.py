# core/security.py
import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

from core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# =============================================================================
# Password Hashing
# =============================================================================

def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(password, hashed_password)


# =============================================================================
# JWT
# =============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode JWT token."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return {}


def validate_token(token: str) -> bool:
    """Validate JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY,
                             algorithms=[settings.ALGORITHM])
        return payload.get("exp", 0) > datetime.utcnow().timestamp()
    except JWTError:
        return False


# =============================================================================
# XSS & SQL Injection Prevention
# =============================================================================

def sanitize_input(value: str) -> str:
    """Sanitize input to prevent XSS."""
    if not value:
        return value

    # Replace dangerous characters
    dangerous = {
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#x27;",
        "/": "&#x2F;",
        "\\": "&#x5C;",
    }

    for char, replacement in dangerous.items():
        value = value.replace(char, replacement)

    return value


def escape_sql(value: str) -> str:
    """Escape SQL injection characters."""
    if not value:
        return value

    dangerous = {
        "'": "''",
        "\\": "\\\\",
        "%": "\\%",
        "_": "\\_",
    }

    for char, replacement in dangerous.items():
        value = value.replace(char, replacement)

    return value
