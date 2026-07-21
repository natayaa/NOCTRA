# app/modules/auth/domain/password_hasher.py
"""
Password hashing domain logic.
Pure business logic - no framework dependencies.
"""

import re
import secrets
from typing import Optional, Tuple

from passlib.context import CryptContext

from app.core.config import settings
from app.modules.auth.constants import AuthConstants


class PasswordHasher:
    """
    Domain service for password hashing and verification.
    Handles password security business rules.
    """
    
    def __init__(self):
        self._pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=settings.PASSWORD_HASH_ROUNDS
        )
    
    def hash(self, plain_password: str) -> str:
        """Hash a plain text password."""
        return self._pwd_context.hash(plain_password)
    
    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain text password against a hash."""
        try:
            return self._pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False
    
    def need_rehash(self, hashed_password: str) -> bool:
        """Check if password hash needs to be updated."""
        return self._pwd_context.needs_update(hashed_password)
    
    def validate_strength(self, password: str) -> Tuple[bool, Optional[str]]:
        """
        Validate password strength based on business rules.
        
        Args:
            password: Password to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check length
        if len(password) < AuthConstants.PASSWORD_MIN_LENGTH:
            return False, f"Password must be at least {AuthConstants.PASSWORD_MIN_LENGTH} characters"
        
        if len(password) > AuthConstants.PASSWORD_MAX_LENGTH:
            return False, f"Password must be at most {AuthConstants.PASSWORD_MAX_LENGTH} characters"
        
        # Check uppercase
        if AuthConstants.PASSWORD_REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"
        
        # Check lowercase
        if AuthConstants.PASSWORD_REQUIRE_LOWERCASE and not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"
        
        # Check digit
        if AuthConstants.PASSWORD_REQUIRE_DIGIT and not any(c.isdigit() for c in password):
            return False, "Password must contain at least one digit"
        
        # Check special character
        if AuthConstants.PASSWORD_REQUIRE_SPECIAL and not any(
            c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password
        ):
            return False, "Password must contain at least one special character"
        
        # Check for common patterns
        common_patterns = [
            r'^password$', r'^123456$', r'^qwerty$', r'^admin$',
            r'^([a-zA-Z])\1+$',  # Same character repeated
            r'^[0-9]+$',         # Only digits
            r'^[a-z]+$',         # Only lowercase
            r'^[A-Z]+$',         # Only uppercase
        ]
        
        for pattern in common_patterns:
            if re.match(pattern, password, re.IGNORECASE):
                return False, "Password is too common or uses a simple pattern"
        
        # Check sequential characters
        if self._has_sequential_chars(password, 3):
            return False, "Password contains sequential characters (e.g., abc, 123)"
        
        # Check repeated characters
        if self._has_repeated_chars(password, 4):
            return False, "Password contains too many repeated characters"
        
        return True, None
    
    def _has_sequential_chars(self, password: str, length: int = 3) -> bool:
        """
        Check if password contains sequential characters.
        
        Args:
            password: Password to check
            length: Minimum sequence length
            
        Returns:
            True if sequential characters found
        """
        # Check alphabetic sequences
        for i in range(len(password) - length + 1):
            sub = password[i:i+length]
            if sub.isalpha():
                if all(ord(sub[j]) == ord(sub[0]) + j for j in range(length)):
                    return True
                if all(ord(sub[j]) == ord(sub[0]) - j for j in range(length)):
                    return True
        
        # Check numeric sequences
        for i in range(len(password) - length + 1):
            if password[i:i+length].isdigit():
                sub = [int(c) for c in password[i:i+length]]
                if all(sub[j] == sub[0] + j for j in range(length)):
                    return True
                if all(sub[j] == sub[0] - j for j in range(length)):
                    return True
        
        return False
    
    def _has_repeated_chars(self, password: str, max_repeats: int = 3) -> bool:
        """
        Check if password has too many repeated characters.
        
        Args:
            password: Password to check
            max_repeats: Maximum allowed repeats
            
        Returns:
            True if repeated characters found
        """
        for i in range(len(password) - max_repeats + 1):
            if len(set(password[i:i+max_repeats])) == 1:
                return True
        return False
    
    def generate_verification_code(self) -> str:
        """
        Generate a numeric verification code.
        
        Returns:
            Verification code string
        """
        length = AuthConstants.VERIFICATION_CODE_LENGTH
        return ''.join(str(secrets.randbelow(10)) for _ in range(length))
    
    def generate_reset_token(self) -> str:
        """
        Generate a secure reset token.
        
        Returns:
            Secure reset token
        """
        return secrets.token_urlsafe(32)


__all__ = ['PasswordHasher']