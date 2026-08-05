# modules/auth/services.py
from uuid import UUID
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict, Any
import secrets

from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from jose import jwt, JWTError

from core.config import settings
from core.exceptions import (
    NotFoundError,
    ValidationError,
    UnauthorizedError,
    BusinessError
)
from core.constants import UserStatus
from .models import User, Role, Permission, RefreshToken
from .repository import (
    UserRepository,
    RoleRepository,
    PermissionRepository,
    RefreshTokenRepository
)
from .schemas import UserCreate, UserLogin, UserRegister, ChangePasswordRequest


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class PasswordService:
    """Service untuk password management."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt."""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def generate_reset_token() -> str:
        """Generate password reset token."""
        return secrets.token_urlsafe(32)


class TokenService:
    """Service untuk token management."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.refresh_repo = RefreshTokenRepository(db)

    def create_access_token(self, user_id: UUID, username: str) -> str:
        """Create JWT access token."""
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        expire = datetime.utcnow() + expires_delta

        to_encode = {
            "sub": str(user_id),
            "username": username,
            "exp": expire,
            "type": "access"
        }
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    def create_refresh_token(self) -> Tuple[str, datetime]:
        """Create refresh token string and expiry."""
        token = secrets.token_urlsafe(64)
        expires_at = datetime.now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        return token, expires_at

    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode JWT token."""
        try:
            return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except JWTError:
            return {}

    def validate_access_token(self, token: str) -> Optional[UUID]:
        """Validate access token and return user_id."""
        payload = self.decode_token(token)
        if not payload:
            return None

        user_id = payload.get("sub")
        token_type = payload.get("type")

        if not user_id or token_type != "access":
            return None

        try:
            return UUID(user_id)
        except ValueError:
            return None

    async def validate_refresh_token(self, token: str) -> Optional[UUID]:
        """Validate refresh token and return user_id."""
        refresh_token = await self.refresh_repo.get_by_token(token)
        if not refresh_token or not refresh_token.is_valid:
            return None

        return refresh_token.user_id

    async def store_refresh_token(
        self,
        user_id: UUID,
        token: str,
        expires_at: datetime,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> RefreshToken:
        """Store refresh token."""
        return await self.refresh_repo.create_token(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )


class AuthService:
    """Service untuk authentication."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)
        self.permission_repo = PermissionRepository(db)
        self.token_service = TokenService(db)
        self.password_service = PasswordService()

    # =========================================================================
    # Registration & Login
    # =========================================================================

    async def register(self, data: UserRegister, ip_address: Optional[str] = None) -> User:
        """Register new user."""
        # Check if username exists
        existing_username = await self.user_repo.get_by_username(data.username)
        if existing_username:
            raise ValidationError(f"Username '{data.username}' already exists")

        # Check if email exists
        existing_email = await self.user_repo.get_by_email(data.email)
        if existing_email:
            raise ValidationError(f"Email '{data.email}' already exists")

        # Hash password
        password_hash = self.password_service.hash_password(data.password)

        # Create user
        user_data = data.model_dump(exclude={"password"})
        user = User(
            **user_data,
            password_hash=password_hash,
            status=UserStatus.ACTIVE,
            is_verified=False,
            failed_login_attempts=0
        )

        # Assign default role (if exists)
        default_role = await self.role_repo.get_by_name("user")
        if default_role:
            await self.user_repo.assign_role(user.id, default_role.id)

        user = await self.user_repo.create(user)

        # Add to database
        await self.db.flush()
        await self.db.refresh(user)

        return user

    async def login(self, data: UserLogin, ip_address: Optional[str] = None) -> Dict[str, Any]:
        """Login user."""
        # Find user by username or email
        user = await self.user_repo.get_by_username_or_email(data.username_or_email)
        if not user:
            raise UnauthorizedError("Invalid credentials")

        # Check if user is locked
        if user.is_locked:
            raise UnauthorizedError(
                f"Account is locked. Try again after {user.locked_until.strftime('%Y-%m-%d %H:%M')}"
            )

        # Check status
        if user.status == UserStatus.SUSPENDED:
            raise UnauthorizedError(
                "Account is suspended. Contact administrator")
        if user.status == UserStatus.INACTIVE:
            raise UnauthorizedError(
                "Account is inactive. Contact administrator")

        # Verify password
        if not self.password_service.verify_password(data.password, user.password_hash):
            await self.user_repo.increment_failed_login(user.id)
            await self.db.flush()
            raise UnauthorizedError("Invalid credentials")

        # Reset failed login attempts
        await self.user_repo.reset_failed_login(user.id)

        # Update last login
        await self.user_repo.update_last_login(user.id, ip_address)

        # Generate tokens
        access_token = self.token_service.create_access_token(
            user.id, user.username)
        refresh_token_str, expires_at = self.token_service.create_refresh_token()

        # Store refresh token
        await self.token_service.store_refresh_token(
            user_id=user.id,
            token=refresh_token_str,
            expires_at=expires_at,
            ip_address=ip_address
        )

        # Get user with roles
        user_with_roles = await self.user_repo.get_with_roles(user.id)
        permissions = await self.user_repo.get_user_permissions(user.id)

        await self.db.flush()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token_str,
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": user_with_roles,
            "permissions": permissions
        }

    async def refresh_token(self, refresh_token: str, ip_address: Optional[str] = None) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        # Validate refresh token
        user_id = await self.token_service.validate_refresh_token(refresh_token)
        if not user_id:
            raise UnauthorizedError("Invalid or expired refresh token")

        # Get user
        user = await self.user_repo.get_with_roles(user_id)
        if not user:
            raise UnauthorizedError("User not found")

        if user.status != UserStatus.ACTIVE:
            raise UnauthorizedError("Account is not active")

        # Revoke old refresh token
        await self.token_service.revoke_token(refresh_token, "Refreshed")

        # Generate new tokens
        access_token = self.token_service.create_access_token(
            user.id, user.username)
        new_refresh_token, expires_at = self.token_service.create_refresh_token()

        # Store new refresh token
        await self.token_service.store_refresh_token(
            user_id=user.id,
            token=new_refresh_token,
            expires_at=expires_at,
            ip_address=ip_address
        )

        permissions = await self.user_repo.get_user_permissions(user.id)

        await self.db.flush()

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": user,
            "permissions": permissions
        }

    async def logout(self, refresh_token: str) -> bool:
        """Logout user."""
        return await self.token_service.revoke_token(refresh_token, "User logged out")

    async def logout_all(self, user_id: UUID) -> int:
        """Logout user from all devices."""
        return await self.token_service.revoke_all_user_tokens(user_id, "User logged out from all devices")

    # =========================================================================
    # User Management
    # =========================================================================

    async def get_user(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        return await self.user_repo.get_with_roles(user_id)

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return await self.user_repo.get_by_username(username)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return await self.user_repo.get_by_email(email)

    async def get_current_user(self, user_id: UUID) -> Optional[User]:
        """Get current user with roles and permissions."""
        return await self.user_repo.get_with_roles(user_id)

    async def update_user(self, user_id: UUID, data: Dict[str, Any]) -> Optional[User]:
        """Update user."""
        user = await self.user_repo.get(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")

        # Update roles if provided
        if "role_ids" in data:
            role_ids = data.pop("role_ids")
            # Get current roles
            current_roles = await self.user_repo.get_user_roles(user_id)
            current_role_ids = [r.id for r in user.roles if r.role]

            # Add new roles
            for role_id in role_ids:
                if role_id not in current_role_ids:
                    await self.user_repo.assign_role(user_id, role_id)

            # Remove old roles
            for role in user.roles:
                if role.role_id not in role_ids:
                    await self.user_repo.remove_role(user_id, role.role_id)

        user = await self.user_repo.update(user_id, data)
        await self.db.flush()
        return user

    async def change_password(self, user_id: UUID, data: ChangePasswordRequest) -> bool:
        """Change user password."""
        user = await self.user_repo.get(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")

        # Verify old password
        if not self.password_service.verify_password(data.old_password, user.password_hash):
            raise ValidationError("Old password is incorrect")

        # Hash new password
        user.password_hash = self.password_service.hash_password(
            data.new_password)
        await self.db.flush()
        return True

    async def reset_password(self, email: str) -> str:
        """Reset password for user (generate reset token)."""
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise NotFoundError(f"User with email {email} not found")

        # Generate reset token
        reset_token = self.password_service.generate_reset_token()

        # TODO: Send email with reset link
        # await self.email_service.send_password_reset(user.email, reset_token)

        return reset_token

    # =========================================================================
    # Role & Permission Management
    # =========================================================================

    async def get_role(self, role_id: UUID) -> Optional[Role]:
        """Get role by ID."""
        return await self.role_repo.get_with_permissions(role_id)

    async def get_role_by_name(self, name: str) -> Optional[Role]:
        """Get role by name."""
        return await self.role_repo.get_by_name(name)

    async def create_role(self, data: Dict[str, Any]) -> Role:
        """Create new role."""
        role = Role(**data)
        role = await self.role_repo.create(role)

        if "permission_ids" in data and data["permission_ids"]:
            for perm_id in data["permission_ids"]:
                await self.role_repo.assign_permission(role.id, perm_id)

        await self.db.flush()
        await self.db.refresh(role)
        return role

    async def update_role(self, role_id: UUID, data: Dict[str, Any]) -> Optional[Role]:
        """Update role."""
        role = await self.role_repo.get(role_id)
        if not role:
            raise NotFoundError(f"Role {role_id} not found")

        # Update permissions if provided
        if "permission_ids" in data:
            perm_ids = data.pop("permission_ids")
            # Get current permissions
            current_perms = [rp.permission_id for rp in role.permissions]

            # Add new permissions
            for perm_id in perm_ids:
                if perm_id not in current_perms:
                    await self.role_repo.assign_permission(role_id, perm_id)

            # Remove old permissions
            for role_perm in role.permissions:
                if role_perm.permission_id not in perm_ids:
                    await self.role_repo.remove_permission(role_id, role_perm.permission_id)

        role = await self.role_repo.update(role_id, data)
        await self.db.flush()
        return role

    async def get_permissions(self, module: Optional[str] = None) -> List[Permission]:
        """Get all permissions."""
        if module:
            return await self.permission_repo.get_by_module(module)
        return await self.permission_repo.get_all()

    async def has_permission(self, user_id: UUID, permission: str) -> bool:
        """Check if user has a specific permission."""
        user = await self.user_repo.get_with_roles(user_id)
        if not user:
            return False

        # Superuser has all permissions
        if user.is_superuser:
            return True

        permissions = await self.user_repo.get_user_permissions(user_id)
        return permission in permissions

    async def has_permission_module(self, user_id: UUID, module: str, action: str) -> bool:
        """Check if user has module:action permission."""
        return await self.has_permission(user_id, f"{module}:{action}")
