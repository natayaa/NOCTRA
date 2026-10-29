"""Self-service password reset.

Flow:
    POST /admin/forgot-password  → always the same answer (no account
    enumeration); if the account exists and has an email, a signed link
    is queued.
    GET  /admin/reset-password?token=…  → form.
    POST /admin/reset-password          → validates the token, writes the
    new hash, clears lockout, and invalidates every existing session via
    `password_changed_at`.

The token embeds a fingerprint of the current password hash. Changing
the password changes the fingerprint, so a link is single-use without a
token table, and a password change elsewhere kills outstanding links.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime
from urllib.parse import quote
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import AuditAction
from app.core.exceptions import ValidationError
from app.core.logging import log
from app.core.security import hash_password
from app.core.tokens import (
    create_password_reset_token,
    decode_password_reset_token,
)
from app.modules.audit.service import AuditService
from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository
from app.modules.settings.business import business_profile


def password_fingerprint(hashed: str) -> str:
    """Short, non-reversible marker of the current password hash."""
    return hashlib.sha256(hashed.encode()).hexdigest()[:16]


class PasswordResetService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.audit = AuditService(db)

    async def find_user(self, identifier: str) -> User | None:
        identifier = identifier.strip()
        if not identifier:
            return None
        if "@" in identifier:
            stmt = select(User).where(
                func.lower(User.email) == identifier.lower()
            )
            return (await self.db.execute(stmt)).scalar_one_or_none()
        return await self.users.by_username(identifier)

    async def request_reset(
        self,
        identifier: str,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> bool:
        """Queue a reset link. Returns whether an email was queued.

        The HTTP layer must NOT expose this return value — it leaks which
        accounts exist.
        """
        if not settings.PASSWORD_RESET_ENABLED:
            return False

        user = await self.find_user(identifier)
        if user is None or not user.is_active or not user.email:
            log.info("password_reset_request_ignored", identifier_len=len(identifier))
            return False

        token = create_password_reset_token(
            str(user.id), password_fingerprint(user.hashed_password)
        )
        reset_url = (
            f"{settings.APP_BASE_URL.rstrip('/')}/admin/reset-password"
            f"?token={quote(token, safe='')}"
        )

        await self.audit.log(
            action=AuditAction.PASSWORD_RESET,
            table_name="users",
            record_id=user.id,
            user_id=user.id,
            new_data={"stage": "requested"},
            ip_address=ip,
            user_agent=user_agent,
        )

        # Capture plain values — the request session (and this ORM
        # instance) is gone by the time the queued job runs.
        user_id = user.id
        username = user.username
        to_email = user.email
        to_name = user.full_name or user.username

        async def _dispatch() -> None:
            from app.core.database import SessionLocal
            from app.modules.email.constants import (
                EmailRelatedType,
                EmailTemplate,
            )
            from app.modules.email.service import EmailService

            async with SessionLocal() as session:
                try:
                    business = await business_profile(session)
                    await EmailService(session).send_template(
                        template=EmailTemplate.PASSWORD_RESET,
                        template_path="emails/password_reset.html",
                        to_email=to_email,
                        to_name=to_name,
                        subject=f"Reset your {settings.APP_NAME} password",
                        context={
                            "user_name": to_name,
                            "username": username,
                            "reset_url": reset_url,
                            "expires_minutes": settings.PASSWORD_RESET_TTL_MINUTES,
                            "business": business,
                        },
                        related_type=EmailRelatedType.USER,
                        related_id=user_id,
                    )
                    await session.commit()
                except Exception:
                    await session.rollback()
                    log.exception(
                        "password_reset_email_failed", user_id=str(user_id)
                    )

        from app.core.jobs import queue

        await queue.enqueue(_dispatch)
        log.info("password_reset_email_queued", user_id=str(user_id))
        return True

    async def reset_password(
        self,
        token: str,
        new_password: str,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> User:
        try:
            payload = decode_password_reset_token(token)
        except ValueError as exc:
            raise ValidationError(
                "This reset link is invalid or has expired. Request a new one."
            ) from exc

        try:
            uid = UUID(payload.sub)
        except ValueError as exc:
            raise ValidationError("This reset link is invalid.") from exc

        user = await self.db.get(User, uid, with_for_update=True)
        if user is None or not user.is_active:
            raise ValidationError("This reset link is no longer valid.")

        expected = password_fingerprint(user.hashed_password)
        supplied = str(payload.extra.get("fp", ""))
        if not supplied or not hmac.compare_digest(supplied, expected):
            raise ValidationError(
                "This reset link has already been used. Request a new one."
            )

        user.hashed_password = hash_password(new_password)
        user.password_changed_at = datetime.now(UTC)
        user.failed_login_attempts = 0
        user.locked_until = None
        await self.db.flush()

        await self.audit.log(
            action=AuditAction.PASSWORD_RESET,
            table_name="users",
            record_id=user.id,
            user_id=user.id,
            new_data={"stage": "completed"},
            ip_address=ip,
            user_agent=user_agent,
        )
        return user
