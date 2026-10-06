from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import AuditAction
from app.core.exceptions import UnauthorizedError
from app.core.tokens import create_access_token, create_refresh_token, decode_token
from app.modules.audit.service import AuditService
from app.modules.auth.models import User
from app.core.security import verify_password
from app.modules.auth.repository import UserRepository
from app.modules.auth.schemas import LoginRequest, TokenPair

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW = timedelta(minutes=15)


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.audit = AuditService(db)

    async def login(
        self,
        payload: LoginRequest,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User, TokenPair]:
        user = await self.users.by_username(payload.username)

        if user and user.locked_until and user.locked_until > datetime.now(UTC):
            raise UnauthorizedError("Account temporarily locked. Try again later.")

        if not user or not verify_password(payload.password, user.hashed_password):
            if user:
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                    user.locked_until = datetime.now(UTC) + LOCKOUT_WINDOW
                    user.failed_login_attempts = 0
            await self.audit.log(
                action=AuditAction.LOGIN_FAILED,
                table_name="users",
                record_id=user.id if user else "unknown",
                ip_address=ip,
                user_agent=user_agent,
            )
            await self.db.commit()      # ← add this
            raise UnauthorizedError("Invalid username or password")

        if not user.is_active:
            raise UnauthorizedError("Account is disabled")

        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.now(UTC)

        tokens = TokenPair(
            access_token=create_access_token(str(user.id), {"username": user.username}),
            refresh_token=create_refresh_token(str(user.id)),
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

        await self.audit.log(
            action=AuditAction.LOGIN,
            table_name="users",
            record_id=user.id,
            user_id=user.id,
            ip_address=ip,
            user_agent=user_agent,
        )
        return user, tokens

    async def refresh(self, refresh_token: str) -> TokenPair:
        try:
            payload = decode_token(refresh_token)
        except ValueError as exc:
            raise UnauthorizedError("Invalid refresh token") from exc
        if payload.typ != "refresh":
            raise UnauthorizedError("Wrong token type")

        from uuid import UUID

        user = await self.users.get(UUID(payload.sub))
        if not user or not user.is_active:
            raise UnauthorizedError("User not found or inactive")

        return TokenPair(
            access_token=create_access_token(str(user.id), {"username": user.username}),
            refresh_token=create_refresh_token(str(user.id)),
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )