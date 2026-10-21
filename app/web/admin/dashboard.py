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
from app.modules.analytics.schemas import (
    EstimateAccuracyStats,
    InquiryFunnel,
    KpiSet,
)
from app.modules.analytics.service import AnalyticsService
from app.modules.auth.dependencies import get_current_user
from app.web.admin._perms import read
from app.web.templates_env import templates

router = APIRouter(prefix="/admin", tags=["admin-dashboard"])


def _empty_analytics(
    *,
    from_date: date | None,
    to_date: date | None,
) -> dict:
    """
    Safe fallback context when analytics fail.

    Every top-level field the template accesses is provided as an EMPTY
    but VALID object so the template never crashes. Previously the error
    path passed `None` for kpis/funnel/accuracy, and the template did
    `{% for card in kpis.cards %}` → AttributeError → 500.
    """
    # Fallback date so KpiSet(period_from=..., period_to=...) has real values
    from datetime import date as _date
    fallback = _date.today()
    pf = from_date or fallback
    pt = to_date or fallback

    return {
        "kpis": KpiSet(period_from=pf, period_to=pt, cards=[]),
        "funnel": InquiryFunnel(total=0, stages=[]),
        "top_customers": [],
        "top_materials": [],
        "accuracy": EstimateAccuracyStats(
            project_count=0,
            avg_variance_pct=0.0,
            median_variance_pct=0.0,
            worst_overrun_pct=0.0,
            best_case_pct=0.0,
            avg_estimated_hpp=0.0,
            avg_actual_hpp=0.0,
        ),
        "activity": [],
        "chart_periods": [],
        "chart_revenue": [],
        "chart_gross_profit": [],
        "chart_cash_periods": [],
        "chart_cash_in": [],
        "chart_cash_out": [],
        "funnel_labels": [],
        "funnel_counts": [],
    }


def _render_error(
    request: Request,
    current,
    *,
    error_message: str,
    preset: str,
    from_date: date | None,
    to_date: date | None,
    status_code: int,
) -> HTMLResponse:
    """
    Single error-render path used by both validation and analytics errors.
    Avoids duplicating the ~20-line context dict.
    """
    ctx = {
        "title": "Dashboard",
        "current_user": current,
        "error": error_message,
        "period_preset": preset,
        "period_labels": PERIOD_LABELS,
        "period_presets": PERIOD_PRESETS,
        "period_from": from_date,
        "period_to": to_date,
        "interval_label": None,
        **_empty_analytics(from_date=from_date, to_date=to_date),
    }
    return templates.render(
        request, "admin/dashboard.html", ctx, status_code=status_code,
    )


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
    # ── Validate period ─────────────────────────────────
    try:
        f, t = resolve_period(preset, from_date=from_date, to_date=to_date)
    except ValueError as exc:
        return _render_error(
            request,
            current,
            error_message=str(exc),
            preset="month",
            from_date=None,
            to_date=None,
            status_code=400,
        )

    svc = AnalyticsService(db)

    # ── Load analytics — any failure degrades gracefully ──
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
        # Domain error — log at warning, return 503 (not our bug)
        log.warning(
            "dashboard_analytics_failed",
            error=exc.message,
            code=exc.code,
            period_from=f.isoformat(),
            period_to=t.isoformat(),
        )
        return _render_error(
            request,
            current,
            error_message=f"Could not load analytics: {exc.message}",
            preset=preset,
            from_date=f,
            to_date=t,
            status_code=503,
        )
    except Exception as exc:
        # Unexpected — log with traceback, return 503
        log.exception(
            "dashboard_unexpected_error",
            error=str(exc),
            error_type=type(exc).__name__,
        )
        return _render_error(
            request,
            current,
            error_message="Could not load analytics. Please try again later.",
            preset=preset,
            from_date=f,
            to_date=t,
            status_code=503,
        )

    # ── Shape series for Chart.js ──────────────────────
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