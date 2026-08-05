# modules/settings/models.py
"""
Settings Module Models - REFACTORED

✅ SoftDeleteMixin untuk semua models
✅ Indexes untuk performance
✅ Validasi constraints
✅ Dokumentasi lengkap
"""

from decimal import Decimal
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    String, Text, ForeignKey, Integer, DateTime,
    Numeric, Boolean, Enum as SQLEnum, JSON, Index, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.base import Base, UUIDMixin, TimestampMixin, SoftDeleteMixin
from core.constants import UserRole


# ============================================================
# WORKSHOP SETTINGS
# ============================================================
class WorkshopSettings(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Model untuk pengaturan workshop.
    
    ✅ Single record (hanya ada 1 record)
    ✅ Soft delete support
    ✅ Index untuk email dan phone
    """
    __tablename__ = "tb_workshop_settings"

    name: Mapped[str] = mapped_column(
        String(200), nullable=False, default="NOCTRA Autoworks"
    )
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Logo & Branding
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    favicon_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    primary_color: Mapped[str | None] = mapped_column(
        String(20), nullable=True, default="#ff6b00"
    )

    __table_args__ = (
        CheckConstraint(
            "primary_color IS NULL OR primary_color ~ '^#[0-9a-fA-F]{6}$'",
            name="ck_workshop_primary_color_format"
        ),
        Index("idx_workshop_email", "email"),
        Index("idx_workshop_phone", "phone"),
        Index("idx_workshop_deleted", "is_deleted"),
    )

    def __repr__(self):
        return f"<WorkshopSettings {self.id} - {self.name}>"


# ============================================================
# PRICING SETTINGS
# ============================================================
class PricingSettings(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Model untuk pengaturan pricing.
    
    ✅ Single record
    ✅ Tax, margin, deposit settings
    ✅ Labor rates
    """
    __tablename__ = "tb_pricing_settings"

    # Base prices per project type
    paint_base_price: Mapped[int] = mapped_column(
        Integer, nullable=False, default=2500000
    )
    restoration_base_price: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5000000
    )
    detailing_base_price: Mapped[int] = mapped_column(
        Integer, nullable=False, default=500000
    )
    custom_color_surcharge: Mapped[int] = mapped_column(
        Integer, nullable=False, default=500000
    )

    # Labor rates
    labor_painter_per_day: Mapped[int] = mapped_column(
        Integer, nullable=False, default=200000
    )
    labor_body_per_day: Mapped[int] = mapped_column(
        Integer, nullable=False, default=250000
    )
    labor_assembly_per_day: Mapped[int] = mapped_column(
        Integer, nullable=False, default=150000
    )
    labor_supervisor_per_day: Mapped[int] = mapped_column(
        Integer, nullable=False, default=300000
    )

    # Tax & Margin
    tax_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=11.0
    )
    default_margin_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=40.0
    )

    # Defaults
    default_duration_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=14
    )
    deposit_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=30.0
    )

    # Currency
    currency: Mapped[str] = mapped_column(
        String(10), nullable=False, default="IDR"
    )

    # Flags
    auto_generate_invoice: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    email_notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    whatsapp_notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    __table_args__ = (
        CheckConstraint(
            "tax_percent >= 0 AND tax_percent <= 100",
            name="ck_pricing_tax_percent_range"
        ),
        CheckConstraint(
            "default_margin_percent >= 0 AND default_margin_percent <= 100",
            name="ck_pricing_margin_percent_range"
        ),
        CheckConstraint(
            "deposit_percent >= 0 AND deposit_percent <= 100",
            name="ck_pricing_deposit_percent_range"
        ),
        CheckConstraint(
            "default_duration_days >= 1",
            name="ck_pricing_duration_days_positive"
        ),
        Index("idx_pricing_deleted", "is_deleted"),
    )

    def __repr__(self):
        return f"<PricingSettings {self.id} - Tax: {self.tax_percent}%, Margin: {self.default_margin_percent}%>"


