"""Low-level SMTP dispatch via aiosmtplib.

This module knows nothing about business logic. It sends one email.

Retry policy:
    Transient failures (network errors, timeouts, SMTP 4xx responses) are
    retried up to `SMTP_MAX_RETRIES` times with exponential backoff and
    jitter. Permanent failures (auth failures, bad recipients/senders,
    SMTP 5xx responses) fail immediately without retry.

    On exhaustion of retries (or on a permanent error), the last exception
    is re-raised so the caller can record the failure on the EmailLog row.

Idempotency:
    SMTP is not truly idempotent. If a read-timeout occurs AFTER the DATA
    command was sent, a retry could deliver a duplicate. We mitigate by
    building the MIME message ONCE — the same Message-ID is used across
    all retries, letting most mail servers dedupe within a short window.
    For transactional email, occasional duplicates are preferable to loss.
"""

from __future__ import annotations

import asyncio
import random
import re
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr
from enum import StrEnum

import aiosmtplib

from app.core.config import settings
from app.core.logging import log


class SendOutcome(StrEnum):
    """Result of one `send()` attempt — distinguishes skipped from sent."""
    SENT = "SENT"
    SKIPPED = "SKIPPED"       # EMAIL_ENABLED=False


@dataclass
class OutgoingEmail:
    to_email: str
    to_name: str | None
    subject: str
    html_body: str
    text_body: str | None = None
    reply_to: str | None = None


# Exceptions that ALWAYS indicate a permanent failure (do not retry).
_PERMANENT_SMTP_ERRORS: tuple[type[BaseException], ...] = (
    aiosmtplib.SMTPAuthenticationError,   # bad credentials
    aiosmtplib.SMTPRecipientsRefused,     # recipient rejected
    aiosmtplib.SMTPSenderRefused,         # sender rejected
    aiosmtplib.SMTPHeloError,             # server rejected our HELO
)

# Exceptions in the network/timeout layer — always safe to retry.
_RETRYABLE_LAYER_ERRORS: tuple[type[BaseException], ...] = (
    OSError,        # ConnectionError, socket.error, etc.
    TimeoutError,   # asyncio.TimeoutError is an alias in Python 3.11+
)


def _is_retryable(exc: BaseException) -> bool:
    """
    Classify an exception as transient (safe to retry) or permanent.

    SMTP response codes follow RFC 5321:
        4xx → temporary (retry)
        5xx → permanent (do not retry)
    """
    # Never retry explicit cancellation / system exit.
    if isinstance(exc, (asyncio.CancelledError, KeyboardInterrupt, SystemExit)):
        return False

    # Auth / bad-address errors are permanent regardless of code.
    if isinstance(exc, _PERMANENT_SMTP_ERRORS):
        return False

    # Network / timeout layer — always retryable.
    if isinstance(exc, _RETRYABLE_LAYER_ERRORS):
        return True

    # SMTP response exception — use the RFC 5321 code semantics.
    if isinstance(exc, aiosmtplib.SMTPException):
        code = getattr(exc, "smtp_code", None)
        if isinstance(code, int):
            return 400 <= code < 500
        # Non-response SMTP exceptions (e.g. SMTPTimeoutError) → retry.
        return True

    # Unknown exception type — fail fast rather than retry blindly.
    return False


