from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from enum import Enum


# ---------- Enums ----------
class InquiryStatus(str, Enum):
    NEW = "new"
    REVIEW = "review"
    QUOTED = "quoted"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONVERTED = "converted"
    
class ConvertToProjectRequest(BaseModel):
    project_start_date: Optional[datetime] = None
    project_target_delivery: Optional[datetime] = None

# ---------- Nested response schemas ----------
class InquiryPhotoResponse(BaseModel):
    id: UUID
    file_path: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class InquiryActivityResponse(BaseModel):
    id: UUID
    activity: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ProjectMinimalResponse(BaseModel):
    id: UUID
    name: str
    status: str          # e.g. "active", "completed"
    progress: int        # 0–100

    model_config = ConfigDict(from_attributes=True)

# ---------- Request schema ----------
class CustomerInquiryRequest(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=100, strip_whitespace=True)
    customer_phone_number: str = Field(..., min_length=8, max_length=20, strip_whitespace=True)
    customer_email: EmailStr
    vehicle_brand: str = Field(..., min_length=1, max_length=50, strip_whitespace=True)
    vehicle_model: str = Field(..., min_length=1, max_length=100, strip_whitespace=True)
    vehicle_license_plate: Optional[str] = Field(None, max_length=20, strip_whitespace=True)
    vehicle_condition: str = Field(..., min_length=1, max_length=100, strip_whitespace=True)
    project_type: str = Field(..., min_length=1, max_length=500, strip_whitespace=True)
    project_description: str = Field(..., min_length=10, max_length=5000, strip_whitespace=True)
    project_target: Optional[str] = Field(None, max_length=255, strip_whitespace=True)
    reference_link: Optional[str] = Field(None, strip_whitespace=True)

    estimated_budget: Optional[int] = None
    # Auto‑strip all string fields using a validator (backup)
    @field_validator("*", mode="before")
    @classmethod
    def strip_strings(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

# ---------- Full detail response ----------
class CustomerInquiryResponse(BaseModel):
    id: UUID

    # Customer
    customer_name: str
    customer_phone_number: str
    customer_email: Optional[str] = None

    # Vehicle
    vehicle_brand: str
    vehicle_model: str
    vehicle_license_plate: Optional[str] = None
    vehicle_condition: str

    # Project request
    project_type: str
    project_description: str
    project_target: Optional[str] = None
    reference_link: Optional[str] = None
    estimated_budget: Optional[int] = None   # in Rupiah

    # Status & metadata
    status: InquiryStatus
    note: Optional[str] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime
    

    # Relationships
    photos: Optional[List[InquiryPhotoResponse]] = Field(None)
    activities: List[InquiryActivityResponse] = Field(default_factory=list)
    project: Optional[ProjectMinimalResponse] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @property
    def display_status(self) -> str:
        """Human‑readable status (useful for frontend)."""
        mapping = {
            InquiryStatus.NEW: "New",
            InquiryStatus.REVIEW: "Review",
            InquiryStatus.QUOTED: "Quoted",
            InquiryStatus.APPROVED: "Approved",
            InquiryStatus.REJECTED: "Rejected",
            InquiryStatus.CONVERTED: "Converted",
        }
        return mapping.get(self.status, self.status.value.upper())

# ---------- Action request schemas ----------
class InquiryApproved(BaseModel):
    note: Optional[str] = None

class InquiryReject(BaseModel):
    reason: str

class InquirySendQuotation(BaseModel):
    estimated_cost: float
    estimated_revenue: float

class InquiryNotifyCustomer(BaseModel):
    channel: str = Field(default="email")   # email | whatsapp | telegram

class InquiryStatusUpdate(BaseModel):
    status: str

class NoteUpdate(BaseModel):
    note: str
    
class CustomerInquirySummary(BaseModel):
    id: UUID
    customer_name: str
    vehicle_brand: str
    vehicle_model: str
    project_type: str
    status: InquiryStatus
    created_at: datetime
    project: Optional[ProjectMinimalResponse] = None   # ← field opsional

    model_config = ConfigDict(from_attributes=True)   # ← WAJIB
    
class CustomerInquiryPhotoSummary(BaseModel):
    id: UUID
    file_path: str
    stage: str
    created_at: datetime