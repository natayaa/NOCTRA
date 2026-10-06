"""Low-level SMTP dispatch via aiosmtplib.

This module knows nothing about business logic. It sends one email.
"""

from __future__ import annotations

from dataclasses import dataclass
from email.message import EmailMessage

import aiosmtplib

from app.core.config import settings
from app.core.logging import log


@dataclass
class OutgoingEmail:
    to_email: str
    to_name: str | None
    subject: str
    html_body: str
    text_body: str | None = None
    reply_to: str | None = None


class EmailSender:
    """Stateless SMTP client. Config comes from settings."""

    def __init__(self) -> None:
        self.enabled = settings.EMAIL_ENABLED

    async def send(self, msg: OutgoingEmail) -> None:
        """
        Send one email. Raises on failure — callers should catch and log.
        """
        if not self.enabled:
            log.info("email_skipped_disabled", to=msg.to_email, subject=msg.subject)
            return

        mime = EmailMessage()
        mime["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM_ADDRESS}>"
        mime["To"] = (
            f"{msg.to_name} <{msg.to_email}>" if msg.to_name else msg.to_email
        )
        mime["Subject"] = msg.subject

        reply_to = msg.reply_to or settings.EMAIL_REPLY_TO
        if reply_to:
            mime["Reply-To"] = reply_to

        # Plain text first, HTML second — best practice for deliverability.
        text = msg.text_body or _strip_html(msg.html_body)
        mime.set_content(text)
        mime.add_alternative(msg.html_body, subtype="html")

        log.info("email_sending", to=msg.to_email, subject=msg.subject)

        try:
            await aiosmtplib.send(
                mime,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USERNAME or None,
                password=settings.SMTP_PASSWORD or None,
                start_tls=settings.SMTP_USE_STARTTLS and not settings.SMTP_USE_SSL,
                use_tls=settings.SMTP_USE_SSL,
                timeout=settings.SMTP_TIMEOUT_SECONDS,
            )
            log.info("email_sent", to=msg.to_email, subject=msg.subject)
        except Exception as exc:
            log.error(
                "email_send_failed",
                to=msg.to_email,
                subject=msg.subject,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise


def _strip_html(html: str) -> str:
    """Rudimentary HTML → text fallback. Good enough for our templates."""
    import re
    text = re.sub(r"<br\s*/?>", "\n", html)
    text = re.sub(r"</p>", "\n\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


sender = EmailSender()