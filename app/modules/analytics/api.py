"""REST endpoints for analytics."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from app.core.constants import PermissionCode
from app.core.deps import DbSession
from app.modules.analytics.constants import (
    INTERVAL_LABELS,
    INTERVALS,
    PERIOD_LABELS,
    PERIOD_PRESETS,
    resolve_period,
)
from app.modules.analytics.schemas import (
    ActivityEntry,
    CashFlowPoint,
    CustomerValueRow,
    EstimateAccuracyStats,
    InquiryFunnel,
    KpiSet,
    MaterialSpendRow,
    ProfitabilityRow,
    SeriesSet,
)
from app.modules.analytics.service import AnalyticsService
from app.modules.auth.dependencies import require_permission

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _range(
    preset: str = Query("month"),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
) -> tuple[date, date]:
    return resolve_period(preset, from_date=from_date, to_date=to_date)


@router.get("/catalog")
async def catalog() -> dict:
    return {
        "period_presets": PERIOD_PRESETS,
        "period_labels": PERIOD_LABELS,
        "intervals": INTERVALS,
        "interval_labels": INTERVAL_LABELS,
    }


@router.get("/kpis", response_model=KpiSet)
async def kpis(
    db: DbSession,
    range_: tuple[date, date] = Depends(_range),
    _=Depends(require_permission(PermissionCode.ANALYTICS_READ)),
) -> KpiSet:
    f, t = range_
    return await AnalyticsService(db).kpis(f, t)


@router.get("/revenue", response_model=SeriesSet)
async def revenue_series(
    db: DbSession,
    range_: tuple[date, date] = Depends(_range),
    interval: str | None = Query(None),
    _=Depends(require_permission(PermissionCode.ANALYTICS_READ)),
) -> SeriesSet:
    f, t = range_
    return await AnalyticsService(db).revenue_series(f, t, interval)


@router.get("/expenses", response_model=SeriesSet)
async def expense_series(
    db: DbSession,
    range_: tuple[date, date] = Depends(_range),
    interval: str | None = Query(None),
    _=Depends(require_permission(PermissionCode.ANALYTICS_READ)),
) -> SeriesSet:
    f, t = range_
    return await AnalyticsService(db).expense_series(f, t, interval)


@router.get("/gross-profit", response_model=SeriesSet)
async def gross_profit_series(
    db: DbSession,
    range_: tuple[date, date] = Depends(_range),
    interval: str | None = Query(None),
    _=Depends(require_permission(PermissionCode.ANALYTICS_READ)),
) -> SeriesSet:
    f, t = range_
    return await AnalyticsService(db).gross_profit_series(f, t, interval)


@router.get("/cash-flow", response_model=list[CashFlowPoint])
async def cash_flow(
    db: DbSession,
    range_: tuple[date, date] = Depends(_range),
    interval: str | None = Query(None),
    _=Depends(require_permission(PermissionCode.ANALYTICS_READ)),
) -> list[CashFlowPoint]:
    f, t = range_
    return await AnalyticsService(db).cash_flow_series(f, t, interval)


@router.get("/services", response_model=list[ProfitabilityRow])
async def service_profitability(
    db: DbSession,
    range_: tuple[date, date] = Depends(_range),
    _=Depends(require_permission(PermissionCode.ANALYTICS_READ)),
) -> list[ProfitabilityRow]:
    f, t = range_
    return await AnalyticsService(db).service_profitability(f, t)


@router.get("/vehicle-categories", response_model=list[ProfitabilityRow])
async def vehicle_profitability(
    db: DbSession,
    range_: tuple[date, date] = Depends(_range),
    _=Depends(require_permission(PermissionCode.ANALYTICS_READ)),
) -> list[ProfitabilityRow]:
    f, t = range_
    return await AnalyticsService(db).vehicle_category_profitability(f, t)


@router.get("/customers", response_model=list[CustomerValueRow])
async def top_customers(
    db: DbSession,
    range_: tuple[date, date] = Depends(_range),
    limit: int = Query(10, ge=1, le=50),
    _=Depends(require_permission(PermissionCode.ANALYTICS_READ)),
) -> list[CustomerValueRow]:
    f, t = range_
    return await AnalyticsService(db).top_customers(f, t, limit)


@router.get("/materials", response_model=list[MaterialSpendRow])
async def top_materials(
    db: DbSession,
    range_: tuple[date, date] = Depends(_range),
    limit: int = Query(20, ge=1, le=100),
    _=Depends(require_permission(PermissionCode.ANALYTICS_READ)),
) -> list[MaterialSpendRow]:
    f, t = range_
    return await AnalyticsService(db).top_materials(f, t, limit)


@router.get("/estimate-accuracy", response_model=EstimateAccuracyStats)
async def estimate_accuracy(
    db: DbSession,
    range_: tuple[date, date] = Depends(_range),
    _=Depends(require_permission(PermissionCode.ANALYTICS_READ)),
) -> EstimateAccuracyStats:
    f, t = range_
    return await AnalyticsService(db).estimate_accuracy(f, t)


@router.get("/inquiry-funnel", response_model=InquiryFunnel)
async def inquiry_funnel(
    db: DbSession,
    range_: tuple[date, date] = Depends(_range),
    _=Depends(require_permission(PermissionCode.ANALYTICS_READ)),
) -> InquiryFunnel:
    f, t = range_
    return await AnalyticsService(db).inquiry_funnel(f, t)


@router.get("/recent-activity", response_model=list[ActivityEntry])
async def recent_activity(
    db: DbSession,
    limit: int = Query(20, ge=1, le=100),
    _=Depends(require_permission(PermissionCode.ANALYTICS_READ)),
) -> list[ActivityEntry]:
    return await AnalyticsService(db).recent_activity(limit)