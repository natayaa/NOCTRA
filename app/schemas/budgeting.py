# schemas/budgeting.py
from pydantic import BaseModel, Field
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from datetime import date, datetime


class SummaryResponse(BaseModel):
    """Summary cards data for budgeting dashboard."""
    active_projects: int = Field(..., description="Jumlah project aktif")
    pending_payments: Decimal = Field(..., description="Total pending payments")
    material_cost_ratio: float = Field(..., description="Rasio biaya material terhadap revenue")
    avg_project_profit: Decimal = Field(..., description="Rata-rata profit per project")


class KPIsResponse(BaseModel):
    """Main KPIs for budgeting."""
    revenue: Decimal = Field(..., description="Total pendapatan")
    expenses: Decimal = Field(..., description="Total pengeluaran")
    net_profit: Decimal = Field(..., description="Laba bersih")
    cash_available: Decimal = Field(..., description="Kas tersedia")


class MonthlyExpensePoint(BaseModel):
    """Monthly expense data point for line chart."""
    month: str = Field(..., description="Nama bulan (Jan 2026)")
    amount: Decimal = Field(..., description="Total pengeluaran")


class BreakdownItem(BaseModel):
    """Expense breakdown item for pie chart."""
    category: str = Field(..., description="Kategori pengeluaran")
    amount: Decimal = Field(..., description="Total pengeluaran")
    percentage: float = Field(..., description="Persentase dari total")


class CashflowPoint(BaseModel):
    """Cashflow data point for bar chart."""
    month: str = Field(..., description="Nama bulan")
    revenue: Decimal = Field(..., description="Pendapatan")
    expenses: Decimal = Field(..., description="Pengeluaran")


class ProjectProfitabilityItem(BaseModel):
    """Project profitability data."""
    project_name: str = Field(..., description="Nama project")
    revenue: Decimal = Field(..., description="Pendapatan")
    cost: Decimal = Field(..., description="Biaya")
    profit: Decimal = Field(..., description="Laba")
    margin: float = Field(..., description="Margin persentase")
    status: str = Field(..., description="success, warning, danger")


class BudgetingExpenseCreate(BaseModel):
    """Schema untuk membuat expense baru di budgeting."""
    project_id: Optional[UUID] = Field(None, description="ID project (opsional)")
    category: str = Field(..., max_length=100, description="Kategori expense")
    description: str = Field(..., max_length=1000, description="Deskripsi")
    amount: Decimal = Field(..., gt=0, description="Jumlah biaya")
    expense_date: date = Field(default_factory=date.today, description="Tanggal expense")
    payment_method: Optional[str] = Field(None, max_length=50, description="Metode pembayaran")
    reference_number: Optional[str] = Field(None, max_length=100, description="Nomor referensi")
    notes: Optional[str] = Field(None, description="Catatan tambahan")


class BudgetingExpenseUpdate(BaseModel):
    """Schema untuk update expense."""
    project_id: Optional[UUID] = Field(None, description="ID project")
    category: Optional[str] = Field(None, max_length=100, description="Kategori expense")
    description: Optional[str] = Field(None, max_length=1000, description="Deskripsi")
    amount: Optional[Decimal] = Field(None, gt=0, description="Jumlah biaya")
    expense_date: Optional[date] = Field(None, description="Tanggal expense")
    payment_method: Optional[str] = Field(None, max_length=50, description="Metode pembayaran")
    reference_number: Optional[str] = Field(None, max_length=100, description="Nomor referensi")
    notes: Optional[str] = Field(None, description="Catatan tambahan")


class BudgetingExpenseResponse(BaseModel):
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
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}