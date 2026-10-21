from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import AuditAction
from app.core.exceptions import UnauthorizedError
from app.core.security import hash_password, verify_password
from app.core.tokens import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from app.modules.audit.service import AuditService
from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository
from app.modules.auth.schemas import LoginRequest, TokenPair

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW = timedelta(minutes=15)
_CLOCK_SKEW = timedelta(seconds=1)

# Lazily-computed dummy hash — equalizes timing when the user does not exist.
_dummy_hash: str | None = None


def _get_dummy_hash() -> str:
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = hash_password("__noctra_login_timing_dummy__")
    return _dummy_hash


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.audit = AuditService(db)

    # ── Login ────────────────────────────────────────────────

    async def login(
        self,
        payload: LoginRequest,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User, TokenPair]:
        user = await self.users.by_username(payload.username)

        if user and user.locked_until and user.locked_until > datetime.now(UTC):
            await self.audit.log(
                action=AuditAction.LOGIN_FAILED,
                table_name="users",
                record_id=user.id,
                ip_address=ip,
                user_agent=user_agent,
            )
            raise UnauthorizedError("Account temporarily locked. Try again later.")

        # Always run bcrypt — even when the user does not exist — so that
        # an attacker cannot enumerate usernames via response timing.
        password_ok = verify_password(
            payload.password,
            user.hashed_password if user else _get_dummy_hash(),
        )

        if not user or not password_ok:
            if user:
                # Re-fetch with SELECT ... FOR UPDATE and a fresh read of
                # `failed_login_attempts`. Two parallel failures would
                # otherwise both read the same count and both write `+1`,
                # losing an increment — an attacker could exceed the
                # 5-attempt lockout by firing requests in parallel.
                locked = await self.users.by_username(
                    payload.username, for_update=True
                )
                if locked is not None:
                    locked.failed_login_attempts += 1
                    if locked.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                        locked.locked_until = datetime.now(UTC) + LOCKOUT_WINDOW
                        locked.failed_login_attempts = 0

            await self.audit.log(
                action=AuditAction.LOGIN_FAILED,
                table_name="users",
                record_id=user.id if user else "anonymous",
                ip_address=ip,
                user_agent=user_agent,
            )
            # Commit explicitly so the counter / audit row persist even
            # though we raise immediately. (DBSessionMiddleware will also
            # commit on AppError; the explicit call is intentional for
            # auth's defence-in-depth.)
            await self.db.commit()
            raise UnauthorizedError("Invalid username or password")

        if not user.is_active:
            await self.audit.log(
                action=AuditAction.LOGIN_FAILED,
                table_name="users",
                record_id=user.id,
                ip_address=ip,
                user_agent=user_agent,
            )
            await self.db.commit()
            raise UnauthorizedError("Account is disabled")

        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.now(UTC)

        tokens = self._issue_tokens(user)

        await self.audit.log(
            action=AuditAction.LOGIN,
            table_name="users",
            record_id=user.id,
            user_id=user.id,
            ip_address=ip,
            user_agent=user_agent,
        )
        return user, tokens

    # ── Refresh ──────────────────────────────────────────────

    async def refresh(
        self, refresh_token: str, *, ip: str | None = None
    ) -> TokenPair:
        try:
            payload = decode_refresh_token(refresh_token)
        except ValueError as exc:
            raise UnauthorizedError("Invalid refresh token") from exc

        user = await self.users.get(UUID(payload.sub))
        if not user or not user.is_active:
            raise UnauthorizedError("User not found or inactive")

        # Same invalidation rule as `get_current_user`. Without this,
        # a stolen refresh token could obtain a fresh access token even
        # after the victim's password is reset, defeating the entire
        # force-logout mechanism for stateless JWTs.
        if user.password_changed_at is not None:
            token_iat = datetime.fromtimestamp(payload.iat, tz=UTC)
            if token_iat < user.password_changed_at - _CLOCK_SKEW:
                raise UnauthorizedError(
                    "Session expired — password was changed. Please log in again."
                )

        await self.audit.log(
            action=AuditAction.REFRESH,
            table_name="users",
            record_id=user.id,
            user_id=user.id,
            ip_address=ip,
        )
        return self._issue_tokens(user)

    # ── Logout ───────────────────────────────────────────────

    async def logout(
        self,
        *,
        user_id: UUID | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        if user_id is None:
            return
        await self.audit.log(
            action=AuditAction.LOGOUT,
            table_name="users",
            record_id=user_id,
            user_id=user_id,
            ip_address=ip,
            user_agent=user_agent,
        )

    # ── Internals ────────────────────────────────────────────

    @staticmethod
    def _issue_tokens(user: User) -> TokenPair:
        return TokenPair(
            access_token=create_access_token(
                str(user.id), {"username": user.username}
            ),
            refresh_token=create_refresh_token(str(user.id)),
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_expires_in=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        )