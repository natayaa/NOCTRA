"""Admin web route for pricing analytics."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select

from app.core.constants import PermissionCode
from app.core.deps import DbSession
from app.core.pagination import PageParams, paginate, page_params
from app.modules.auth.dependencies import get_current_user
from app.modules.pricing.models import PricingSnapshot
from app.modules.pricing.repository import PricingSnapshotRepository
from app.web.admin._perms import read
from app.web.templates_env import templates

router = APIRouter(
    prefix="/admin/pricing-analytics",
    tags=["admin-pricing-analytics"],
)


@router.get("", response_class=HTMLResponse)
async def overview(
    request: Request,
    db: DbSession,
    params: PageParams = Depends(page_params),
    project_id: UUID | None = Query(None),
    _=read(PermissionCode.PRICING_READ),
    current=Depends(get_current_user),
) -> HTMLResponse:
    agg_stmt = select(
        func.count(PricingSnapshot.id).label("total"),
        func.avg(PricingSnapshot.actual_margin_pct).label("avg_actual_margin"),
        func.avg(PricingSnapshot.target_margin_pct).label("avg_target_margin"),
        func.avg(PricingSnapshot.recommended_price).label("avg_recommended"),
        func.avg(PricingSnapshot.actual_quoted_price).label("avg_quoted"),
    )
    row = (await db.execute(agg_stmt)).one()

    by_service_stmt = (
        select(
            PricingSnapshot.service_interest,
            func.count(PricingSnapshot.id).label("count"),
            func.avg(PricingSnapshot.actual_margin_pct).label("avg_margin"),
            func.avg(PricingSnapshot.target_margin_pct).label("avg_target"),
        )
        .where(PricingSnapshot.service_interest.is_not(None))
        .where(PricingSnapshot.actual_margin_pct.is_not(None))
        .group_by(PricingSnapshot.service_interest)
        .order_by(func.count(PricingSnapshot.id).desc())
    )
    by_service = (await db.execute(by_service_stmt)).all()

    stmt = PricingSnapshotRepository(db).query(project_id=project_id)
    rows, meta = await paginate(db, stmt, params)

    return templates.render(
        request,
        "admin/pricing_analytics/overview.html",
        {
            "title": "Pricing Analytics",
            "snapshots": rows,
            "page_meta": meta,
            "total": row.total or 0,
            "avg_actual_margin": float(row.avg_actual_margin or 0),
            "avg_target_margin": float(row.avg_target_margin or 0),
            "avg_recommended": float(row.avg_recommended or 0),
            "avg_quoted": float(row.avg_quoted or 0),
            "by_service": by_service,
        },
    )