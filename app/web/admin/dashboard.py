"""Admin dashboard with real KPIs and charts."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse

from app.core.constants import PermissionCode
from app.core.deps import DbSession
from app.core.exceptions import AppError
from app.core.logging import log
from app.modules.analytics.constants import (
    INTERVAL_LABELS,
    PERIOD_LABELS,
    PERIOD_PRESETS,
    resolve_period,
)
from app.modules.analytics.service import AnalyticsService
from app.modules.auth.dependencies import get_current_user
from app.web.admin._perms import read
from app.web.templates_env import templates

router = APIRouter(prefix="/admin", tags=["admin-dashboard"])


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: DbSession,
    preset: str = Query("month"),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    _=read(PermissionCode.ANALYTICS_READ),
    current=Depends(get_current_user),
) -> HTMLResponse:
    try:
        f, t = resolve_period(preset, from_date=from_date, to_date=to_date)
    except ValueError as exc:
        # Invalid preset / inverted range → render with error banner,
        # not a 500.
        return templates.render(
            request,
            "admin/dashboard.html",
            {
                "title": "Dashboard",
                "current_user": current,
                "error": str(exc),
                "period_preset": "month",
                "period_labels": PERIOD_LABELS,
                "period_presets": PERIOD_PRESETS,
                "period_from": None,
                "period_to": None,
                "interval_label": None,
                "funnel": None,
                "top_customers": [],
                "top_materials": [],
                "accuracy": None,
                "activity": [],
                "chart_periods": [],
                "chart_revenue": [],
                "chart_gross_profit": [],
                "chart_cash_periods": [],
                "chart_cash_in": [],
                "chart_cash_out": [],
                "funnel_labels": [],
                "funnel_counts": [],
                "kpis": None,
            },
            status_code=400,
        )

    svc = AnalyticsService(db)

    try:
        kpis = await svc.kpis(f, t)
        revenue_series = await svc.revenue_series(f, t)
        gross_profit_series = await svc.gross_profit_series(f, t)
        cash_flow_series = await svc.cash_flow_series(f, t)
        funnel = await svc.inquiry_funnel(f, t)
        top_customers = await svc.top_customers(f, t, limit=5)
        top_materials = await svc.top_materials(f, t, limit=5)
        accuracy = await svc.estimate_accuracy(f, t)
        activity = await svc.recent_activity(limit=10)
    except AppError as exc:
        # Domain error in a report query — surface it, don't crash.
        log.warning("dashboard_analytics_failed", error=exc.message)
        return templates.render(
            request,
            "admin/dashboard.html",
            {
                "title": "Dashboard",
                "current_user": current,
                "error": f"Could not load analytics: {exc.message}",
                "period_preset": preset,
                "period_labels": PERIOD_LABELS,
                "period_presets": PERIOD_PRESETS,
                "period_from": f,
                "period_to": t,
                "interval_label": None,
                "funnel": None,
                "top_customers": [],
                "top_materials": [],
                "accuracy": None,
                "activity": [],
                "chart_periods": [],
                "chart_revenue": [],
                "chart_gross_profit": [],
                "chart_cash_periods": [],
                "chart_cash_in": [],
                "chart_cash_out": [],
                "funnel_labels": [],
                "funnel_counts": [],
                "kpis": None,
            },
            status_code=503,
        )

    # Shape the series for Chart.js
    rev_by_period = {p.period.isoformat(): p.value for p in revenue_series.points}
    gp_by_period = {p.period.isoformat(): p.value for p in gross_profit_series.points}
    all_periods = sorted(set(rev_by_period) | set(gp_by_period))

    chart_revenue = [rev_by_period.get(p, 0) for p in all_periods]
    chart_gp = [gp_by_period.get(p, 0) for p in all_periods]

    chart_cash_periods = [c.period.isoformat() for c in cash_flow_series]
    chart_cash_in = [c.inflow for c in cash_flow_series]
    chart_cash_out = [c.outflow for c in cash_flow_series]

    return templates.render(
        request,
        "admin/dashboard.html",
        {
            "title": "Dashboard",
            "current_user": current,
            "kpis": kpis,
            "period_preset": preset,
            "period_labels": PERIOD_LABELS,
            "period_presets": PERIOD_PRESETS,
            "period_from": f,
            "period_to": t,
            "interval_label": INTERVAL_LABELS.get(
                revenue_series.interval, revenue_series.interval
            ),
            "funnel": funnel,
            "top_customers": top_customers,
            "top_materials": top_materials,
            "accuracy": accuracy,
            "activity": activity,
            "chart_periods": all_periods,
            "chart_revenue": chart_revenue,
            "chart_gross_profit": chart_gp,
            "chart_cash_periods": chart_cash_periods,
            "chart_cash_in": chart_cash_in,
            "chart_cash_out": chart_cash_out,
            "funnel_labels": [s.label for s in funnel.stages],
            "funnel_counts": [s.count for s in funnel.stages],
        },
    )