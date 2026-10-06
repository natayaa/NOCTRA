"""Business-specific notification dispatchers.

Each function here knows about domain concepts (inquiries, projects, …)
and calls EmailService with the right template + context.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import log
from app.modules.email.constants import EmailTemplate
from app.modules.email.service import EmailService
from app.modules.inquiries.constants import (
    BUDGET_LABELS,
    COLOR_LABELS,
    FINISH_LABELS,
    SERVICE_INTEREST_LABELS,
)
from app.modules.inquiries.models import Inquiry


async def notify_inquiry_received(
    db: AsyncSession,
    *,
    inquiry: Inquiry,
    customer_name: str,
    customer_phone: str,
    customer_email: str | None,
    customer_code: str,
    customer_is_new: bool,
    service_label: str | None = None,
    vehicle_label: str | None = None,
    photo_count: int = 0,
) -> None:
    """
    Send both notifications for a new inquiry:
      1. Auto-response to the customer (if they gave an email)
      2. Alert to the sales team
    """
    email = EmailService(db)
    catalog_labels = {
        "service": SERVICE_INTEREST_LABELS.get(inquiry.service_interest, inquiry.service_interest)
        if inquiry.service_interest else None,
        "color": COLOR_LABELS.get(inquiry.color_family, inquiry.color_family)
        if inquiry.color_family else None,
        "finish": FINISH_LABELS.get(inquiry.finish_preference, inquiry.finish_preference)
        if inquiry.finish_preference else None,
        "budget": BUDGET_LABELS.get(inquiry.budget_range, inquiry.budget_range)
        if inquiry.budget_range else None,
    }

    # ── 1. Customer auto-response ────────────────────
    if customer_email:
        await email.send_template(
            template_name=EmailTemplate.INQUIRY_AUTO_RESPONSE.value,
            template="emails/inquiry_auto_response.html",
            to_email=customer_email,
            to_name=customer_name,
            subject=f"We received your inquiry — {inquiry.code}",
            context={
                "inquiry_code": inquiry.code,
                "inquiry": {"customer_name": customer_name},
                "service_label": catalog_labels["service"],
                "vehicle_label": vehicle_label,
                "color_label": catalog_labels["color"] or inquiry.color_preference,
                "finish_label": catalog_labels["finish"],
                "description_excerpt": (inquiry.description or "")[:400],
            },
            related_type="INQUIRY",
            related_id=inquiry.id,
        )
        log.info("inquiry_auto_response_sent", inquiry=inquiry.code, to=customer_email)
    else:
        log.info("inquiry_auto_response_skipped_no_email", inquiry=inquiry.code)

    # ── 2. Sales notification ────────────────────────
    # Destination is configurable; falls back to PUBLIC_EMAIL
    from app.modules.settings.service import SettingsService
    svc = SettingsService(db)
    sales_email = await svc.get_value("notifications.sales_email", settings.PUBLIC_EMAIL)

    if sales_email:
        admin_url = f"{settings.APP_BASE_URL}/admin/inquiries/{inquiry.id}"
        await email.send_template(
            template_name=EmailTemplate.INQUIRY_SALES_NOTIFICATION.value,
            template="emails/inquiry_sales_notification.html",
            to_email=sales_email,
            to_name=None,
            subject=f"[New Inquiry] {customer_name} — {catalog_labels['service'] or 'Inquiry'} ({inquiry.code})",
            context={
                "inquiry_code": inquiry.code,
                "customer_name": customer_name,
                "customer_phone": customer_phone,
                "customer_email": customer_email,
                "customer_code": customer_code,
                "customer_is_new": customer_is_new,
                "service_label": catalog_labels["service"],
                "vehicle_label": vehicle_label,
                "color_label": catalog_labels["color"] or inquiry.color_preference,
                "finish_label": catalog_labels["finish"],
                "budget_label": catalog_labels["budget"],
                "desired_date": inquiry.desired_date.strftime("%d %b %Y") if inquiry.desired_date else None,
                "description": inquiry.description,
                "has_custom_graphics": inquiry.has_custom_graphics,
                "photo_count": photo_count,
                "admin_url": admin_url,
            },
            related_type="INQUIRY",
            related_id=inquiry.id,
        )
        log.info("inquiry_sales_notification_sent", inquiry=inquiry.code, to=sales_email)