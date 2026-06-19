# schemas/budgeting.py
from pydantic import BaseModel
from decimal import Decimal
from typing import List, Optional


class SummaryResponse(BaseModel):
    active_projects: int
    pending_payments: Decimal
    material_cost_ratio: float  # persentase
    avg_project_profit: Decimal


class KPIsResponse(BaseModel):
    revenue: Decimal
    expenses: Decimal
    net_profit: Decimal
    cash_available: Decimal


class MonthlyExpensePoint(BaseModel):
    month: str
    amount: Decimal


class BreakdownItem(BaseModel):
    category: str
    amount: Decimal
    percentage: float


class CashflowPoint(BaseModel):
    month: str
    revenue: Decimal
    expenses: Decimal


class ProjectProfitabilityItem(BaseModel):
    project_name: str
    revenue: Decimal
    cost: Decimal
    profit: Decimal
    margin: float  # persentase
    status: str  # success, warning, danger