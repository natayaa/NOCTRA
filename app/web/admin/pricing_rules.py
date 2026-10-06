"""Admin web routes for pricing rules."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.deps import DbSession
from app.core.exceptions import AppError, NotFoundError
from app.core.pagination import PageParams, paginate, page_params
from app.modules.auth.dependencies import get_current_user
from app.modules.inquiries.constants import (
    SERVICE_INTEREST_LABELS,
    SERVICE_INTERESTS,
)
from app.modules.pricing.repository import PricingRuleRepository
from app.modules.pricing.schemas import PricingRuleCreate, PricingRuleUpdate
from app.modules.pricing.service import PricingService
from app.modules.vehicles.constants import VEHICLE_CATEGORIES
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/pricing-rules", tags=["admin-pricing-rules"])


def _catalog() -> dict:
    return {
        "services": SERVICE_INTERESTS,
        "service_labels": SERVICE_INTEREST_LABELS,
        "vehicle_categories": VEHICLE_CATEGORIES,
    }


@router.get("", response_class=HTMLResponse)
async def list_view(
    request: Request,
    db: DbSession,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, max_length=200),
    current=Depends(get_current_user),
) -> HTMLResponse:
    stmt = PricingRuleRepository(db).query(q=q)
    rows, meta = await paginate(db, stmt, params)
    return templates.render(
        request,
        "admin/pricing_rules/list.html",
        {
            "title": "Pricing Rules",
            "rules": rows,
            "page_meta": meta,
            "q": q or "",
            **_catalog(),
        },
    )


@router.get("/new", response_class=HTMLResponse)
async def new_view(request: Request, current=Depends(get_current_user)) -> HTMLResponse:
    return templates.render(
        request,
        "admin/pricing_rules/form.html",
        {"title": "New Pricing Rule", "mode": "create", "rule": None, **_catalog()},
    )


@router.post("")
async def create_submit(request: Request, db: DbSession, current=Depends(get_current_user)):
    form = await request.form()

    def clean(k):
        v = form.get(k)
        if v is None:
            return None
        s = str(v).strip()
        if not s or s.lower() in ("none", "null", "undefined", "nil"):
            return None
        return s

    payload = PricingRuleCreate(
        name=(form.get("name") or "").strip(),
        notes=clean("notes"),
        service_interest=clean("service_interest"),
        vehicle_category=clean("vehicle_category"),
        target_margin_pct=float(form.get("target_margin_pct") or 50),
        min_margin_pct=float(form.get("min_margin_pct") or 30),
        complexity_factor=float(form.get("complexity_factor") or 1.0),
        min_price_floor=(float(form["min_price_floor"]) if form.get("min_price_floor") else None),
    )
    try:
        rule = await PricingService(db).create_rule(payload, actor=current)
    except AppError as exc:
        await db.rollback()
        return templates.render(
            request,
            "admin/pricing_rules/form.html",
            {
                "title": "New Pricing Rule",
                "mode": "create",
                "rule": None,
                "error": exc.message,
                "form_values": dict(form),
                **_catalog(),
            },
            status_code=exc.status_code,
        )
    await db.commit()
    return RedirectResponse(url=f"/admin/pricing-rules/{rule.id}", status_code=303)


@router.get("/{rule_id}", response_class=HTMLResponse)
async def detail_view(
    rule_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
) -> HTMLResponse:
    rule = await PricingRuleRepository(db).get(rule_id)
    if not rule:
        raise NotFoundError("Pricing rule not found")

    spec = 0
    if rule.service_interest:
        spec += 2
    if rule.vehicle_category:
        spec += 1

    return templates.render(
        request,
        "admin/pricing_rules/detail.html",
        {"title": rule.name, "rule": rule, "specificity": spec, **_catalog()},
    )


@router.get("/{rule_id}/edit", response_class=HTMLResponse)
async def edit_view(
    rule_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
) -> HTMLResponse:
    rule = await PricingRuleRepository(db).get(rule_id)
    if not rule:
        raise NotFoundError("Pricing rule not found")
    return templates.render(
        request,
        "admin/pricing_rules/form.html",
        {"title": f"Edit {rule.name}", "mode": "edit", "rule": rule, **_catalog()},
    )


@router.post("/{rule_id}")
async def update_submit(
    rule_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
):
    form = await request.form()

    def clean(k):
        v = form.get(k)
        if v is None:
            return None
        s = str(v).strip()
        if not s or s.lower() in ("none", "null", "undefined", "nil"):
            return None
        return s

    payload = PricingRuleUpdate(
        name=(form.get("name") or "").strip() or None,
        notes=clean("notes"),
        service_interest=clean("service_interest"),
        vehicle_category=clean("vehicle_category"),
        target_margin_pct=(float(form["target_margin_pct"]) if form.get("target_margin_pct") else None),
        min_margin_pct=(float(form["min_margin_pct"]) if form.get("min_margin_pct") else None),
        complexity_factor=(float(form["complexity_factor"]) if form.get("complexity_factor") else None),
        min_price_floor=(float(form["min_price_floor"]) if form.get("min_price_floor") else None),
        is_active=form.get("is_active") == "true",
    )
    try:
        await PricingService(db).update_rule(rule_id, payload, actor=current)
        await db.commit()
    except AppError as exc:
        await db.rollback()
        return RedirectResponse(
            url=f"/admin/pricing-rules/{rule_id}?error={exc.message}", status_code=303
        )
    return RedirectResponse(url=f"/admin/pricing-rules/{rule_id}", status_code=303)


@router.post("/{rule_id}/deactivate")
async def deactivate_submit(
    rule_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
):
    await PricingService(db).delete_rule(rule_id, actor=current)
    await db.commit()
    return RedirectResponse(url=f"/admin/pricing-rules/{rule_id}", status_code=303)