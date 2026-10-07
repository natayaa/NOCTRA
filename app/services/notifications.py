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
    inquiry_id,
    inquiry_code: str,
    service_interest: str | None,
    description: str,
    color_family: str | None,
    color_preference: str | None,
    finish_preference: str | None,
    has_custom_graphics: bool,
    budget_range: str | None,
    desired_date,
    customer_name: str,
    customer_phone: str,
    customer_email: str | None,
    customer_code: str,
    customer_is_new: bool,
    vehicle_label: str | None = None,
    photo_count: int = 0,
) -> None:
    """
    Send both notifications for a new inquiry:
      1. Auto-response to the customer
      2. Alert to the sales team

    Takes plain values, not ORM objects — callers may run this in a
    background task where the original session is closed.
    """
    from app.modules.pricing.service import margin_of  # only if needed

    email = EmailService(db)

    service_label = SERVICE_INTEREST_LABELS.get(service_interest, service_interest) if service_interest else None
    color_label = COLOR_LABELS.get(color_family, color_family) if color_family else color_preference
    finish_label = FINISH_LABELS.get(finish_preference, finish_preference) if finish_preference else None
    budget_label = BUDGET_LABELS.get(budget_range, budget_range) if budget_range else None
    desired = desired_date.strftime("%d %b %Y") if desired_date else None

    # ── 1. Customer auto-response ──
    if customer_email:
        await email.send_template(
            template_name=EmailTemplate.INQUIRY_AUTO_RESPONSE.value,
            template="emails/inquiry_auto_response.html",
            to_email=customer_email,
            to_name=customer_name,
            subject=f"We received your inquiry — {inquiry_code}",
            context={
                "inquiry_code": inquiry_code,
                "inquiry": {"customer_name": customer_name},
                "service_label": service_label,
                "vehicle_label": vehicle_label,
                "color_label": color_label,
                "finish_label": finish_label,
                "description_excerpt": (description or "")[:400],
            },
            related_type="INQUIRY",
            related_id=inquiry_id,
        )

    # ── 2. Sales notification ──
    from app.modules.settings.service import SettingsService
    sales_email = await SettingsService(db).get_value(
        "notifications.sales_email", settings.PUBLIC_EMAIL,
    )

    if sales_email:
        admin_url = f"{settings.APP_BASE_URL}/admin/inquiries/{inquiry_id}"
        await email.send_template(
            template_name=EmailTemplate.INQUIRY_SALES_NOTIFICATION.value,
            template="emails/inquiry_sales_notification.html",
            to_email=sales_email,
            to_name=None,
            subject=f"[New Inquiry] {customer_name} — {service_label or 'Inquiry'} ({inquiry_code})",
            context={
                "inquiry_code": inquiry_code,
                "customer_name": customer_name,
                "customer_phone": customer_phone,
                "customer_email": customer_email,
                "customer_code": customer_code,
                "customer_is_new": customer_is_new,
                "service_label": service_label,
                "vehicle_label": vehicle_label,
                "color_label": color_label,
                "finish_label": finish_label,
                "budget_label": budget_label,
                "desired_date": desired,
                "description": description,
                "has_custom_graphics": has_custom_graphics,
                "photo_count": photo_count,
                "admin_url": admin_url,
            },
            related_type="INQUIRY",
            related_id=inquiry_id,
        )