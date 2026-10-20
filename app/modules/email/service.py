"""Email service: renders templates, sends, and logs."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from jinja2 import TemplateError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import log
from app.modules.email.constants import (
    EmailRelatedType,
    EmailStatus,
    EmailTemplate,
)
from app.modules.email.models import EmailLog
from app.modules.email.repository import EmailLogRepository
from app.modules.email.sender import (
    OutgoingEmail,
    SendOutcome,
    sender,
)
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
        template: EmailTemplate | str,
        to_email: str,
        to_name: str | None,
        subject: str,
        context: dict,
        template_path: str | None = None,
        related_type: EmailRelatedType | str | None = None,
        related_id: UUID | None = None,
        reply_to: str | None = None,
    ) -> EmailLog:
        """
        Render `template` (an EmailTemplate or raw name), send it, and record.

        Never raises for transport/template errors — failures are captured
        on the EmailLog row so nothing is silently lost. Programmer errors
        (e.g. DB unavailable) still propagate.

        `template_path` overrides the default `email/{template}.html`
        convention when a non-standard location is needed.
        """
        template_value = (
            template.value if isinstance(template, EmailTemplate) else str(template)
        )
        related_type_value = (
            related_type.value
            if isinstance(related_type, EmailRelatedType)
            else related_type
        )
        # Default template path convention: templates/email/<name>.html
        jinja_path = template_path or f"email/{template_value}.html"

        # Create the log entry FIRST so every attempt (render + send) is recorded.
        entry = EmailLog(
            to_email=to_email,
            to_name=to_name,
            subject=subject,
            template=template_value,
            status=EmailStatus.PENDING.value,
            related_type=related_type_value,
            related_id=related_id,
        )
        await self.repo.add(entry)

        try:
            html_body = self._render(jinja_path, context)
        except TemplateError as exc:
            entry.status = EmailStatus.FAILED.value
            entry.error_message = f"TemplateError: {exc}"
            log.warning(
                "email_template_failed",
                template=template_value,
                to=to_email,
                error=str(exc),
            )
            await self.db.flush()
            return entry

        try:
            outcome = await sender.send(
                OutgoingEmail(
                    to_email=to_email,
                    to_name=to_name,
                    subject=subject,
                    html_body=html_body,
                    reply_to=reply_to,
                )
            )
            if outcome == SendOutcome.SKIPPED:
                entry.status = EmailStatus.SKIPPED.value
            else:
                entry.status = EmailStatus.SENT.value
                entry.sent_at = datetime.now(UTC)
        except Exception as exc:
            entry.status = EmailStatus.FAILED.value
            entry.error_message = f"{type(exc).__name__}: {exc}"
            log.warning(
                "email_logged_as_failed",
                to=to_email,
                template=template_value,
                error=entry.error_message,
            )

        await self.db.flush()
        return entry

    @staticmethod
    def _render(template_path: str, context: dict) -> str:
        """
        Render a Jinja2 template. Caller context wins over global context
        on key collision — merges dicts before spreading into render().
        """
        merged = {**EmailService._global_context(), **context}
        return templates.env.get_template(template_path).render(**merged)

    @staticmethod
    def _global_context() -> dict:
        return {
            "app_name": settings.APP_NAME,
            "app_base_url": settings.APP_BASE_URL,
            "public_phone": settings.PUBLIC_PHONE,
            "public_email": settings.PUBLIC_EMAIL,
            "public_address": settings.PUBLIC_ADDRESS,
            "public_whatsapp": settings.PUBLIC_WHATSAPP,
        }