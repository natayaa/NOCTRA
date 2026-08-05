# modules/settings/schemas.py
"""
Settings Module Schemas - REFACTORED

✅ Complete request/response schemas
✅ Validations with Pydantic field_validator
✅ Soft delete support
✅ Email, phone, website validations
✅ Color format validation
"""

from pydantic import BaseModel, Field, ConfigDict, EmailStr, field_validator
from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime
from decimal import Decimal
import re


# ============================================================================
# WORKSHOP SETTINGS
# ============================================================================

class WorkshopSettingsResponse(BaseModel):
    """Response untuk workshop settings."""
    id: UUID
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    primary_color: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkshopSettingsUpdate(BaseModel):
    """Schema untuk update workshop settings."""
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Nama workshop")
    address: Optional[str] = Field(None, description="Alamat workshop")
    phone: Optional[str] = Field(None, max_length=30, description="Nomor telepon")
    email: Optional[EmailStr] = Field(None, description="Email workshop")
    website: Optional[str] = Field(None, description="Website workshop")
    logo_url: Optional[str] = Field(None, description="URL logo")
    favicon_url: Optional[str] = Field(None, description="URL favicon")
    primary_color: Optional[str] = Field(
        None, 
        pattern=r'^#[0-9a-fA-F]{6}$',
        description="Warna utama (format hex: #RRGGBB)"
    )

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v:
            # Clean phone number
            cleaned = re.sub(r'[\s\-\(\)]', '', v)
            if not re.match(r'^\+?[0-9]{8,15}$', cleaned):
                raise ValueError("Invalid phone number format")
        return v

    @field_validator("website")
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        if v:
            if not v.startswith(('http://', 'https://')):
                return f"https://{v}"
        return v


# ============================================================================
# PRICING SETTINGS
# ============================================================================

class PricingSettingsResponse(BaseModel):
    """Response untuk pricing settings."""
    id: UUID
    paint_base_price: int
    restoration_base_price: int
    detailing_base_price: int
    custom_color_surcharge: int
    labor_painter_per_day: int
    labor_body_per_day: int
    labor_assembly_per_day: int
    labor_supervisor_per_day: int
    tax_percent: Decimal
    default_margin_percent: Decimal
    default_duration_days: int
    deposit_percent: Decimal
    currency: str
    auto_generate_invoice: bool
    email_notifications_enabled: bool
    whatsapp_notifications_enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PricingSettingsUpdate(BaseModel):
    """Schema untuk update pricing settings."""
    paint_base_price: Optional[int] = Field(None, ge=0, description="Harga dasar paint job")
    restoration_base_price: Optional[int] = Field(None, ge=0, description="Harga dasar restorasi")
    detailing_base_price: Optional[int] = Field(None, ge=0, description="Harga dasar detailing")
    custom_color_surcharge: Optional[int] = Field(None, ge=0, description="Surcharge warna custom")
    labor_painter_per_day: Optional[int] = Field(None, ge=0, description="Biaya painter per hari")
    labor_body_per_day: Optional[int] = Field(None, ge=0, description="Biaya body per hari")
    labor_assembly_per_day: Optional[int] = Field(None, ge=0, description="Biaya assembly per hari")
    labor_supervisor_per_day: Optional[int] = Field(None, ge=0, description="Biaya supervisor per hari")
    tax_percent: Optional[Decimal] = Field(None, ge=0, le=100, description="Persentase pajak")
    default_margin_percent: Optional[Decimal] = Field(None, ge=0, le=100, description="Persentase margin default")
    default_duration_days: Optional[int] = Field(None, ge=1, le=365, description="Durasi default (hari)")
    deposit_percent: Optional[Decimal] = Field(None, ge=0, le=100, description="Persentase deposit")
    currency: Optional[str] = Field(None, max_length=10, description="Mata uang")
    auto_generate_invoice: Optional[bool] = Field(None, description="Auto-generate invoice")
    email_notifications_enabled: Optional[bool] = Field(None, description="Email notifications enabled")
    whatsapp_notifications_enabled: Optional[bool] = Field(None, description="WhatsApp notifications enabled")


# ============================================================================
# SECURITY SETTINGS
# ============================================================================

