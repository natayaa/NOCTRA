# app/modules/auth/services/authentication_service.py
"""
Authentication service for login, logout, token management.
"""

from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from uuid import UUID

from app.shared.base_service import BaseService
from app.modules.auth.domain.jwt_manager import JWTManager
from app.modules.auth.domain.token_factory import TokenFactory
from app.modules.auth.domain.password_hasher import PasswordHasher
from app.modules.auth.domain.session_manager import SessionManager
from app.modules.auth.domain.validator import AuthValidator

from app.modules.auth.repositories.user_repository import UserRepository
from app.modules.auth.repositories.session_repository import SessionRepository
from app.modules.auth.repositories.token_repository import TokenRepository
from app.modules.auth.repositories.login_history_repository import LoginHistoryRepository
from app.modules.auth.repositories.failed_login_repository import FailedLoginRepository

from app.modules.auth.models.user import User
from app.modules.auth.models.session import Session

from app.modules.auth.enums import UserStatus, UserRole, LoginType, AuthMethod, TokenType
from app.modules.auth.exceptions import (
    InvalidCredentialsError,
    AccountLockedError,
    AccountSuspendedError,
    AccountBannedError,
    AccountNotVerifiedError,
    TokenExpiredError,
    TokenInvalidError,
    TokenRevokedError,
    TokenMissingError,
    RateLimitExceededError,
    UserNotFoundError,
)

from app.core.logging import get_logger
from app.core.config import settings
from jose.exceptions import ExpiredSignatureError, JWTError

logger = get_logger(__name__)


