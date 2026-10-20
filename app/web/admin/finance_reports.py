"""Admin web routes for finance reports."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse

from app.core.constants import PermissionCode
from app.core.deps import DbSession
from app.core.exceptions import ValidationError
from app.modules.auth.dependencies import get_current_user
from app.modules.finance.constants import today_local
from app.modules.finance.service import FinanceReportService
from app.web.admin._perms import read
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/reports", tags=["admin-reports"])


def _default_period() -> tuple[date, date]:
    """Current month by default, in the app's local timezone."""
    today = today_local()
    start = today.replace(day=1)
    # End = last day of current month
    next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    end = next_month - timedelta(days=1)
    return start, end


def _validate_range(f: date, t: date) -> None:
    if f > t:
        raise ValidationError("from_date must be <= to_date")


@router.get("/pnl", response_class=HTMLResponse)
async def pnl(
    request: Request,
    db: DbSession,
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    _=read(PermissionCode.FINANCE_REPORTS),
    current=Depends(get_current_user),
) -> HTMLResponse:
    default_start, default_end = _default_period()
    f = from_date or default_start
    t = to_date or default_end

    try:
        _validate_range(f, t)
        report = await FinanceReportService(db).pnl(from_date=f, to_date=t)
        cash_flow = await FinanceReportService(db).cash_flow(from_date=f, to_date=t)
    except ValidationError as exc:
        return templates.render(
            request,
            "admin/reports/pnl.html",
            {
                "title": "Profit & Loss",
                "error": exc.message,
                "from_date": f.isoformat(),
                "to_date": t.isoformat(),
                "report": None,
                "cash_flow": None,
            },
            status_code=422,
        )

    return templates.render(
        request,
        "admin/reports/pnl.html",
        {
            "title": "Profit & Loss",
            "report": report,
            "cash_flow": cash_flow,
            "from_date": f.isoformat(),
            "to_date": t.isoformat(),
        },
    )


@router.get("/receivables", response_class=HTMLResponse)
async def receivables(
    request: Request,
    db: DbSession,
    _=read(PermissionCode.FINANCE_REPORTS),
    current=Depends(get_current_user),
) -> HTMLResponse:
    summary = await FinanceReportService(db).receivables()
    return templates.render(
        request,
        "admin/reports/receivables.html",
        {"title": "Receivables", "summary": summary},
    )


@router.get("/payables", response_class=HTMLResponse)
async def payables(
    request: Request,
    db: DbSession,
    _=read(PermissionCode.FINANCE_REPORTS),
    current=Depends(get_current_user),
) -> HTMLResponse:
    summary = await FinanceReportService(db).payables()
    return templates.render(
        request,
        "admin/reports/payables.html",
        {"title": "Payables", "summary": summary},
    )