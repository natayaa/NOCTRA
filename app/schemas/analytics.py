# schemas/analytics.py
from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from typing import Optional, List
from uuid import UUID


# -----------------------------------------------------------------------------
# KPI Response
# -----------------------------------------------------------------------------

class KPITrend(BaseModel):
    value: float = Field(..., description="Nilai KPI saat ini")
    trend_percent: Optional[float] = Field(None, description="Persentase perubahan vs periode sebelumnya")

    @classmethod
    def from_decimal(cls, value: Decimal, trend: Optional[Decimal] = None):
        return cls(
            value=float(value),
            trend_percent=float(trend) if trend is not None else None
        )


class KPIsResponse(BaseModel):
    total_revenue: KPITrend = Field(..., description="Total pendapatan")
    net_profit: KPITrend = Field(..., description="Laba bersih")
    conversion_rate: KPITrend = Field(..., description="Rate konversi inquiry ke project")
    completed_projects: KPITrend = Field(..., description="Jumlah project selesai")
    low_stock_items: int = Field(0, description="Jumlah item dengan stok rendah")
    active_projects: int = Field(0, description="Jumlah project aktif")
    period: str = Field(..., description="Periode yang digunakan (today, week, month, quarter, year)")


# -----------------------------------------------------------------------------
# Revenue vs Profit Chart
# -----------------------------------------------------------------------------

class RevenueProfitDataPoint(BaseModel):
    label: str = Field(..., description="Label untuk sumbu X (tanggal/minggu/bulan)")
    revenue: float = Field(..., description="Pendapatan")
    profit: float = Field(..., description="Laba")


class RevenueProfitResponse(BaseModel):
    period: str = Field(..., description="Periode yang digunakan")
    data: List[RevenueProfitDataPoint] = Field(default_factory=list, description="Data chart")


# -----------------------------------------------------------------------------
# Conversion Chart
# -----------------------------------------------------------------------------

class ConversionDataPoint(BaseModel):
    label: str = Field(..., description="Label untuk sumbu X")
    inquiries: int = Field(..., description="Jumlah inquiry")
    conversions: int = Field(..., description="Jumlah konversi")


class ConversionResponse(BaseModel):
    period: str = Field(..., description="Periode yang digunakan")
    data: List[ConversionDataPoint] = Field(default_factory=list, description="Data chart")


# -----------------------------------------------------------------------------
# Service Breakdown (Pie Chart)
# -----------------------------------------------------------------------------

class ServiceBreakdownItem(BaseModel):
    name: str = Field(..., description="Nama service")
    value: float = Field(..., description="Persentase")
    color: Optional[str] = Field(None, description="Warna hex")


class ServiceBreakdownResponse(BaseModel):
    items: List[ServiceBreakdownItem] = Field(default_factory=list, description="Data pie chart")


# -----------------------------------------------------------------------------
# Material Consumption (Pie Chart)
# -----------------------------------------------------------------------------

class MaterialConsumptionItem(BaseModel):
    name: str = Field(..., description="Nama material")
    value: float = Field(..., description="Persentase")
    color: Optional[str] = Field(None, description="Warna hex")


class MaterialConsumptionResponse(BaseModel):
    items: List[MaterialConsumptionItem] = Field(default_factory=list, description="Data pie chart")


# -----------------------------------------------------------------------------
# Top Services
# -----------------------------------------------------------------------------

class TopServiceItem(BaseModel):
    name: str = Field(..., description="Nama service")
    projects: int = Field(..., description="Jumlah project")
    revenue: Decimal = Field(..., description="Total pendapatan")
    trend: Optional[float] = Field(None, description="Persentase pertumbuhan")


class TopServicesResponse(BaseModel):
    items: List[TopServiceItem] = Field(default_factory=list, description="Data top services")


# -----------------------------------------------------------------------------
# Operational KPIs
# -----------------------------------------------------------------------------

class OperationalKPIItem(BaseModel):
    label: str = Field(..., description="Label KPI")
    value: str = Field(..., description="Nilai KPI dalam format string")
    progress: Optional[int] = Field(None, description="Persentase untuk progress bar (0-100)")
    color: Optional[str] = Field(None, description="success, warning, danger, atau custom")
    status: Optional[str] = Field(None, description="Status untuk indikator")


class OperationalKPIsResponse(BaseModel):
    items: List[OperationalKPIItem] = Field(default_factory=list, description="Data operational KPIs")


# -----------------------------------------------------------------------------
# Insights
# -----------------------------------------------------------------------------

class InsightItem(BaseModel):
    icon: str = Field(..., description="FontAwesome class")
    message: str = Field(..., description="Pesan insight")
    type: str = Field(..., description="positive, warning, neutral")
    link: Optional[str] = Field(None, description="Link untuk tindakan")


class InsightsResponse(BaseModel):
    items: List[InsightItem] = Field(default_factory=list, description="Data insights")


# -----------------------------------------------------------------------------
# Full Analytics Response (untuk satu endpoint jika ingin)
# -----------------------------------------------------------------------------

class FullAnalyticsResponse(BaseModel):
    period: str = Field(..., description="Periode yang digunakan")
    kpis: KPIsResponse = Field(..., description="Data KPIs")
    revenue_profit: RevenueProfitResponse = Field(..., description="Data revenue vs profit")
    conversion: ConversionResponse = Field(..., description="Data conversion")
    service_breakdown: ServiceBreakdownResponse = Field(..., description="Data service breakdown")
    material_consumption: MaterialConsumptionResponse = Field(..., description="Data material consumption")
    top_services: TopServicesResponse = Field(..., description="Data top services")
    operational_kpis: OperationalKPIsResponse = Field(..., description="Data operational KPIs")
    insights: InsightsResponse = Field(..., description="Data insights")