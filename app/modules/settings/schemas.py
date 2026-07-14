# modules/settings/schemas.py
from pydantic import BaseModel, Field, ConfigDict, EmailStr, HttpUrl
from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime
from decimal import Decimal


# ============================================================
# WORKSHOP SETTINGS
# ============================================================
class WorkshopSettingsResponse(BaseModel):
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
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    address: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=30)
    email: Optional[EmailStr] = None
    website: Optional[HttpUrl] = None
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    primary_color: Optional[str] = Field(None, pattern=r'^#[0-9a-fA-F]{6}$')


# ============================================================
# PRICING SETTINGS
# ============================================================
class PricingSettingsResponse(BaseModel):
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
    paint_base_price: Optional[int] = Field(None, ge=0)
    restoration_base_price: Optional[int] = Field(None, ge=0)
    detailing_base_price: Optional[int] = Field(None, ge=0)
    custom_color_surcharge: Optional[int] = Field(None, ge=0)
    labor_painter_per_day: Optional[int] = Field(None, ge=0)
    labor_body_per_day: Optional[int] = Field(None, ge=0)
    labor_assembly_per_day: Optional[int] = Field(None, ge=0)
    labor_supervisor_per_day: Optional[int] = Field(None, ge=0)
    tax_percent: Optional[Decimal] = Field(None, ge=0, le=100)
    default_margin_percent: Optional[Decimal] = Field(None, ge=0, le=100)
    default_duration_days: Optional[int] = Field(None, ge=1, le=365)
    deposit_percent: Optional[Decimal] = Field(None, ge=0, le=100)
    currency: Optional[str] = Field(None, max_length=10)
    auto_generate_invoice: Optional[bool] = None
    email_notifications_enabled: Optional[bool] = None
    whatsapp_notifications_enabled: Optional[bool] = None


# ============================================================
# SECURITY SETTINGS
# ============================================================
class SecuritySettingsResponse(BaseModel):
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
    require_mfa: Optional[bool] = None
    allow_remember_me: Optional[bool] = None
    force_password_change_days: Optional[int] = Field(None, ge=0, le=365)
    session_timeout_minutes: Optional[int] = Field(None, ge=5, le=480)
    max_login_attempts: Optional[int] = Field(None, ge=3, le=20)
    lockout_duration_minutes: Optional[int] = Field(None, ge=5, le=1440)


# ============================================================
# WHATSAPP TEMPLATE
# ============================================================
class WhatsAppTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    template: str = Field(..., min_length=1)
    description: Optional[str] = None
    is_default: bool = False
    variables: Optional[Dict[str, str]] = None


class WhatsAppTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    template: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    is_default: Optional[bool] = None
    variables: Optional[Dict[str, str]] = None


class WhatsAppTemplateResponse(BaseModel):
    id: UUID
    name: str
    template: str
    description: Optional[str] = None
    is_default: bool
    variables: Optional[Dict[str, str]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# PROJECT TYPES
# ============================================================
class ProjectTypeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    base_price: Optional[int] = Field(None, ge=0)
    is_active: bool = True
    sort_order: int = 0


class ProjectTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None
    base_price: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class ProjectTypeResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    base_price: Optional[int] = None
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# PAYMENT METHODS
# ============================================================
class PaymentMethodCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    code: str = Field(..., min_length=1, max_length=20)
    icon: Optional[str] = Field(None, max_length=50)
    is_active: bool = True
    sort_order: int = 0
    description: Optional[str] = None


class PaymentMethodUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    code: Optional[str] = Field(None, min_length=1, max_length=20)
    icon: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None
    description: Optional[str] = None


class PaymentMethodResponse(BaseModel):
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


# ============================================================
# INQUIRY STATUS WORKFLOW
# ============================================================
class StatusWorkflowCreate(BaseModel):
    from_status: str = Field(..., min_length=1, max_length=50)
    to_status: str = Field(..., min_length=1, max_length=50)
    sort_order: int = 0
    is_active: bool = True


class StatusWorkflowUpdate(BaseModel):
    from_status: Optional[str] = Field(None, min_length=1, max_length=50)
    to_status: Optional[str] = Field(None, min_length=1, max_length=50)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class StatusWorkflowResponse(BaseModel):
    id: UUID
    from_status: str
    to_status: str
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# COMPOSITE SETTINGS RESPONSE
# ============================================================
class AllSettingsResponse(BaseModel):
    workshop: WorkshopSettingsResponse
    pricing: PricingSettingsResponse
    security: SecuritySettingsResponse
    whatsapp_templates: List[WhatsAppTemplateResponse]
    project_types: List[ProjectTypeResponse]
    payment_methods: List[PaymentMethodResponse]
    status_workflows: List[StatusWorkflowResponse]
