# app/modules/auth/domain/validator.py
"""
Authentication validation domain logic.
"""

import re
from typing import Optional, Tuple, List, Any
from datetime import datetime
from uuid import UUID

from email_validator import validate_email, EmailNotValidError

from app.modules.auth.constants import AuthConstants
from app.modules.auth.exceptions import AuthException


class AuthValidator:
    """
    Domain service for authentication validation.
    Handles validation of email, phone, password, etc.
    """
    
    # ==================== EMAIL VALIDATION ====================
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, Optional[str]]:
        """
        Validate email format.
        
        Args:
            email: Email to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not email:
            return False, "Email is required"
        
        try:
            validate_email(email)
            return True, None
        except EmailNotValidError as e:
            return False, str(e)
    
    @staticmethod
    def normalize_email(email: str) -> str:
        """
        Normalize email address (lowercase, strip whitespace).
        
        Args:
            email: Email to normalize
            
        Returns:
            Normalized email
        """
        try:
            result = validate_email(email)
            return result.email
        except EmailNotValidError:
            return email.lower().strip()
    
    # ==================== PHONE VALIDATION ====================
    
    @staticmethod
    def validate_phone(phone: str) -> Tuple[bool, Optional[str]]:
        """
        Validate phone number format.
        
        Args:
            phone: Phone number to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not phone:
            return False, "Phone number is required"
        
        # Remove whitespace and special characters
        cleaned = re.sub(r'[\s\-\(\)\.]', '', phone)
        
        # Check if it contains only digits and optional '+'
        if not re.match(r'^\+?[0-9]+$', cleaned):
            return False, "Phone number contains invalid characters"
        
        # Check length (min 8, max 15 for international)
        if len(cleaned) < 8:
            return False, "Phone number is too short (min 8 digits)"
        if len(cleaned) > 15:
            return False, "Phone number is too long (max 15 digits)"
        
        return True, None
    
    @staticmethod
    def normalize_phone(phone: str) -> str:
        """
        Normalize phone number (remove formatting).
        
        Args:
            phone: Phone number to normalize
            
        Returns:
            Normalized phone number
        """
        return re.sub(r'[\s\-\(\)\.]', '', phone)
    
    # ==================== PASSWORD VALIDATION ====================
    
    @staticmethod
    def validate_password(password: str) -> Tuple[bool, Optional[str]]:
        """
        Validate password against security policy.
        
        Args:
            password: Password to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not password:
            return False, "Password is required"
        
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
        
        # Check common patterns
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
        
        return True, None
    
    @staticmethod
    def validate_password_confirmation(
        password: str,
        confirm_password: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that password and confirmation match.
        
        Args:
            password: Password
            confirm_password: Password confirmation
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if password != confirm_password:
            return False, "Passwords do not match"
        return AuthValidator.validate_password(password)
    
    # ==================== UUID VALIDATION ====================
    
    @staticmethod
    def validate_uuid(value: str) -> Tuple[bool, Optional[str]]:
        """
        Validate UUID format.
        
        Args:
            value: UUID string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not value:
            return False, "UUID is required"
        
        try:
            UUID(value)
            return True, None
        except ValueError:
            return False, "Invalid UUID format"
    
    @staticmethod
    def validate_user_id(user_id: str) -> Tuple[bool, Optional[str]]:
        """
        Validate user ID.
        
        Args:
            user_id: User ID to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        return AuthValidator.validate_uuid(user_id)
    
    @staticmethod
    def validate_session_id(session_id: str) -> Tuple[bool, Optional[str]]:
        """
        Validate session ID.
        
        Args:
            session_id: Session ID to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        return AuthValidator.validate_uuid(session_id)
    
    # ==================== TOKEN VALIDATION ====================
    
    @staticmethod
    def validate_token_string(token: str) -> Tuple[bool, Optional[str]]:
        """
        Validate token format.
        
        Args:
            token: Token to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not token:
            return False, "Token is required"
        
        if len(token) < 10:
            return False, "Token is too short"
        
        return True, None
    
    @staticmethod
    def validate_verification_code(code: str) -> Tuple[bool, Optional[str]]:
        """
        Validate verification code.
        
        Args:
            code: Verification code to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not code:
            return False, "Verification code is required"
        
        expected_length = AuthConstants.VERIFICATION_CODE_LENGTH
        
        if len(code) != expected_length:
            return False, f"Verification code must be {expected_length} digits"
        
        if not code.isdigit():
            return False, "Verification code must contain only digits"
        
        return True, None


__all__ = ['AuthValidator']