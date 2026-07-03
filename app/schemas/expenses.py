# schemas/expenses.py
from pydantic import BaseModel, Field
from uuid import UUID
from decimal import Decimal
from datetime import date, datetime
from typing import Optional

from schemas.constants import ExpenseStatus


class ExpenseCreate(BaseModel):
    """Schema untuk membuat expense baru."""
    project_id: Optional[UUID] = Field(None, description="ID project (opsional)")
    category: str = Field(..., max_length=100, description="Kategori expense")
    description: str = Field(..., max_length=1000, description="Deskripsi expense")
    amount: Decimal = Field(..., gt=0, description="Jumlah biaya")
    expense_date: date = Field(default_factory=date.today, description="Tanggal expense")
    payment_method: Optional[str] = Field(None, max_length=50, description="Metode pembayaran")
    reference_number: Optional[str] = Field(None, max_length=100, description="Nomor referensi")
    notes: Optional[str] = Field(None, description="Catatan tambahan")
    status: Optional[str] = Field(ExpenseStatus.PENDING, description="Status expense")


class ExpenseUpdate(BaseModel):
    """Schema untuk update expense."""
    project_id: Optional[UUID] = Field(None, description="ID project")
    category: Optional[str] = Field(None, max_length=100, description="Kategori expense")
    description: Optional[str] = Field(None, max_length=1000, description="Deskripsi expense")
    amount: Optional[Decimal] = Field(None, gt=0, description="Jumlah biaya")
    expense_date: Optional[date] = Field(None, description="Tanggal expense")
    payment_method: Optional[str] = Field(None, max_length=50, description="Metode pembayaran")
    reference_number: Optional[str] = Field(None, max_length=100, description="Nomor referensi")
    notes: Optional[str] = Field(None, description="Catatan tambahan")
    status: Optional[str] = Field(None, description="Status expense")


class ExpenseResponse(BaseModel):
    """Response untuk expense."""
    id: UUID
    project_id: Optional[UUID] = None
    project_name: Optional[str] = None
    category: str
    description: str
    amount: Decimal
    expense_date: date
    payment_method: Optional[str] = None
    reference_number: Optional[str] = None
    status: str
    notes: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExpenseApprove(BaseModel):
    """Schema untuk approve expense."""
    approved_by: str = Field(..., min_length=1, description="Nama yang approve")
    notes: Optional[str] = Field(None, description="Catatan approval")