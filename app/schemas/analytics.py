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
    value: Decimal | float | int
    trend_percent: Optional[float] = Field(None, description="Persentase perubahan vs periode sebelumnya")

class KPIsResponse(BaseModel):
    total_revenue: KPITrend | Decimal
    net_profit: KPITrend | Decimal
    conversion_rate: KPITrend | float
    completed_projects: KPITrend | int
    low_stock_items: Optional[int] = 0
    active_projects: Optional[int] = 0
    period: str = Field(..., description="Periode yang digunakan (today, week, month, quarter, year)")


# -----------------------------------------------------------------------------
# Revenue vs Profit Chart
# -----------------------------------------------------------------------------

class RevenueProfitDataPoint(BaseModel):
    label: str
    revenue: float
    profit: float

class RevenueProfitResponse(BaseModel):
    period: str
    data: List[RevenueProfitDataPoint]


# -----------------------------------------------------------------------------
# Conversion Chart
# -----------------------------------------------------------------------------

class ConversionDataPoint(BaseModel):
    label: str
    inquiries: int
    conversions: int

class ConversionResponse(BaseModel):
    period: str
    data: List[ConversionDataPoint]


# -----------------------------------------------------------------------------
# Service Breakdown (Pie Chart)
# -----------------------------------------------------------------------------

class ServiceBreakdownItem(BaseModel):
    name: str
    value: float  # percentage
    color: Optional[str] = None  # hex color

class ServiceBreakdownResponse(BaseModel):
    items: List[ServiceBreakdownItem]


# -----------------------------------------------------------------------------
# Material Consumption (Pie Chart)
# -----------------------------------------------------------------------------

class MaterialConsumptionItem(BaseModel):
    name: str
    value: float  # percentage
    color: Optional[str] = None

class MaterialConsumptionResponse(BaseModel):
    items: List[MaterialConsumptionItem]


# -----------------------------------------------------------------------------
# Top Services
# -----------------------------------------------------------------------------

class TopServiceItem(BaseModel):
    name: str
    projects: int
    revenue: Decimal
    trend: Optional[float] = None  # % growth compared to previous period

class TopServicesResponse(BaseModel):
    items: List[TopServiceItem]


# -----------------------------------------------------------------------------
# Operational KPIs
# -----------------------------------------------------------------------------

class OperationalKPIItem(BaseModel):
    label: str
    value: str | float | int
    progress: Optional[int] = Field(None, description="Persentase untuk progress bar (0-100)")
    color: Optional[str] = Field(None, description="success, warning, danger, atau custom")

class OperationalKPIsResponse(BaseModel):
    items: List[OperationalKPIItem]


# -----------------------------------------------------------------------------
# Insights
# -----------------------------------------------------------------------------

class InsightItem(BaseModel):
    icon: str  # FontAwesome class
    message: str
    type: str = Field(..., description="positive, warning, neutral")
    link: Optional[str] = None

class InsightsResponse(BaseModel):
    items: List[InsightItem]


# -----------------------------------------------------------------------------
# Full Analytics Response (untuk satu endpoint jika ingin)
# -----------------------------------------------------------------------------

class FullAnalyticsResponse(BaseModel):
    period: str
    kpis: KPIsResponse
    revenue_profit: RevenueProfitResponse
    conversion: ConversionResponse
    service_breakdown: ServiceBreakdownResponse
    material_consumption: MaterialConsumptionResponse
    top_services: TopServicesResponse
    operational_kpis: OperationalKPIsResponse
    insights: InsightsResponse