class AuthenticationService:
    """
    Authentication service for login, logout, token management.
    
    Handles user authentication flow including:
    - Login with email/phone/username
    - Token creation and refresh
    - Logout and session termination
    - Rate limiting and security checks
    """
    
    def __init__(
        self,
        user_repo: UserRepository,
        session_repo: SessionRepository,
        token_repo: TokenRepository,
        login_history_repo: LoginHistoryRepository,
        failed_login_repo: FailedLoginRepository,
        password_hasher: Optional[PasswordHasher] = None,
        token_factory: Optional[TokenFactory] = None,
        session_manager: Optional[SessionManager] = None,
    ):
        self.user_repo = user_repo
        self.session_repo = session_repo
        self.token_repo = token_repo
        self.login_history_repo = login_history_repo
        self.failed_login_repo = failed_login_repo
        
        self.password_hasher = password_hasher or PasswordHasher()
        self.token_factory = token_factory or TokenFactory()
        self.session_manager = session_manager or SessionManager()
        
        self.logger = get_logger(self.__class__.__name__)
    
    # ==================== LOGIN ====================
    
    async def login(
        self,
        identifier: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        login_type: LoginType = LoginType.WEB,
        device_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Authenticate user and create session with tokens.
        
        Args:
            identifier: Email, phone, or username
            password: Plain text password
            ip_address: Client IP address
            user_agent: Client user agent
            login_type: Type of login
            device_info: Device information
            
        Returns:
            Dictionary with user, session, tokens, and login history
            
        Raises:
            InvalidCredentialsError: If credentials are invalid
            AccountLockedError: If account is locked
            AccountSuspendedError: If account is suspended
            AccountBannedError: If account is banned
            AccountNotVerifiedError: If account is not verified
            RateLimitExceededError: If too many failed attempts
        """
        # Check rate limiting
        await self._check_rate_limit(identifier, ip_address)
        
        # Find user by identifier
        user = await self.user_repo.get_by_identifier(identifier)
        
        if not user:
            # Log failed attempt
            await self._log_failed_attempt(identifier, ip_address, user_agent, login_type)
            raise InvalidCredentialsError("Invalid email, phone, or password")
        
        # Check account status
        self._validate_user_status(user)
        
        # Verify password
        if not self.password_hasher.verify(password, user.password_hash):
            # Log failed attempt
            await self._log_failed_attempt(identifier, ip_address, user_agent, login_type, user.id)
            raise InvalidCredentialsError("Invalid email, phone, or password")
        
        # Check if password needs rehash
        if self.password_hasher.need_rehash(user.password_hash):
            new_hash = self.password_hasher.hash(password)
            await self.user_repo.update_password(user.id, new_hash)
        
        # Check if 2FA is required
        requires_2fa = user.is_2fa_enabled
        
        # Create session
        session_data = self.session_manager.create_session_data(
            user_id=user.id,
            login_type=login_type,
            ip_address=ip_address,
            user_agent=user_agent,
            device_info=device_info,
        )
        
        session = await self.session_repo.create_session(**session_data)
        
        # Create token pair
        tokens = self.token_factory.create_token_pair(
            user_id=user.id,
            session_id=session.id,
            extra_data={
                "email": user.email,
                "role": user.role.value,
                "requires_2fa": requires_2fa,
            }
        )
        
        # Save tokens
        await self.token_repo.create_token_pair(
            access_token=tokens["access_token"],
            access_jti=tokens["access_jti"],
            refresh_token=tokens["refresh_token"],
            refresh_jti=tokens["refresh_jti"],
            session_id=session.id,
            user_id=user.id,
            access_expires_at=tokens["access_expires_at"],
            refresh_expires_at=tokens["refresh_expires_at"],
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        # Update user last login
        await self.user_repo.update_last_login(user.id, ip_address)
        
        # Log successful login
        await self.login_history_repo.log_successful_login(
            user_id=user.id,
            session_id=session.id,
            login_type=login_type,
            ip_address=ip_address,
            user_agent=user_agent,
            is_2fa_required=requires_2fa,
            is_2fa_verified=False,
        )
        
        self.logger.info(f"User logged in: {user.email} from {ip_address}")
        
        return {
            "user": user.to_dict(),
            "session": session.to_dict(),
            "tokens": {
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "access_expires_at": tokens["access_expires_at"].isoformat(),
                "refresh_expires_at": tokens["refresh_expires_at"].isoformat(),
            },
            "requires_2fa": requires_2fa,
        }
    
    # ==================== REFRESH TOKEN ====================
    
    async def refresh_tokens(
        self,
        refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token string
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            New token pair
            
        Raises:
            TokenExpiredError: If refresh token is expired
            TokenInvalidError: If refresh token is invalid
            TokenRevokedError: If refresh token is revoked
            TokenMissingError: If refresh token is missing
        """
        if not refresh_token:
            raise TokenMissingError("Refresh token required")
        
        # Validate refresh token
        try:
            payload = self.token_factory.jwt_manager.validate_token(
                refresh_token,
                expected_type=TokenType.REFRESH
            )
        except JWTError:
            raise TokenInvalidError("Invalid refresh token")
        except ExpiredSignatureError:
            raise TokenExpiredError("Refresh token has expired")
        
        # Get token from database
        token_record = await self.token_repo.get_refresh_token(refresh_token)
        if not token_record:
            raise TokenInvalidError("Refresh token not found")
        
        if token_record.is_expired:
            raise TokenExpiredError("Refresh token has expired")
        
        if token_record.is_revoked:
            raise TokenRevokedError("Refresh token has been revoked")
        
        # Get session
        session = await self.session_repo.get_or_raise(token_record.session_id)
        
        if not session.is_active:
            raise TokenInvalidError("Session is no longer active")
        
        # Get user
        user = await self.user_repo.get_or_raise(session.user_id)
        
        # Update session activity
        await self.session_repo.update_activity(session.id)
        
        # Create new token pair
        tokens = self.token_factory.create_token_pair(
            user_id=user.id,
            session_id=session.id,
            extra_data={
                "email": user.email,
                "role": user.role.value,
            }
        )
        
        # Revoke old refresh token
        await self.token_repo.revoke_refresh_token(
            refresh_token,
            revoked_by=user.id,
            commit=False
        )
        
        # Save new tokens
        await self.token_repo.create_token_pair(
            access_token=tokens["access_token"],
            access_jti=tokens["access_jti"],
            refresh_token=tokens["refresh_token"],
            refresh_jti=tokens["refresh_jti"],
            session_id=session.id,
            user_id=user.id,
            access_expires_at=tokens["access_expires_at"],
            refresh_expires_at=tokens["refresh_expires_at"],
            ip_address=ip_address or session.ip_address,
            user_agent=user_agent or session.user_agent,
        )
        
        self.logger.info(f"Tokens refreshed for user: {user.email}")
        
        return {
            "tokens": {
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "access_expires_at": tokens["access_expires_at"].isoformat(),
                "refresh_expires_at": tokens["refresh_expires_at"].isoformat(),
            },
        }
    
    # ==================== LOGOUT ====================
    
    async def logout(
        self,
        user_id: UUID,
        session_id: UUID,
        access_token: Optional[str] = None,
    ) -> bool:
        """
        Logout user by terminating session and revoking tokens.
        
        Args:
            user_id: User ID
            session_id: Session ID
            access_token: Optional access token to revoke
            
        Returns:
            True if logout successful
        """
        # Terminate session
        await self.session_repo.terminate_session(session_id, terminated_by=user_id)
        
        # Revoke all tokens for this session
        await self.token_repo.revoke_access_tokens_by_session(
            session_id,
            revoked_by=user_id
        )
        await self.token_repo.revoke_refresh_tokens_by_session(
            session_id,
            revoked_by=user_id
        )
        
        self.logger.info(f"User logged out: {user_id}")
        return True
    
    async def logout_all_devices(
        self,
        user_id: UUID,
        except_session_id: Optional[UUID] = None,
    ) -> int:
        """
        Logout user from all devices except one.
        
        Args:
            user_id: User ID
            except_session_id: Session ID to keep active
            
        Returns:
            Number of sessions terminated
        """
        # Terminate all sessions except one
        count = await self.session_repo.terminate_all_sessions(
            user_id,
            except_session_id=except_session_id,
            terminated_by=user_id,
        )
        
        self.logger.info(f"Logged out all devices for user: {user_id}")
        return count
    
    # ==================== TOKEN VALIDATION ====================
    
    async def validate_access_token(
        self,
        access_token: str,
    ) -> Dict[str, Any]:
        """
        Validate access token.
        
        Args:
            access_token: Access token string
            
        Returns:
            Validated token data
            
        Raises:
            TokenExpiredError: If token is expired
            TokenInvalidError: If token is invalid
            TokenRevokedError: If token is revoked
            TokenMissingError: If token is missing
        """
        if not access_token:
            raise TokenMissingError("Access token required")
        
        # Validate JWT
        try:
            payload = self.token_factory.jwt_manager.validate_token(
                access_token,
                expected_type=TokenType.ACCESS
            )
        except ExpiredSignatureError:
            raise TokenExpiredError("Access token has expired")
        except JWTError:
            raise TokenInvalidError("Invalid access token")
        
        # Check token in database
        token_record = await self.token_repo.get_access_token(access_token)
        if not token_record:
            raise TokenInvalidError("Access token not found")
        
        if token_record.is_revoked:
            raise TokenRevokedError("Access token has been revoked")
        
        if token_record.is_expired:
            raise TokenExpiredError("Access token has expired")
        
        # Update last used
        token_record.use()
        await self.db.commit()
        
        # Get user
        user = await self.user_repo.get_or_raise(payload.get("user_id"))
        
        return {
            "user_id": str(user.id),
            "user": user.to_dict(),
            "session_id": payload.get("session_id"),
            "expires_at": token_record.expires_at,
            "payload": payload,
        }
    
    # ==================== PRIVATE METHODS ====================
    
    async def _check_rate_limit(
        self,
        identifier: str,
        ip_address: Optional[str] = None,
    ) -> None:
        """
        Check rate limit for login attempts.
        
        Args:
            identifier: Email, phone, or username
            ip_address: Client IP address
            
        Raises:
            RateLimitExceededError: If rate limit exceeded
        """
        from app.modules.auth.constants import AuthConstants
        
        # Check attempts by identifier
        attempts = await self.failed_login_repo.get_attempt_count(
            identifier,
            minutes=5
        )
        
        if attempts >= AuthConstants.RATE_LIMIT_LOGIN:
            raise RateLimitExceededError(
                "Too many login attempts. Please try again later."
            )
        
        # Check attempts by IP
        if ip_address:
            attempts_by_ip = await self.failed_login_repo.get_attempt_count(
                ip_address,
                minutes=5
            )
            
            if attempts_by_ip >= AuthConstants.RATE_LIMIT_LOGIN * 2:
                raise RateLimitExceededError(
                    "Too many login attempts from this IP. Please try again later."
                )
    
    async def _log_failed_attempt(
        self,
        identifier: str,
        ip_address: Optional[str],
        user_agent: Optional[str],
        login_type: LoginType,
        user_id: Optional[UUID] = None,
    ) -> None:
        """
        Log a failed login attempt.
        
        Args:
            identifier: Email, phone, or username
            ip_address: Client IP address
            user_agent: Client user agent
            login_type: Type of login
            user_id: Optional user ID if found
        """
        # Log to failed login table
        await self.failed_login_repo.log_failed_attempt(
            identifier=identifier,
            identifier_type="email" if "@" in identifier else "username",
            ip_address=ip_address,
            user_agent=user_agent,
            login_type=login_type,
            reason="Invalid credentials",
            error_code="INVALID_CREDENTIALS",
        )
        
        # Log to login history if user_id is available
        if user_id:
            await self.login_history_repo.log_failed_login(
                user_id=user_id,
                login_type=login_type,
                ip_address=ip_address,
                user_agent=user_agent,
                failure_reason="Invalid credentials",
                error_code="INVALID_CREDENTIALS",
            )
    
    def _validate_user_status(self, user: User) -> None:
        """
        Validate user account status.
        
        Args:
            user: User instance
            
        Raises:
            AccountLockedError: If account is locked
            AccountSuspendedError: If account is suspended
            AccountBannedError: If account is banned
            AccountNotVerifiedError: If account is not verified
        """
        if user.status == UserStatus.SUSPENDED:
            raise AccountSuspendedError("Account has been suspended")
        
        if user.status == UserStatus.BANNED:
            raise AccountBannedError("Account has been banned")
        
        if user.status == UserStatus.PENDING:
            raise AccountNotVerifiedError("Account not verified")
        
        if user.status == UserStatus.DELETED:
            raise AccountLockedError("Account has been deleted")


__all__ = ['AuthenticationService']