class SecuritySettingsResponse(BaseModel):
    """Response untuk security settings."""
    id: UUID
    require_mfa: bool
    allow_remember_me: bool
    force_password_change_days: int
    session_timeout_minutes: int
    max_login_attempts: int
    lockout_duration_minutes: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SecuritySettingsUpdate(BaseModel):
    """Schema untuk update security settings."""
    require_mfa: Optional[bool] = Field(None, description="Require MFA")
    allow_remember_me: Optional[bool] = Field(None, description="Allow remember me")
    force_password_change_days: Optional[int] = Field(None, ge=0, le=365, description="Force password change (days)")
    session_timeout_minutes: Optional[int] = Field(None, ge=5, le=480, description="Session timeout (minutes)")
    max_login_attempts: Optional[int] = Field(None, ge=3, le=20, description="Max login attempts")
    lockout_duration_minutes: Optional[int] = Field(None, ge=5, le=1440, description="Lockout duration (minutes)")


# ============================================================================
# WHATSAPP TEMPLATE
# ============================================================================

class WhatsAppTemplateCreate(BaseModel):
    """Schema untuk membuat WhatsApp template."""
    name: str = Field(..., min_length=1, max_length=100, description="Nama template")
    template: str = Field(..., min_length=1, description="Isi template dengan placeholder {{variable}}")
    description: Optional[str] = Field(None, description="Deskripsi template")
    is_default: bool = Field(default=False, description="Set sebagai default")
    variables: Optional[Dict[str, str]] = Field(None, description="Daftar variabel yang digunakan")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return v.strip()

    @field_validator("template")
    @classmethod
    def validate_template(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Template cannot be empty")
        return v


class WhatsAppTemplateUpdate(BaseModel):
    """Schema untuk update WhatsApp template."""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Nama template")
    template: Optional[str] = Field(None, min_length=1, description="Isi template")
    description: Optional[str] = Field(None, description="Deskripsi template")
    is_default: Optional[bool] = Field(None, description="Set sebagai default")
    variables: Optional[Dict[str, str]] = Field(None, description="Daftar variabel")

    @field_validator("template")
    @classmethod
    def validate_template(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.strip():
            raise ValueError("Template cannot be empty")
        return v


class WhatsAppTemplateResponse(BaseModel):
    """Response untuk WhatsApp template."""
    id: UUID
    name: str
    template: str
    description: Optional[str] = None
    is_default: bool
    variables: Optional[Dict[str, str]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# PROJECT TYPES
# ============================================================================

class ProjectTypeCreate(BaseModel):
    """Schema untuk membuat project type."""
    name: str = Field(..., min_length=1, max_length=50, description="Nama tipe project (unique)")
    description: Optional[str] = Field(None, description="Deskripsi")
    base_price: Optional[int] = Field(None, ge=0, description="Harga dasar")
    is_active: bool = Field(default=True, description="Status aktif")
    sort_order: int = Field(default=0, description="Urutan")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return v.strip().lower()


class ProjectTypeUpdate(BaseModel):
    """Schema untuk update project type."""
    name: Optional[str] = Field(None, min_length=1, max_length=50, description="Nama tipe project")
    description: Optional[str] = Field(None, description="Deskripsi")
    base_price: Optional[int] = Field(None, ge=0, description="Harga dasar")
    is_active: Optional[bool] = Field(None, description="Status aktif")
    sort_order: Optional[int] = Field(None, description="Urutan")


class ProjectTypeResponse(BaseModel):
    """Response untuk project type."""
    id: UUID
    name: str
    description: Optional[str] = None
    base_price: Optional[int] = None
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# PAYMENT METHODS
# ============================================================================

class PaymentMethodCreate(BaseModel):
    """Schema untuk membuat payment method."""
    name: str = Field(..., min_length=1, max_length=50, description="Nama metode (unique)")
    code: str = Field(..., min_length=1, max_length=20, description="Kode unik (unique)")
    icon: Optional[str] = Field(None, max_length=50, description="Icon untuk UI")
    is_active: bool = Field(default=True, description="Status aktif")
    sort_order: int = Field(default=0, description="Urutan")
    description: Optional[str] = Field(None, description="Deskripsi")

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        return v.strip().upper()


class PaymentMethodUpdate(BaseModel):
    """Schema untuk update payment method."""
    name: Optional[str] = Field(None, min_length=1, max_length=50, description="Nama metode")
    code: Optional[str] = Field(None, min_length=1, max_length=20, description="Kode unik")
    icon: Optional[str] = Field(None, max_length=50, description="Icon untuk UI")
    is_active: Optional[bool] = Field(None, description="Status aktif")
    sort_order: Optional[int] = Field(None, description="Urutan")
    description: Optional[str] = Field(None, description="Deskripsi")


class PaymentMethodResponse(BaseModel):
    """Response untuk payment method."""
    id: UUID
    name: str
    code: str
    icon: Optional[str] = None
    is_active: bool
    sort_order: int
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# INQUIRY STATUS WORKFLOW
# ============================================================================

class StatusWorkflowCreate(BaseModel):
    """Schema untuk membuat status workflow."""
    from_status: str = Field(..., min_length=1, max_length=50, description="Status asal")
    to_status: str = Field(..., min_length=1, max_length=50, description="Status tujuan")
    sort_order: int = Field(default=0, description="Urutan")
    is_active: bool = Field(default=True, description="Status aktif")

    @field_validator("from_status")
    @classmethod
    def validate_from_status(cls, v: str) -> str:
        valid_statuses = ["new", "under_review", "contacted", "quoted", "approved", "converted", "rejected", "closed", "completed"]
        if v not in valid_statuses:
            raise ValueError(f"from_status must be one of: {valid_statuses}")
        return v

    @field_validator("to_status")
    @classmethod
    def validate_to_status(cls, v: str) -> str:
        valid_statuses = ["new", "under_review", "contacted", "quoted", "approved", "converted", "rejected", "closed", "completed"]
        if v not in valid_statuses:
            raise ValueError(f"to_status must be one of: {valid_statuses}")
        return v

    @field_validator("to_status")
    @classmethod
    def validate_different_status(cls, v: str, info) -> str:
        from_status = info.data.get("from_status")
        if from_status and v == from_status:
            raise ValueError("from_status and to_status cannot be the same")
        return v


class StatusWorkflowUpdate(BaseModel):
    """Schema untuk update status workflow."""
    from_status: Optional[str] = Field(None, min_length=1, max_length=50, description="Status asal")
    to_status: Optional[str] = Field(None, min_length=1, max_length=50, description="Status tujuan")
    sort_order: Optional[int] = Field(None, description="Urutan")
    is_active: Optional[bool] = Field(None, description="Status aktif")


class StatusWorkflowResponse(BaseModel):
    """Response untuk status workflow."""
    id: UUID
    from_status: str
    to_status: str
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# COMPOSITE SETTINGS RESPONSE
# ============================================================================

class AllSettingsResponse(BaseModel):
    """Response untuk semua settings dalam satu request."""
    workshop: Optional[WorkshopSettingsResponse] = None
    pricing: Optional[PricingSettingsResponse] = None
    security: Optional[SecuritySettingsResponse] = None
    whatsapp_templates: List[WhatsAppTemplateResponse] = Field(default_factory=list)
    project_types: List[ProjectTypeResponse] = Field(default_factory=list)
    payment_methods: List[PaymentMethodResponse] = Field(default_factory=list)
    status_workflows: List[StatusWorkflowResponse] = Field(default_factory=list)


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Workshop
    "WorkshopSettingsResponse",
    "WorkshopSettingsUpdate",
    
    # Pricing
    "PricingSettingsResponse",
    "PricingSettingsUpdate",
    
    # Security
    "SecuritySettingsResponse",
    "SecuritySettingsUpdate",
    
    # WhatsApp
    "WhatsAppTemplateCreate",
    "WhatsAppTemplateUpdate",
    "WhatsAppTemplateResponse",
    
    # Project Types
    "ProjectTypeCreate",
    "ProjectTypeUpdate",
    "ProjectTypeResponse",
    
    # Payment Methods
    "PaymentMethodCreate",
    "PaymentMethodUpdate",
    "PaymentMethodResponse",
    
    # Status Workflow
    "StatusWorkflowCreate",
    "StatusWorkflowUpdate",
    "StatusWorkflowResponse",
    
    # Composite
    "AllSettingsResponse",
]