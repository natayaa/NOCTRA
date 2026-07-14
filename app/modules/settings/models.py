# modules/settings/models.py
from decimal import Decimal
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    String, Text, ForeignKey, Integer, DateTime,
    Numeric, Boolean, Enum as SQLEnum, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.base import Base, UUIDMixin, TimestampMixin
from core.constants import UserRole


# ============================================================
# WORKSHOP SETTINGS
# ============================================================
class WorkshopSettings(Base, UUIDMixin, TimestampMixin):
    """Model untuk pengaturan workshop."""
    __tablename__ = "tb_workshop_settings"

    name: Mapped[str] = mapped_column(
        String(200), nullable=False, default="NOCTRA Autoworks")
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Logo & Branding
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    favicon_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    primary_color: Mapped[str | None] = mapped_column(
        String(20), nullable=True, default="#ff6b00")


# ============================================================
# PRICING SETTINGS
# ============================================================
class PricingSettings(Base, UUIDMixin, TimestampMixin):
    """Model untuk pengaturan pricing."""
    __tablename__ = "tb_pricing_settings"

    # Base prices per project type
    paint_base_price: Mapped[int] = mapped_column(
        Integer, nullable=False, default=2500000)
    restoration_base_price: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5000000)
    detailing_base_price: Mapped[int] = mapped_column(
        Integer, nullable=False, default=500000)
    custom_color_surcharge: Mapped[int] = mapped_column(
        Integer, nullable=False, default=500000)

    # Labor rates
    labor_painter_per_day: Mapped[int] = mapped_column(
        Integer, nullable=False, default=200000)
    labor_body_per_day: Mapped[int] = mapped_column(
        Integer, nullable=False, default=250000)
    labor_assembly_per_day: Mapped[int] = mapped_column(
        Integer, nullable=False, default=150000)
    labor_supervisor_per_day: Mapped[int] = mapped_column(
        Integer, nullable=False, default=300000)

    # Tax & Margin
    tax_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=11.0)
    default_margin_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=40.0)

    # Defaults
    default_duration_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=14)
    deposit_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=30.0)

    # Currency
    currency: Mapped[str] = mapped_column(
        String(10), nullable=False, default="IDR")

    # Flags
    auto_generate_invoice: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True)
    email_notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True)
    whatsapp_notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True)


# ============================================================
# SECURITY SETTINGS
# ============================================================
class SecuritySettings(Base, UUIDMixin, TimestampMixin):
    """Model untuk pengaturan keamanan."""
    __tablename__ = "tb_security_settings"

    require_mfa: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False)
    allow_remember_me: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True)
    force_password_change_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=90)
    session_timeout_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60)
    max_login_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5)
    lockout_duration_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30)


# ============================================================
# WHATSAPP TEMPLATE
# ============================================================
class WhatsAppTemplate(Base, UUIDMixin, TimestampMixin):
    """Model untuk template WhatsApp."""
    __tablename__ = "tb_whatsapp_templates"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    template: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False)
    variables: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Example: {"customer_name": "Customer Name", "vehicle": "Vehicle", "project_type": "Project Type"}

    def render(self, data: dict) -> str:
        """Render template dengan data yang diberikan."""
        result = self.template
        for key, value in data.items():
            result = result.replace(f"{{{{{key}}}}}", str(value or ""))
        return result


# ============================================================
# PROJECT TYPES
# ============================================================
class ProjectType(Base, UUIDMixin, TimestampMixin):
    """Model untuk tipe proyek yang tersedia."""
    __tablename__ = "tb_project_types"

    name: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


# ============================================================
# PAYMENT METHODS
# ============================================================
class PaymentMethod(Base, UUIDMixin, TimestampMixin):
    """Model untuk metode pembayaran."""
    __tablename__ = "tb_payment_methods"

    name: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


# ============================================================
# INQUIRY STATUS WORKFLOW
# ============================================================
class InquiryStatusWorkflow(Base, UUIDMixin, TimestampMixin):
    """Model untuk workflow status inquiry."""
    __tablename__ = "tb_inquiry_status_workflow"

    from_status: Mapped[str] = mapped_column(String(50), nullable=False)
    to_status: Mapped[str] = mapped_column(String(50), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True)
