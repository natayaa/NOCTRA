"""Email module constants."""

from __future__ import annotations

from enum import StrEnum


class EmailStatus(StrEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    # Used when EMAIL_ENABLED=False — the send was skipped by design,
    # not failed. Keeping this distinct from SENT avoids misleading
    # logs in development / staging.
    SKIPPED = "SKIPPED"


class EmailTemplate(StrEnum):
    INQUIRY_AUTO_RESPONSE = "inquiry_auto_response"
    INQUIRY_SALES_NOTIFICATION = "inquiry_sales_notification"


class EmailRelatedType(StrEnum):
    """Domain objects an email can be linked to via (related_type, related_id)."""
    INQUIRY = "INQUIRY"
    CUSTOMER = "CUSTOMER"
    PROJECT = "PROJECT"
    INVOICE = "INVOICE"


EMAIL_STATUSES: list[str] = [s.value for s in EmailStatus]
EMAIL_TEMPLATES: list[str] = [t.value for t in EmailTemplate]
EMAIL_RELATED_TYPES: list[str] = [r.value for r in EmailRelatedType]