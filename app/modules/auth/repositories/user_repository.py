# app/modules/auth/repositories/user_repository.py
"""
User repository for user management operations.
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.base_repository import BaseRepository
from app.modules.auth.models.user import User
from app.modules.auth.enums import UserStatus, UserRole, AuthMethod
from app.core.exceptions import NotFoundError, DatabaseError
from app.core.logging import get_logger

logger = get_logger(__name__)


class UserRepository(BaseRepository[User]):
    """
    Repository for User model operations.
    
    Handles user account management, authentication, and profile operations.
    """
    
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)
    
    # ==================== CREATE OPERATIONS ====================
    
    async def create_user(
        self,
        email: str,
        password_hash: str,
        role: UserRole = UserRole.CUSTOMER,
        status: UserStatus = UserStatus.PENDING,
        auth_method: AuthMethod = AuthMethod.PASSWORD,
        full_name: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        username: Optional[str] = None,
        locale: str = "en",
        metadata: Optional[Dict[str, Any]] = None,
        created_by: Optional[UUID] = None,
        commit: bool = True
    ) -> User:
        """
        Create a new user.
        
        Args:
            email: User email
            password_hash: Hashed password
            role: User role
            status: User status
            auth_method: Authentication method
            full_name: Full name
            first_name: First name
            last_name: Last name
            phone: Phone number
            username: Username
            locale: User locale
            metadata: Additional metadata
            created_by: User ID who created this record
            commit: Whether to commit immediately
            
        Returns:
            Created User instance
        """
        data = {
            "email": email,
            "password_hash": password_hash,
            "role": role,
            "status": status,
            "auth_method": auth_method,
            "full_name": full_name,
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "username": username,
            "locale": locale,
            "metadata": metadata,
            "created_by": created_by,
        }
        
        return await self.create(data, commit=commit)
    
    # ==================== QUERY OPERATIONS ====================
    
    async def get_by_email(
        self,
        email: str,
        include_deleted: bool = False,
        load_relations: Optional[List[str]] = None
    ) -> Optional[User]:
        """
        Get user by email.
        
        Args:
            email: User email
            include_deleted: Whether to include soft-deleted records
            load_relations: List of relationship names to eager load
            
        Returns:
            User instance or None
        """
        return await self.get_by_field('email', email, include_deleted, load_relations)
    
    async def get_by_email_or_raise(
        self,
        email: str,
        load_relations: Optional[List[str]] = None
    ) -> User:
        """
        Get user by email or raise NotFoundError.
        
        Args:
            email: User email
            load_relations: List of relationship names to eager load
            
        Returns:
            User instance
            
        Raises:
            NotFoundError: If user not found
        """
        user = await self.get_by_email(email, load_relations=load_relations)
        if not user:
            raise NotFoundError(f"User with email {email} not found")
        return user
    
    async def get_by_phone(
        self,
        phone: str,
        include_deleted: bool = False
    ) -> Optional[User]:
        """
        Get user by phone number.
        
        Args:
            phone: User phone number
            include_deleted: Whether to include soft-deleted records
            
        Returns:
            User instance or None
        """
        return await self.get_by_field('phone', phone, include_deleted)
    
    async def get_by_username(
        self,
        username: str,
        include_deleted: bool = False
    ) -> Optional[User]:
        """
        Get user by username.
        
        Args:
            username: Username
            include_deleted: Whether to include soft-deleted records
            
        Returns:
            User instance or None
        """
        return await self.get_by_field('username', username, include_deleted)
    
    async def get_by_identifier(
        self,
        identifier: str,
        include_deleted: bool = False
    ) -> Optional[User]:
        """
        Get user by any identifier (email, phone, or username).
        
        Args:
            identifier: Email, phone, or username
            include_deleted: Whether to include soft-deleted records
            
        Returns:
            User instance or None
        """
        query = self._build_base_query(include_deleted)
        query = query.where(
            or_(
                self.model.email == identifier,
                self.model.phone == identifier,
                self.model.username == identifier,
            )
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_active_users(
        self,
        limit: int = 50,
        offset: int = 0,
        role: Optional[UserRole] = None
    ) -> List[User]:
        """
        Get active users.
        
        Args:
            limit: Maximum number of records
            offset: Offset for pagination
            role: Optional role filter
            
        Returns:
            List of active users
        """
        query = select(User).where(
            User.status == UserStatus.ACTIVE,
            User.is_active == True
        )
        
        if role:
            query = query.where(User.role == role)
        
        query = query.order_by(User.created_at.desc()).offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_users_by_role(
        self,
        role: UserRole,
        include_inactive: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[User]:
        """
        Get users by role.
        
        Args:
            role: User role
            include_inactive: Whether to include inactive users
            limit: Maximum number of records
            offset: Offset for pagination
            
        Returns:
            List of users
        """
        query = select(User).where(User.role == role)
        
        if not include_inactive:
            query = query.where(User.status == UserStatus.ACTIVE, User.is_active == True)
        
        query = query.order_by(User.created_at.desc()).offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_users_by_status(
        self,
        status: UserStatus,
        limit: int = 50,
        offset: int = 0
    ) -> List[User]:
        """
        Get users by status.
        
        Args:
            status: User status
            limit: Maximum number of records
            offset: Offset for pagination
            
        Returns:
            List of users
        """
        query = select(User).where(
            User.status == status,
            User.is_active == True
        ).order_by(User.created_at.desc()).offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_pending_users(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[User]:
        """
        Get pending users (email not verified).
        
        Args:
            limit: Maximum number of records
            offset: Offset for pagination
            
        Returns:
            List of pending users
        """
        return await self.get_users_by_status(UserStatus.PENDING, limit, offset)
    
    async def get_unverified_users(
        self,
        days: int = 7,
        limit: int = 50
    ) -> List[User]:
        """
        Get users who haven't verified their email.
        
        Args:
            days: Number of days to look back
            limit: Maximum number of records
            
        Returns:
            List of unverified users
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        query = select(User).where(
            User.is_email_verified == False,
            User.status == UserStatus.PENDING,
            User.created_at >= cutoff,
            User.is_active == True
        ).order_by(User.created_at.asc()).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    # ==================== UPDATE OPERATIONS ====================
    
    async def update_password(
        self,
        user_id: UUID,
        new_password_hash: str,
        commit: bool = True
    ) -> User:
        """
        Update user password.
        
        Args:
            user_id: User ID
            new_password_hash: New hashed password
            commit: Whether to commit immediately
            
        Returns:
            Updated User instance
            
        Raises:
            NotFoundError: If user not found
        """
        user = await self.get_or_raise(user_id)
        user.change_password(new_password_hash)
        
        if commit:
            await self.db.commit()
            await self.db.refresh(user)
        
        return user
    
    async def update_last_login(
        self,
        user_id: UUID,
        ip_address: Optional[str] = None,
        commit: bool = True
    ) -> User:
        """
        Update user last login information.
        
        Args:
            user_id: User ID
            ip_address: Client IP address
            commit: Whether to commit immediately
            
        Returns:
            Updated User instance
            
        Raises:
            NotFoundError: If user not found
        """
        user = await self.get_or_raise(user_id)
        user.update_last_login(ip_address)
        
        if commit:
            await self.db.commit()
            await self.db.refresh(user)
        
        return user
    
    async def verify_email(
        self,
        user_id: UUID,
        commit: bool = True
    ) -> User:
        """
        Verify user email.
        
        Args:
            user_id: User ID
            commit: Whether to commit immediately
            
        Returns:
            Updated User instance
            
        Raises:
            NotFoundError: If user not found
        """
        user = await self.get_or_raise(user_id)
        user.verify_email()
        
        # If user was pending, activate them
        if user.status == UserStatus.PENDING:
            user.activate()
        
        if commit:
            await self.db.commit()
            await self.db.refresh(user)
        
        return user
    
    async def verify_phone(
        self,
        user_id: UUID,
        commit: bool = True
    ) -> User:
        """
        Verify user phone.
        
        Args:
            user_id: User ID
            commit: Whether to commit immediately
            
        Returns:
            Updated User instance
            
        Raises:
            NotFoundError: If user not found
        """
        user = await self.get_or_raise(user_id)
        user.verify_phone()
        
        if commit:
            await self.db.commit()
            await self.db.refresh(user)
        
        return user
    
    async def update_role(
        self,
        user_id: UUID,
        new_role: UserRole,
        commit: bool = True
    ) -> User:
        """
        Update user role.
        
        Args:
            user_id: User ID
            new_role: New user role
            commit: Whether to commit immediately
            
        Returns:
            Updated User instance
            
        Raises:
            NotFoundError: If user not found
        """
        user = await self.get_or_raise(user_id)
        user.role = new_role
        
        if commit:
            await self.db.commit()
            await self.db.refresh(user)
        
        return user
    
    async def update_profile(
        self,
        user_id: UUID,
        data: Dict[str, Any],
        commit: bool = True
    ) -> User:
        """
        Update user profile.
        
        Args:
            user_id: User ID
            data: Profile data to update
            commit: Whether to commit immediately
            
        Returns:
            Updated User instance
            
        Raises:
            NotFoundError: If user not found
        """
        # Filter allowed fields
        allowed_fields = {
            'full_name', 'first_name', 'last_name', 'phone',
            'username', 'avatar_url', 'locale', 'timezone'
        }
        
        filtered_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        return await self.update(user_id, filtered_data, commit)
    
    # ==================== STATUS OPERATIONS ====================
    
    async def activate_user(
        self,
        user_id: UUID,
        commit: bool = True
    ) -> User:
        """
        Activate a user account.
        
        Args:
            user_id: User ID
            commit: Whether to commit immediately
            
        Returns:
            Updated User instance
            
        Raises:
            NotFoundError: If user not found
        """
        user = await self.get_or_raise(user_id)
        user.activate()
        
        if commit:
            await self.db.commit()
            await self.db.refresh(user)
        
        return user
    
    async def suspend_user(
        self,
        user_id: UUID,
        commit: bool = True
    ) -> User:
        """
        Suspend a user account.
        
        Args:
            user_id: User ID
            commit: Whether to commit immediately
            
        Returns:
            Updated User instance
            
        Raises:
            NotFoundError: If user not found
        """
        user = await self.get_or_raise(user_id)
        user.suspend()
        
        if commit:
            await self.db.commit()
            await self.db.refresh(user)
        
        return user
    
    async def ban_user(
        self,
        user_id: UUID,
        reason: Optional[str] = None,
        commit: bool = True
    ) -> User:
        """
        Ban a user account.
        
        Args:
            user_id: User ID
            reason: Ban reason
            commit: Whether to commit immediately
            
        Returns:
            Updated User instance
            
        Raises:
            NotFoundError: If user not found
        """
        user = await self.get_or_raise(user_id)
        user.ban(reason)
        
        if commit:
            await self.db.commit()
            await self.db.refresh(user)
        
        return user
    
    async def unban_user(
        self,
        user_id: UUID,
        commit: bool = True
    ) -> User:
        """
        Unban a user account.
        
        Args:
            user_id: User ID
            commit: Whether to commit immediately
            
        Returns:
            Updated User instance
            
        Raises:
            NotFoundError: If user not found
        """
        user = await self.get_or_raise(user_id)
        user.unban()
        
        if commit:
            await self.db.commit()
            await self.db.refresh(user)
        
        return user
    
    # ==================== 2FA OPERATIONS ====================
    
    async def enable_2fa(
        self,
        user_id: UUID,
        totp_secret: str,
        backup_codes: List[str],
        commit: bool = True
    ) -> User:
        """
        Enable 2FA for a user.
        
        Args:
            user_id: User ID
            totp_secret: TOTP secret key
            backup_codes: List of backup codes
            commit: Whether to commit immediately
            
        Returns:
            Updated User instance
            
        Raises:
            NotFoundError: If user not found
        """
        user = await self.get_or_raise(user_id)
        user.enable_2fa(totp_secret, backup_codes)
        
        if commit:
            await self.db.commit()
            await self.db.refresh(user)
        
        return user
    
    async def disable_2fa(
        self,
        user_id: UUID,
        commit: bool = True
    ) -> User:
        """
        Disable 2FA for a user.
        
        Args:
            user_id: User ID
            commit: Whether to commit immediately
            
        Returns:
            Updated User instance
            
        Raises:
            NotFoundError: If user not found
        """
        user = await self.get_or_raise(user_id)
        user.disable_2fa()
        
        if commit:
            await self.db.commit()
            await self.db.refresh(user)
        
        return user
    
    # ==================== VALIDATION OPERATIONS ====================
    
    async def email_exists(
        self,
        email: str,
        exclude_id: Optional[UUID] = None
    ) -> bool:
        """
        Check if email already exists.
        
        Args:
            email: Email to check
            exclude_id: User ID to exclude from check
            
        Returns:
            True if email exists
        """
        return await self.exists_by_field('email', email, exclude_id)
    
    async def phone_exists(
        self,
        phone: str,
        exclude_id: Optional[UUID] = None
    ) -> bool:
        """
        Check if phone number already exists.
        
        Args:
            phone: Phone number to check
            exclude_id: User ID to exclude from check
            
        Returns:
            True if phone exists
        """
        if not phone:
            return False
        return await self.exists_by_field('phone', phone, exclude_id)
    
    async def username_exists(
        self,
        username: str,
        exclude_id: Optional[UUID] = None
    ) -> bool:
        """
        Check if username already exists.
        
        Args:
            username: Username to check
            exclude_id: User ID to exclude from check
            
        Returns:
            True if username exists
        """
        if not username:
            return False
        return await self.exists_by_field('username', username, exclude_id)
    
    # ==================== STATISTICS OPERATIONS ====================
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get user statistics.
        
        Returns:
            Dictionary with user statistics
        """
        # Total users
        total_query = select(func.count()).select_from(User).where(User.is_active == True)
        total_result = await self.db.execute(total_query)
        total_users = total_result.scalar_one() or 0
        
        # Users by status
        status_query = select(
            User.status,
            func.count().label("count")
        ).select_from(User).where(
            User.is_active == True
        ).group_by(User.status)
        
        status_result = await self.db.execute(status_query)
        status_breakdown = {row.status.value: row.count for row in status_result.all()}
        
        # Users by role
        role_query = select(
            User.role,
            func.count().label("count")
        ).select_from(User).where(
            User.is_active == True
        ).group_by(User.role)
        
        role_result = await self.db.execute(role_query)
        role_breakdown = {row.role.value: row.count for row in role_result.all()}
        
        # Verified vs unverified
        verified_query = select(
            func.count().label("verified")
        ).select_from(User).where(
            User.is_email_verified == True,
            User.is_active == True
        )
        verified_result = await self.db.execute(verified_query)
        verified_count = verified_result.scalar_one() or 0
        
        # 2FA enabled
        twofa_query = select(
            func.count().label("twofa")
        ).select_from(User).where(
            User.is_2fa_enabled == True,
            User.is_active == True
        )
        twofa_result = await self.db.execute(twofa_query)
        twofa_count = twofa_result.scalar_one() or 0
        
        return {
            "total_users": total_users,
            "status_breakdown": status_breakdown,
            "role_breakdown": role_breakdown,
            "email_verified": verified_count,
            "email_unverified": total_users - verified_count,
            "twofa_enabled": twofa_count,
        }


__all__ = ['UserRepository']