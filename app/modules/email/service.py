"""Email service: renders templates, sends, and logs."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import log
from app.modules.email.constants import EmailStatus
from app.modules.email.models import EmailLog
from app.modules.email.repository import EmailLogRepository
from app.modules.email.sender import OutgoingEmail, sender
from app.web.templates_env import templates


class EmailService:
    """
    High-level send: render a Jinja2 template with context, dispatch via
    SMTP, record the attempt in email_logs.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = EmailLogRepository(db)

    async def send_template(
        self,
        *,
        template_name: str,
        template: str,
        to_email: str,
        to_name: str | None,
        subject: str,
        context: dict,
        related_type: str | None = None,
        related_id: UUID | None = None,
        reply_to: str | None = None,
    ) -> EmailLog:
        """
        Render `template` (a Jinja2 email template), send it, and record.
        Never raises — failures are captured on the EmailLog row.
        """
        # Render the HTML body
        env = templates.env
        jinja = env.get_template(template)
        html_body = jinja.render(**context, **self._global_context())

        entry = EmailLog(
            to_email=to_email,
            to_name=to_name,
            subject=subject,
            template=template_name,
            status=EmailStatus.PENDING.value,
            related_type=related_type,
            related_id=related_id,
        )
        await self.repo.add(entry)

        try:
            await sender.send(
                OutgoingEmail(
                    to_email=to_email,
                    to_name=to_name,
                    subject=subject,
                    html_body=html_body,
                    reply_to=reply_to,
                )
            )
            entry.status = EmailStatus.SENT.value
            entry.sent_at = datetime.now(UTC)
        except Exception as exc:
            entry.status = EmailStatus.FAILED.value
            entry.error_message = f"{type(exc).__name__}: {exc}"
            log.warning(
                "email_logged_as_failed",
                to=to_email,
                template=template_name,
                error=entry.error_message,
            )

        await self.db.flush()
        return entry

    @staticmethod
    def _global_context() -> dict:
        from app.core.config import settings
        return {
            "app_name": settings.APP_NAME,
            "app_base_url": settings.APP_BASE_URL,
            "public_phone": settings.PUBLIC_PHONE,
            "public_email": settings.PUBLIC_EMAIL,
            "public_address": settings.PUBLIC_ADDRESS,
            "public_whatsapp": settings.PUBLIC_WHATSAPP,
        }