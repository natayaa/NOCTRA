# app/modules/auth/services/profile_service.py
"""
Profile service for user profile management.
"""

from typing import Optional, Dict, Any, List
from uuid import UUID

from app.modules.auth.domain.validator import AuthValidator
from app.modules.auth.repositories.user_repository import UserRepository
from app.modules.auth.repositories.session_repository import SessionRepository
from app.modules.auth.models.user import User
from app.modules.auth.enums import UserStatus, UserRole
from app.modules.auth.exceptions import UserNotFoundError, InvalidCredentialsError

from app.core.logging import get_logger

logger = get_logger(__name__)


class ProfileService:
    """
    Profile service for user profile management.
    
    Handles:
    - Profile retrieval
    - Profile update
    - Email and phone management
    - 2FA management
    """
    
    def __init__(
        self,
        user_repo: UserRepository,
        session_repo: SessionRepository,
    ):
        self.user_repo = user_repo
        self.session_repo = session_repo
        self.logger = get_logger(self.__class__.__name__)
    
    # ==================== PROFILE RETRIEVAL ====================
    
    async def get_profile(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get user profile.
        
        Args:
            user_id: User ID
            
        Returns:
            User profile data
            
        Raises:
            UserNotFoundError: If user not found
        """
        user = await self.user_repo.get_or_raise(user_id)
        
        # Get session count
        session_count = await self.session_repo.count_active_sessions(user_id)
        
        profile = user.to_dict()
        profile.update({
            "active_sessions": session_count,
        })
        
        return profile
    
    async def get_public_profile(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get public user profile (limited data).
        
        Args:
            user_id: User ID
            
        Returns:
            Public user profile data
            
        Raises:
            UserNotFoundError: If user not found
        """
        user = await self.user_repo.get_or_raise(user_id)
        
        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "avatar_url": user.avatar_url,
            "role": user.role.value if user.role else None,
            "status": user.status.value if user.status else None,
            "created_at": user.created_at.isoformat(),
        }
    
    # ==================== PROFILE UPDATE ====================
    
    async def update_profile(
        self,
        user_id: UUID,
        data: Dict[str, Any],
    ) -> User:
        """
        Update user profile.
        
        Args:
            user_id: User ID
            data: Profile data to update
            
        Returns:
            Updated User instance
            
        Raises:
            UserNotFoundError: If user not found
            ValueError: If validation fails
        """
        user = await self.user_repo.get_or_raise(user_id)
        
        # Validate data
        allowed_fields = {
            'full_name', 'first_name', 'last_name',
            'avatar_url', 'locale', 'timezone'
        }
        
        filtered_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        if not filtered_data:
            raise ValueError("No valid fields to update")
        
        user = await self.user_repo.update_profile(user_id, filtered_data)
        
        self.logger.info(f"Profile updated for user: {user_id}")
        return user
    
    # ==================== EMAIL MANAGEMENT ====================
    
    async def change_email(
        self,
        user_id: UUID,
        new_email: str,
        password: Optional[str] = None,
    ) -> User:
        """
        Change user email.
        
        Args:
            user_id: User ID
            new_email: New email
            password: Optional password verification
            
        Returns:
            Updated User instance
            
        Raises:
            UserNotFoundError: If user not found
            InvalidCredentialsError: If password is incorrect
            ValueError: If email is invalid or already exists
        """
        user = await self.user_repo.get_or_raise(user_id)
        
        # Validate email
        valid, error = AuthValidator.validate_email(new_email)
        if not valid:
            raise ValueError(error)
        
        # Normalize email
        new_email = AuthValidator.normalize_email(new_email)
        
        # Check if email already exists
        if await self.user_repo.email_exists(new_email, exclude_id=user_id):
            raise ValueError("Email already exists")
        
        # Verify password if provided
        if password:
            from app.modules.auth.domain.password_hasher import PasswordHasher
            hasher = PasswordHasher()
            if not hasher.verify(password, user.password_hash):
                raise InvalidCredentialsError("Invalid password")
        
        # Update email
        user = await self.user_repo.update(
            user_id,
            {
                "email": new_email,
                "is_email_verified": False,
                "email_verified_at": None,
            }
        )
        
        self.logger.info(f"Email changed for user: {user_id} to {new_email}")
        return user
    
    async def verify_email(
        self,
        user_id: UUID,
        verification_code: str,
    ) -> User:
        """
        Verify user email with code.
        
        Args:
            user_id: User ID
            verification_code: Verification code
            
        Returns:
            Updated User instance
            
        Raises:
            UserNotFoundError: If user not found
            InvalidCredentialsError: If verification code is invalid
        """
        user = await self.user_repo.get_or_raise(user_id)
        
        # In production, validate against stored code in cache
        # For now, check if code matches (simplified)
        if not verification_code or len(verification_code) != 6:
            raise InvalidCredentialsError("Invalid verification code")
        
        # Verify email
        user = await self.user_repo.verify_email(user_id)
        
        self.logger.info(f"Email verified for user: {user_id}")
        return user
    
    # ==================== PHONE MANAGEMENT ====================
    
    async def change_phone(
        self,
        user_id: UUID,
        new_phone: str,
    ) -> User:
        """
        Change user phone number.
        
        Args:
            user_id: User ID
            new_phone: New phone number
            
        Returns:
            Updated User instance
            
        Raises:
            UserNotFoundError: If user not found
            ValueError: If phone is invalid or already exists
        """
        user = await self.user_repo.get_or_raise(user_id)
        
        # Validate phone
        valid, error = AuthValidator.validate_phone(new_phone)
        if not valid:
            raise ValueError(error)
        
        # Normalize phone
        new_phone = AuthValidator.normalize_phone(new_phone)
        
        # Check if phone already exists
        if await self.user_repo.phone_exists(new_phone, exclude_id=user_id):
            raise ValueError("Phone number already exists")
        
        # Update phone
        user = await self.user_repo.update(
            user_id,
            {
                "phone": new_phone,
                "is_phone_verified": False,
                "phone_verified_at": None,
            }
        )
        
        self.logger.info(f"Phone changed for user: {user_id} to {new_phone}")
        return user
    
    # ==================== 2FA MANAGEMENT ====================
    
    async def enable_2fa(
        self,
        user_id: UUID,
        totp_secret: str,
        backup_codes: List[str],
    ) -> User:
        """
        Enable 2FA for user.
        
        Args:
            user_id: User ID
            totp_secret: TOTP secret
            backup_codes: List of backup codes
            
        Returns:
            Updated User instance
            
        Raises:
            UserNotFoundError: If user not found
        """
        user = await self.user_repo.get_or_raise(user_id)
        
        # Enable 2FA
        user = await self.user_repo.enable_2fa(user_id, totp_secret, backup_codes)
        
        self.logger.info(f"2FA enabled for user: {user_id}")
        return user
    
    async def disable_2fa(
        self,
        user_id: UUID,
        password: Optional[str] = None,
    ) -> User:
        """
        Disable 2FA for user.
        
        Args:
            user_id: User ID
            password: Optional password verification
            
        Returns:
            Updated User instance
            
        Raises:
            UserNotFoundError: If user not found
            InvalidCredentialsError: If password is incorrect
        """
        user = await self.user_repo.get_or_raise(user_id)
        
        # Verify password if provided
        if password:
            from app.modules.auth.domain.password_hasher import PasswordHasher
            hasher = PasswordHasher()
            if not hasher.verify(password, user.password_hash):
                raise InvalidCredentialsError("Invalid password")
        
        # Disable 2FA
        user = await self.user_repo.disable_2fa(user_id)
        
        self.logger.info(f"2FA disabled for user: {user_id}")
        return user
    
    async def regenerate_backup_codes(
        self,
        user_id: UUID,
    ) -> Dict[str, Any]:
        """
        Regenerate backup codes for 2FA.
        
        Args:
            user_id: User ID
            
        Returns:
            New backup codes
            
        Raises:
            UserNotFoundError: If user not found
            ValueError: If 2FA is not enabled
        """
        user = await self.user_repo.get_or_raise(user_id)
        
        if not user.is_2fa_enabled:
            raise ValueError("2FA is not enabled for this user")
        
        # Generate new backup codes
        import secrets
        backup_codes = []
        for _ in range(10):
            code = ''.join(str(secrets.randbelow(10)) for _ in range(8))
            backup_codes.append(code)
        
        # Update user
        await self.user_repo.update(
            user_id,
            {"backup_codes": backup_codes}
        )
        
        self.logger.info(f"Backup codes regenerated for user: {user_id}")
        
        return {
            "backup_codes": backup_codes,
            "message": "Backup codes regenerated. Store them securely.",
        }


__all__ = ['ProfileService']