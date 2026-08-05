# modules/restored_bikes/schemas.py

import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, HttpUrl, validator

from core.enum import RestoredBikeStatus, InitialCondition


# ============================================================
# BASE SCHEMAS
# ============================================================

class RestoredBikeBase(BaseModel):
    brand: str = Field(..., min_length=2, max_length=100)
    model: str = Field(..., min_length=2, max_length=100)
    year: Optional[int] = Field(None, ge=1950, le=2035)
    license_plate: Optional[str] = Field(None, max_length=20)

    customer_name: Optional[str] = Field(None, max_length=200)
    purchase_price: Optional[float] = Field(None, ge=0)
    purchase_source: Optional[str] = Field(None, max_length=200)
    initial_condition: Optional[InitialCondition] = None

    restoration_cost: Optional[float] = Field(None, ge=0)
    restoration_duration: Optional[int] = Field(None, ge=1)
    technician_name: Optional[str] = Field(None, max_length=100)
    status: RestoredBikeStatus = RestoredBikeStatus.COMPLETED
    restoration_notes: Optional[str] = None

    is_featured: bool = False

    @validator("license_plate")
    def validate_license_plate(cls, v):
        if v:
            return v.upper().replace(" ", "")
        return v


class RestoredBikeCreate(RestoredBikeBase):
    pass


class RestoredBikeUpdate(BaseModel):
    brand: Optional[str] = Field(None, min_length=2, max_length=100)
    model: Optional[str] = Field(None, min_length=2, max_length=100)
    year: Optional[int] = Field(None, ge=1950, le=2035)
    license_plate: Optional[str] = Field(None, max_length=20)

    customer_name: Optional[str] = Field(None, max_length=200)
    purchase_price: Optional[float] = Field(None, ge=0)
    purchase_source: Optional[str] = Field(None, max_length=200)
    initial_condition: Optional[InitialCondition] = None

    restoration_cost: Optional[float] = Field(None, ge=0)
    restoration_duration: Optional[int] = Field(None, ge=1)
    technician_name: Optional[str] = Field(None, max_length=100)
    status: Optional[RestoredBikeStatus] = None
    restoration_notes: Optional[str] = None

    is_featured: Optional[bool] = None


# ============================================================
# PHOTO SCHEMAS
# ============================================================

class RestoredBikePhotoBase(BaseModel):
    url: str
    file_path: str
    filename: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    is_primary: bool = False
    sort_order: int = 0


class RestoredBikePhotoCreate(RestoredBikePhotoBase):
    bike_id: uuid.UUID


class RestoredBikePhotoResponse(RestoredBikePhotoBase):
    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# DOCUMENT SCHEMAS
# ============================================================

class RestoredBikeDocumentBase(BaseModel):
    filename: str
    file_path: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    document_type: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None


class RestoredBikeDocumentCreate(RestoredBikeDocumentBase):
    bike_id: uuid.UUID


class RestoredBikeDocumentResponse(RestoredBikeDocumentBase):
    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# RESPONSE SCHEMAS
# ============================================================

class RestoredBikeResponse(RestoredBikeBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    photos: List[RestoredBikePhotoResponse] = []
    documents: List[RestoredBikeDocumentResponse] = []

    @property
    def cover_image(self) -> Optional[str]:
        if self.photos:
            primary = next((p for p in self.photos if p.is_primary), None)
            if primary:
                return primary.url
            return self.photos[0].url
        return None

    class Config:
        from_attributes = True


class RestoredBikeSummary(RestoredBikeBase):
    id: uuid.UUID
    created_at: datetime
    cover_image: Optional[str] = None
    photo_count: int = 0

    class Config:
        from_attributes = True


class RestoredBikeStats(BaseModel):
    total: int = 0
    completed: int = 0
    in_progress: int = 0
    featured: int = 0
    by_brand: Optional[dict] = None


# ============================================================
# PAGINATION
# ============================================================

class PaginatedRestoredBikeResponse(BaseModel):
    success: bool = True
    message: str = "Success"
    data: List[RestoredBikeSummary]
    total: int
    page: int
    limit: int
    total_pages: int
