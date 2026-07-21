# app/modules/auth/services/password_service.py
"""
Password service for password management.
"""

from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from uuid import UUID

from app.modules.auth.domain.password_hasher import PasswordHasher
from app.modules.auth.domain.token_factory import TokenFactory
from app.modules.auth.domain.validator import AuthValidator
from app.modules.auth.repositories.user_repository import UserRepository
from app.modules.auth.repositories.token_repository import TokenRepository
from app.modules.auth.models.user import User
from app.modules.auth.constants import AuthConstants
from app.modules.auth.enums import TokenType, UserStatus
from app.modules.auth.exceptions import (
    UserNotFoundError,
    InvalidCredentialsError,
    TokenExpiredError,
    TokenInvalidError,
    RateLimitExceededError,
)

from app.core.logging import get_logger
from app.core.config import settings
from jose.exceptions import ExpiredSignatureError, JWTError

logger = get_logger(__name__)


class PasswordService:
    """
    Password service for password management.
    
    Handles:
    - Password change
    - Password reset
    - Password validation
    - Password strength checking
    """
    
    def __init__(
        self,
        user_repo: UserRepository,
        token_repo: TokenRepository,
        password_hasher: Optional[PasswordHasher] = None,
        token_factory: Optional[TokenFactory] = None,
    ):
        self.user_repo = user_repo
        self.token_repo = token_repo
        self.password_hasher = password_hasher or PasswordHasher()
        self.token_factory = token_factory or TokenFactory()
        self.logger = get_logger(self.__class__.__name__)
    
    # ==================== PASSWORD CHANGE ====================
    
    async def change_password(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str,
    ) -> User:
        """
        Change user password with current password verification.
        
        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password
            
        Returns:
            Updated User instance
            
        Raises:
            UserNotFoundError: If user not found
            InvalidCredentialsError: If current password is incorrect
            ValueError: If new password is invalid
        """
        # Get user
        user = await self.user_repo.get_or_raise(user_id)
        
        # Verify current password
        if not self.password_hasher.verify(current_password, user.password_hash):
            raise InvalidCredentialsError("Current password is incorrect")
        
        # Validate new password
        valid, error = self.password_hasher.validate_strength(new_password)
        if not valid:
            raise ValueError(error)
        
        # Hash new password
        new_hash = self.password_hasher.hash(new_password)
        
        # Update password
        user = await self.user_repo.update_password(user_id, new_hash)
        
        self.logger.info(f"Password changed for user: {user_id}")
        return user
    
    async def change_password_without_verification(
        self,
        user_id: UUID,
        new_password: str,
    ) -> User:
        """
        Change user password without verification (admin action).
        
        Args:
            user_id: User ID
            new_password: New password
            
        Returns:
            Updated User instance
            
        Raises:
            UserNotFoundError: If user not found
            ValueError: If new password is invalid
        """
        # Get user
        user = await self.user_repo.get_or_raise(user_id)
        
        # Validate new password
        valid, error = self.password_hasher.validate_strength(new_password)
        if not valid:
            raise ValueError(error)
        
        # Hash new password
        new_hash = self.password_hasher.hash(new_password)
        
        # Update password
        user = await self.user_repo.update_password(user_id, new_hash)
        
        self.logger.info(f"Password force-changed for user: {user_id}")
        return user
    
    # ==================== PASSWORD RESET ====================
    
    async def initiate_password_reset(
        self,
        email: str,
    ) -> Dict[str, Any]:
        """
        Initiate password reset by sending reset token.
        
        Args:
            email: User email
            
        Returns:
            Dictionary with reset token info
            
        Raises:
            UserNotFoundError: If user not found
            RateLimitExceededError: If too many reset attempts
        """
        # Find user by email
        user = await self.user_repo.get_by_email(email)
        if not user:
            # Don't reveal that user doesn't exist for security
            return {
                "message": "If an account exists with this email, a reset link has been sent.",
                "email": email,
            }
        
        # Check rate limit (3 attempts per hour)
        # In production, track reset attempts in cache or database
        
        # Create reset token
        reset_data = self.token_factory.create_reset_token(
            user_id=user.id,
            extra_data={"email": user.email}
        )
        
        # Save reset token in database or cache
        # For now, we'll just return the token
        # In production, store in cache with expiration
        
        self.logger.info(f"Password reset initiated for user: {email}")
        
        return {
            "user_id": str(user.id),
            "reset_token": reset_data["token"],
            "expires_at": reset_data["expires_at"].isoformat(),
            "message": "Password reset token created. Check your email.",
        }
    
    async def complete_password_reset(
        self,
        reset_token: str,
        new_password: str,
    ) -> User:
        """
        Complete password reset with token verification.
        
        Args:
            reset_token: Reset token string
            new_password: New password
            
        Returns:
            Updated User instance
            
        Raises:
            TokenExpiredError: If token is expired
            TokenInvalidError: If token is invalid
            ValueError: If new password is invalid
        """
        # Validate reset token
        try:
            payload = self.token_factory.jwt_manager.validate_token(
                reset_token,
                expected_type=TokenType.RESET
            )
        except ExpiredSignatureError:
            raise TokenExpiredError("Reset token has expired")
        except JWTError:
            raise TokenInvalidError("Invalid reset token")
        
        # Get user
        user_id = payload.get("user_id")
        if not user_id:
            raise TokenInvalidError("Invalid reset token")
        
        user = await self.user_repo.get_or_raise(UUID(user_id))
        
        # Validate new password
        valid, error = self.password_hasher.validate_strength(new_password)
        if not valid:
            raise ValueError(error)
        
        # Hash new password
        new_hash = self.password_hasher.hash(new_password)
        
        # Update password
        user = await self.user_repo.update_password(user.id, new_hash)
        
        # Activate user if pending
        if user.status == UserStatus.PENDING:
            await self.user_repo.activate_user(user.id)
        
        self.logger.info(f"Password reset completed for user: {user.email}")
        return user
    
    # ==================== PASSWORD VALIDATION ====================
    
    def validate_password_strength(self, password: str) -> Tuple[bool, Optional[str]]:
        """
        Validate password strength.
        
        Args:
            password: Password to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        return self.password_hasher.validate_strength(password)
    
    def validate_password_confirmation(
        self,
        password: str,
        confirm_password: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate password confirmation.
        
        Args:
            password: Password
            confirm_password: Password confirmation
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        return AuthValidator.validate_password_confirmation(password, confirm_password)
    
    def generate_verification_code(self) -> str:
        """
        Generate a verification code for email/phone verification.
        
        Returns:
            Verification code
        """
        return self.password_hasher.generate_verification_code()
    
    def generate_reset_token(self) -> str:
        """
        Generate a secure reset token.
        
        Returns:
            Reset token
        """
        return self.password_hasher.generate_reset_token()
    
    # ==================== PASSWORD CHECK ====================
    
    async def check_password_history(
        self,
        user_id: UUID,
        new_password: str,
        history_count: int = 5,
    ) -> bool:
        """
        Check if password has been used recently.
        
        Args:
            user_id: User ID
            new_password: New password
            history_count: Number of previous passwords to check
            
        Returns:
            True if password has been used recently
            
        Raises:
            UserNotFoundError: If user not found
        """
        # Get user
        user = await self.user_repo.get_or_raise(user_id)
        
        # In production, query password history from database
        # For now, just return False (not found in history)
        return False
    
    async def require_password_reset(
        self,
        user_id: UUID,
    ) -> User:
        """
        Require user to reset password on next login.
        
        Args:
            user_id: User ID
            
        Returns:
            Updated User instance
            
        Raises:
            UserNotFoundError: If user not found
        """
        user = await self.user_repo.get_or_raise(user_id)
        await self.user_repo.update(
            user_id,
            {"password_reset_required": True}
        )
        
        self.logger.info(f"Password reset required for user: {user_id}")
        return user


__all__ = ['PasswordService']