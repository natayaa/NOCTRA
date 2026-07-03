# schemas/customer_inquiry.py
from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator, HttpUrl
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from enum import Enum

from schemas.constants import InquiryStatus


# ---------- Nested response schemas ----------
class InquiryPhotoResponse(BaseModel):
    id: UUID
    file_path: str
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    stage: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InquiryActivityResponse(BaseModel):
    id: UUID
    activity: str
    activity_type: Optional[str] = None
    performed_by: Optional[str] = None
    meta_data: Optional[dict] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkshopNoteResponse(BaseModel):
    id: UUID
    note: str
    note_type: str
    author: Optional[str] = None
    is_private: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectMinimalResponse(BaseModel):
    id: UUID
    name: str
    status: str
    progress: int
    estimated_cost: Optional[float] = None
    actual_cost: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------- Request schema ----------
class CustomerInquiryCreate(BaseModel):
    """Schema untuk membuat inquiry baru."""
    customer_name: str = Field(..., min_length=3, max_length=100, description="Nama lengkap customer")
    customer_phone_number: str = Field(..., min_length=8, max_length=20, description="Nomor WhatsApp")
    customer_email: Optional[EmailStr] = Field(None, description="Email customer")
    province: Optional[str] = Field(None, max_length=100, description="Provinsi")
    city: Optional[str] = Field(None, max_length=100, description="Kota/Kabupaten")
    
    vehicle_brand: str = Field(..., min_length=2, max_length=50, description="Merk kendaraan")
    vehicle_model: str = Field(..., min_length=2, max_length=100, description="Model kendaraan")
    vehicle_year: Optional[int] = Field(None, ge=1950, le=2035, description="Tahun kendaraan")
    vehicle_license_plate: Optional[str] = Field(None, max_length=20, description="Plat nomor")
    previous_repaint: Optional[str] = Field(None, max_length=50, description="Riwayat repaint")
    bike_modified: Optional[str] = Field(None, max_length=10, description="Status modifikasi")
    vehicle_condition: Optional[str] = Field(None, max_length=500, description="Kondisi kendaraan")
    
    project_type: str = Field(..., min_length=2, max_length=50, description="Tipe project")
    services: Optional[str] = Field(None, max_length=500, description="Layanan yang dipilih")
    desired_finish: Optional[str] = Field(None, max_length=50, description="Finish yang diinginkan")
    desired_color: Optional[str] = Field(None, max_length=100, description="Warna yang diinginkan")
    estimated_budget: Optional[int] = Field(None, ge=0, description="Estimasi budget")
    deadline: Optional[str] = Field(None, max_length=50, description="Target waktu")
    priority: Optional[str] = Field(None, max_length=50, description="Prioritas utama")
    project_description: str = Field(..., min_length=20, max_length=5000, description="Deskripsi project")
    reference_link: Optional[str] = Field(default=None, description="Link referensi")

    @field_validator("customer_phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        import re
        if not re.match(r'^(\+62|62|08)\d{8,13}$', v):
            raise ValueError('Format nomor telepon tidak valid')
        return v

    @field_validator("*", mode="before")
    @classmethod
    def strip_strings(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value


class CustomerInquiryUpdate(BaseModel):
    """Schema untuk update inquiry."""
    customer_name: Optional[str] = Field(None, min_length=3, max_length=100)
    customer_phone_number: Optional[str] = Field(None, min_length=8, max_length=20)
    customer_email: Optional[EmailStr] = None
    province: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    vehicle_brand: Optional[str] = Field(None, min_length=2, max_length=50)
    vehicle_model: Optional[str] = Field(None, min_length=2, max_length=100)
    vehicle_year: Optional[int] = Field(None, ge=1950, le=2035)
    vehicle_license_plate: Optional[str] = Field(None, max_length=20)
    previous_repaint: Optional[str] = Field(None, max_length=50)
    bike_modified: Optional[str] = Field(None, max_length=10)
    vehicle_condition: Optional[str] = Field(None, max_length=500)
    project_type: Optional[str] = Field(None, min_length=2, max_length=50)
    services: Optional[str] = Field(None, max_length=500)
    desired_finish: Optional[str] = Field(None, max_length=50)
    desired_color: Optional[str] = Field(None, max_length=100)
    estimated_budget: Optional[int] = Field(None, ge=0)
    deadline: Optional[str] = Field(None, max_length=50)
    priority: Optional[str] = Field(None, max_length=50)
    project_description: Optional[str] = Field(None, min_length=20, max_length=5000)
    reference_link: Optional[HttpUrl] = None
    status: Optional[str] = None
    note: Optional[str] = None


# ---------- Response schemas ----------
class CustomerInquirySummary(BaseModel):
    """Ringkasan inquiry untuk list view."""
    id: UUID
    customer_name: str
    customer_phone_number: str
    vehicle_brand: str
    vehicle_model: str
    project_type: str
    status: InquiryStatus
    created_at: datetime
    project: Optional[ProjectMinimalResponse] = None

    model_config = ConfigDict(from_attributes=True)


class CustomerInquiryResponse(BaseModel):
    """Detail inquiry untuk single view."""
    id: UUID
    customer_name: str
    customer_phone_number: str
    customer_email: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    
    vehicle_brand: str
    vehicle_model: str
    vehicle_year: Optional[int] = None
    vehicle_license_plate: Optional[str] = None
    previous_repaint: Optional[str] = None
    bike_modified: Optional[str] = None
    vehicle_condition: Optional[str] = None
    
    project_type: str
    services: Optional[str] = None
    desired_finish: Optional[str] = None
    desired_color: Optional[str] = None
    estimated_budget: Optional[int] = None
    deadline: Optional[str] = None
    priority: Optional[str] = None
    project_description: str
    reference_link: Optional[str] = None

    status: InquiryStatus
    note: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    photos: List[InquiryPhotoResponse] = Field(default_factory=list)
    activities: List[InquiryActivityResponse] = Field(default_factory=list)
    workshop_notes: List[WorkshopNoteResponse] = Field(default_factory=list)
    project: Optional[ProjectMinimalResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ---------- Action schemas ----------
class InquiryStatusUpdate(BaseModel):
    status: str = Field(..., description="Status baru")
    note: Optional[str] = Field(None, description="Catatan perubahan status")


class InquiryReject(BaseModel):
    reason: str = Field(..., min_length=1, description="Alasan penolakan")


class InquirySendQuotation(BaseModel):
    estimated_cost: float = Field(..., gt=0, description="Estimasi biaya")
    notes: Optional[str] = Field(None, description="Catatan quotation")


class InquiryConvertToProject(BaseModel):
    project_name: Optional[str] = Field(None, description="Nama project (opsional)")
    project_start_date: Optional[datetime] = Field(None, description="Tanggal mulai project")
    project_target_delivery: Optional[datetime] = Field(None, description="Target delivery")


class NoteUpdate(BaseModel):
    note: str = Field(..., min_length=1, description="Catatan internal")