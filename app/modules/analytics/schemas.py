"""Pydantic schemas for analytics DTOs."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


# ════════════════════════════════════════════════════════════════
# KPIs
# ════════════════════════════════════════════════════════════════

class KpiCard(BaseModel):
    key: str
    label: str
    value: float
    formatted: str
    delta_pct: float | None = None
    delta_direction: str | None = None  # "up" | "down" | "flat"
    hint: str | None = None


class KpiSet(BaseModel):
    period_from: date
    period_to: date
    cards: list[KpiCard]


# ════════════════════════════════════════════════════════════════
# TIME SERIES
# ════════════════════════════════════════════════════════════════

class SeriesPoint(BaseModel):
    period: date
    value: float


class SeriesSet(BaseModel):
    label: str
    interval: str
    points: list[SeriesPoint]


class CashFlowPoint(BaseModel):
    period: date
    inflow: float
    outflow: float
    net: float


# ════════════════════════════════════════════════════════════════
# PROFITABILITY
# ════════════════════════════════════════════════════════════════

class ProfitabilityRow(BaseModel):
    key: str
    label: str
    project_count: int
    revenue: float
    cogs: float
    gross_profit: float
    gross_margin_pct: float
    avg_project_value: float


# ════════════════════════════════════════════════════════════════
# CUSTOMER VALUE
# ════════════════════════════════════════════════════════════════

class CustomerValueRow(BaseModel):
    customer_id: UUID
    code: str
    name: str
    project_count: int
    total_revenue: float
    total_cost: float
    gross_profit: float
    margin_pct: float
    last_project_date: date | None


# ════════════════════════════════════════════════════════════════
# MATERIAL SPEND
# ════════════════════════════════════════════════════════════════

class MaterialSpendRow(BaseModel):
    material_id: UUID
    code: str
    name: str
    category: str
    unit: str
    total_consumed: float
    total_cost: float


# ════════════════════════════════════════════════════════════════
# ESTIMATE ACCURACY
# ════════════════════════════════════════════════════════════════

class EstimateAccuracyStats(BaseModel):
    project_count: int
    avg_variance_pct: float
    median_variance_pct: float
    worst_overrun_pct: float
    best_case_pct: float
    avg_estimated_hpp: float
    avg_actual_hpp: float


# ════════════════════════════════════════════════════════════════
# FUNNEL
# ════════════════════════════════════════════════════════════════

class FunnelStage(BaseModel):
    status: str
    label: str
    count: int
    pct_of_total: float


class InquiryFunnel(BaseModel):
    total: int
    stages: list[FunnelStage]


# ════════════════════════════════════════════════════════════════
# ACTIVITY
# ════════════════════════════════════════════════════════════════

class ActivityEntry(BaseModel):
    id: UUID
    action: str
    table_name: str
    record_id: str
    user_id: UUID | None
    created_at: datetime