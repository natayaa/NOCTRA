"""Email module constants."""

from __future__ import annotations

from enum import StrEnum


class EmailStatus(StrEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class EmailTemplate(StrEnum):
    INQUIRY_AUTO_RESPONSE = "inquiry_auto_response"
    INQUIRY_SALES_NOTIFICATION = "inquiry_sales_notification"


EMAIL_STATUSES: list[str] = [s.value for s in EmailStatus]