# ============================================================
# SECURITY SETTINGS
# ============================================================
class SecuritySettings(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Model untuk pengaturan keamanan.
    
    ✅ MFA, session, login attempts
    """
    __tablename__ = "tb_security_settings"

    require_mfa: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    allow_remember_me: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    force_password_change_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=90
    )
    session_timeout_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60
    )
    max_login_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5
    )
    lockout_duration_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30
    )

    __table_args__ = (
        CheckConstraint(
            "force_password_change_days >= 0",
            name="ck_security_password_change_days_non_negative"
        ),
        CheckConstraint(
            "session_timeout_minutes >= 5",
            name="ck_security_session_timeout_min_5"
        ),
        CheckConstraint(
            "max_login_attempts >= 3",
            name="ck_security_max_login_attempts_min_3"
        ),
        CheckConstraint(
            "lockout_duration_minutes >= 5",
            name="ck_security_lockout_duration_min_5"
        ),
        Index("idx_security_deleted", "is_deleted"),
    )

    def __repr__(self):
        return f"<SecuritySettings {self.id} - MFA: {self.require_mfa}>"


# ============================================================
# WHATSAPP TEMPLATE
# ============================================================
class WhatsAppTemplate(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Model untuk template WhatsApp.
    
    ✅ Render template dengan variables
    ✅ Default template flag
    ✅ Variables sebagai JSON
    """
    __tablename__ = "tb_whatsapp_templates"

    name: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    template: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    variables: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_whatsapp_template_name", "name"),
        Index("idx_whatsapp_template_default", "is_default"),
        Index("idx_whatsapp_template_deleted", "is_deleted"),
    )

    def render(self, data: dict) -> str:
        """
        Render template dengan data yang diberikan.
        
        Args:
            data: Dictionary dengan key-value untuk placeholder
        
        Returns:
            Rendered template string
        """
        result = self.template
        for key, value in data.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value or ""))
        return result

    def __repr__(self):
        return f"<WhatsAppTemplate {self.id} - {self.name} (default: {self.is_default})>"


# ============================================================
# PROJECT TYPES
# ============================================================
class ProjectType(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Model untuk tipe proyek yang tersedia.
    
    ✅ Unique name
    ✅ Active/inactive flag
    ✅ Sort order untuk UI
    """
    __tablename__ = "tb_project_types"

    name: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    __table_args__ = (
        CheckConstraint(
            "base_price IS NULL OR base_price >= 0",
            name="ck_project_type_base_price_non_negative"
        ),
        Index("idx_project_type_name", "name"),
        Index("idx_project_type_active", "is_active"),
        Index("idx_project_type_sort", "sort_order"),
        Index("idx_project_type_deleted", "is_deleted"),
    )

    def __repr__(self):
        return f"<ProjectType {self.id} - {self.name} (active: {self.is_active})>"


# ============================================================
# PAYMENT METHODS
# ============================================================
class PaymentMethod(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Model untuk metode pembayaran.
    
    ✅ Unique name dan code
    ✅ Icon untuk UI
    ✅ Sort order
    """
    __tablename__ = "tb_payment_methods"

    name: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    code: Mapped[str] = mapped_column(
        String(20), nullable=False, unique=True, index=True
    )
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_payment_method_code", "code"),
        Index("idx_payment_method_active", "is_active"),
        Index("idx_payment_method_sort", "sort_order"),
        Index("idx_payment_method_deleted", "is_deleted"),
    )

    def __repr__(self):
        return f"<PaymentMethod {self.id} - {self.code} ({self.name})>"


# ============================================================
# INQUIRY STATUS WORKFLOW
# ============================================================
class InquiryStatusWorkflow(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Model untuk workflow status inquiry.
    
    ✅ Define allowed transitions: from_status → to_status
    ✅ Active/inactive flag
    ✅ Sort order untuk priority
    """
    __tablename__ = "tb_inquiry_status_workflow"

    from_status: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    to_status: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )

    __table_args__ = (
        CheckConstraint(
            "from_status IN ('new', 'under_review', 'contacted', 'quoted', 'approved', 'converted', 'rejected', 'closed', 'completed')",
            name="ck_workflow_from_status_valid"
        ),
        CheckConstraint(
            "to_status IN ('new', 'under_review', 'contacted', 'quoted', 'approved', 'converted', 'rejected', 'closed', 'completed')",
            name="ck_workflow_to_status_valid"
        ),
        CheckConstraint(
            "from_status != to_status",
            name="ck_workflow_from_to_different"
        ),
        Index("idx_workflow_from_status", "from_status"),
        Index("idx_workflow_to_status", "to_status"),
        Index("idx_workflow_active", "is_active"),
        Index("idx_workflow_sort", "sort_order"),
        Index("idx_workflow_deleted", "is_deleted"),
        Index("idx_workflow_from_to", "from_status", "to_status", unique=True),
    )

    def __repr__(self):
        return f"<InquiryStatusWorkflow {self.id} - {self.from_status} → {self.to_status}>"