class EmailSender:
    """Stateless SMTP client with exponential-backoff retry."""

    def __init__(self) -> None:
        self.enabled = settings.EMAIL_ENABLED
        # Hard cap at 10 to prevent absurd backoff from bad config.
        self.max_retries = max(
            0, min(10, int(getattr(settings, "SMTP_MAX_RETRIES", 3)))
        )
        self.retry_base = max(
            0.0, float(getattr(settings, "SMTP_RETRY_BASE_DELAY", 1.0))
        )
        self.retry_max = max(
            self.retry_base,
            float(getattr(settings, "SMTP_RETRY_MAX_DELAY", 30.0)),
        )
        if self.enabled:
            self._validate_config()

    @staticmethod
    def _validate_config() -> None:
        """Surface misconfigurations early via warnings (never blocks)."""
        if settings.SMTP_USE_SSL and settings.SMTP_USE_STARTTLS:
            log.warning(
                "smtp_config_conflict",
                msg="SMTP_USE_SSL overrides SMTP_USE_STARTTLS",
            )
        if settings.SMTP_USE_SSL and settings.SMTP_PORT == 587:
            log.warning(
                "smtp_config_port",
                msg="SMTP_USE_SSL=True usually uses port 465, not 587",
                port=settings.SMTP_PORT,
            )
        if settings.SMTP_USE_STARTTLS and settings.SMTP_PORT == 465:
            log.warning(
                "smtp_config_port",
                msg="STARTTLS usually uses port 587, not 465",
                port=settings.SMTP_PORT,
            )
        has_user = bool(settings.SMTP_USERNAME and settings.SMTP_USERNAME.strip())
        has_pass = bool(settings.SMTP_PASSWORD)
        if has_user != has_pass:
            log.warning(
                "smtp_config_auth_incomplete",
                msg="SMTP_USERNAME and SMTP_PASSWORD must both be set (or both empty)",
            )

    async def send(self, msg: OutgoingEmail) -> SendOutcome:
        """
        Dispatch one email with automatic retry.

        Returns SENT or SKIPPED. Raises on final failure (retries exhausted
        or permanent error) so the caller can record the failure.
        """
        if not self.enabled:
            log.info(
                "email_skipped_disabled",
                to=msg.to_email,
                subject=msg.subject,
            )
            return SendOutcome.SKIPPED

        # Build MIME ONCE so all retries share the same Message-ID.
        # This lets the receiving MTA dedupe in the unlikely event
        # of a duplicate delivery from a read-timeout retry.
        mime = self._build_mime(msg)

        log.info("email_sending", to=msg.to_email, subject=msg.subject)

        attempt = 0
        while True:
            try:
                await self._dispatch(mime)
                log.info(
                    "email_sent",
                    to=msg.to_email,
                    subject=msg.subject,
                    attempts=attempt + 1,
                )
                return SendOutcome.SENT

            except Exception as exc:
                retryable = _is_retryable(exc)
                can_retry = retryable and attempt < self.max_retries

                if not can_retry:
                    log.error(
                        "email_send_failed",
                        to=msg.to_email,
                        subject=msg.subject,
                        error=str(exc),
                        error_type=type(exc).__name__,
                        attempts=attempt + 1,
                        retryable=retryable,
                    )
                    raise

                # Exponential backoff: base * 2^attempt, capped at retry_max,
                # plus up to 30% jitter to avoid synchronised retries.
                delay = min(
                    self.retry_base * (2 ** attempt),
                    self.retry_max,
                ) * (1.0 + random.uniform(0.0, 0.3))

                log.warning(
                    "email_send_retry",
                    to=msg.to_email,
                    subject=msg.subject,
                    error_type=type(exc).__name__,
                    error=str(exc),
                    attempt=attempt + 1,
                    max_attempts=self.max_retries + 1,
                    delay_sec=round(delay, 2),
                )

                await asyncio.sleep(delay)
                attempt += 1

    # ── Internals ────────────────────────────────────────

    @staticmethod
    async def _dispatch(mime: EmailMessage) -> None:
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

    @staticmethod
    def _build_mime(msg: OutgoingEmail) -> EmailMessage:
        mime = EmailMessage()
        # formataddr() escapes commas / quotes in the display name —
        # raw f-string interpolation here would allow header injection.
        mime["From"] = formataddr(
            (settings.EMAIL_FROM_NAME, settings.EMAIL_FROM_ADDRESS)
        )
        mime["To"] = (
            formataddr((msg.to_name, msg.to_email))
            if msg.to_name
            else msg.to_email
        )
        mime["Subject"] = msg.subject

        reply_to = msg.reply_to or settings.EMAIL_REPLY_TO
        if reply_to:
            mime["Reply-To"] = reply_to

        # Plain text first, HTML second — best practice for deliverability.
        text = msg.text_body or _strip_html(msg.html_body)
        mime.set_content(text)
        mime.add_alternative(msg.html_body, subtype="html")
        return mime


_ENTITY_MAP = {
    "&nbsp;": " ", "&amp;": "&", "&lt;": "<", "&gt;": ">",
    "&quot;": '"', "&#39;": "'", "&apos;": "'",
}


def _strip_html(html: str) -> str:
    """Rudimentary HTML → text fallback. Good enough for internal templates."""
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    for entity, char in _ENTITY_MAP.items():
        text = text.replace(entity, char)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


sender = EmailSender()