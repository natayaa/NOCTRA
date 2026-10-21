"""Admin web routes for pricing rules."""

from __future__ import annotations

from urllib.parse import quote, urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError as PydanticValidationError

from app.core.constants import PermissionCode
from app.core.deps import DbSession
from app.core.exceptions import AppError, NotFoundError
from app.core.pagination import PageParams, paginate, page_params
from app.modules.auth.dependencies import get_current_user
from app.modules.inquiries.constants import (
    SERVICE_INTEREST_LABELS,
    SERVICE_INTERESTS,
)
from app.modules.pricing.constants import rule_specificity
from app.modules.pricing.models import PricingRule
from app.modules.pricing.repository import PricingRuleRepository
from app.modules.pricing.schemas import PricingRuleCreate, PricingRuleUpdate
from app.modules.pricing.service import PricingService
from app.modules.vehicles.constants import (
    VEHICLE_CATEGORIES,
    VEHICLE_CATEGORY_LABELS,
)
from app.web.admin._perms import read, write
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/pricing-rules", tags=["admin-pricing-rules"])

_FORM_ERRORS = (AppError, PydanticValidationError, ValueError, KeyError)

# Example HPP used on the detail page — fixed for a stable reference.
EXAMPLE_HPP = 500_000


def _catalog() -> dict:
    return {
        "services": SERVICE_INTERESTS,
        "service_labels": SERVICE_INTEREST_LABELS,
        "vehicle_categories": VEHICLE_CATEGORIES,
        "vehicle_category_labels": VEHICLE_CATEGORY_LABELS,
    }


def _form_error(exc: Exception) -> str:
    return (getattr(exc, "message", None) or str(exc) or "Invalid input").strip()


def _clean_optional(form, key: str) -> str | None:
    v = form.get(key)
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() in ("none", "null", "undefined", "nil"):
        return None
    return s


def _safe_float(raw) -> float | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _compute_example(rule: PricingRule) -> dict:
    """
    Compute a reference-pricing example in Python so the template never
    does Decimal math or division. Handles:
      - min_price_floor override
      - target/min margin >= 100 (legacy bad data → fallback to HPP)
    """
    cf = float(rule.complexity_factor or 1)
    target = float(rule.target_margin_pct)
    min_margin = float(rule.min_margin_pct)
    floor = float(rule.min_price_floor) if rule.min_price_floor is not None else None

    adjusted_hpp = EXAMPLE_HPP * cf

    def _price_for_margin(margin_pct: float) -> float:
        if margin_pct >= 100:
            # Would divide by zero — treat as "no markup" fallback
            return adjusted_hpp
        return adjusted_hpp / (1 - margin_pct / 100.0)

    recommended = _price_for_margin(target)
    minimum = _price_for_margin(min_margin)

    if floor is not None and floor > 0:
        if minimum < floor:
            minimum = floor
        if recommended < floor:
            recommended = floor

    return {
        "hpp": EXAMPLE_HPP,
        "adjusted_hpp": round(adjusted_hpp, 2),
        "minimum_price": round(minimum, 2),
        "recommended_price": round(recommended, 2),
        "floor_applied": floor is not None and floor > 0 and minimum >= floor,
    }


# ════════════════════════════════════════════════════════════════
# LIST
# ════════════════════════════════════════════════════════════════

@router.get("", response_class=HTMLResponse)
async def list_view(
    request: Request,
    db: DbSession,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, max_length=200),
    is_active: bool | None = Query(None),
    _=read(PermissionCode.PRICING_READ),
    current=Depends(get_current_user),
) -> HTMLResponse:
    repo = PricingRuleRepository(db)
    stmt = repo.query(q=q, is_active=is_active)
    rows, meta = await paginate(db, stmt, params)

    # Precompute specificity for each row — template can display it.
    specificity_map = {
        r.id: rule_specificity(r.service_interest, r.vehicle_category)
        for r in rows
    }

    def qs(page: int | None = None, **overrides) -> str:
        base = {
            "q": q or "",
            "is_active": "" if is_active is None else ("true" if is_active else "false"),
        }
        if page is not None:
            base["page"] = str(page)
        base.update({k: ("" if v is None else str(v)) for k, v in overrides.items()})
        return "?" + urlencode({k: v for k, v in base.items() if v})

    return templates.render(
        request,
        "admin/pricing_rules/list.html",
        {
            "title": "Pricing Rules",
            "rules": rows,
            "specificity_map": specificity_map,
            "page_meta": meta,
            "q": q or "",
            "is_active_filter": is_active,
            "qs": qs,
            **_catalog(),
        },
    )


# ════════════════════════════════════════════════════════════════
# NEW / CREATE
# ════════════════════════════════════════════════════════════════

@router.get("/new", response_class=HTMLResponse)
async def new_view(
    request: Request,
    _=write(PermissionCode.PRICING_WRITE),
    current=Depends(get_current_user),
) -> HTMLResponse:
    return templates.render(
        request,
        "admin/pricing_rules/form.html",
        {"title": "New Pricing Rule", "mode": "create", "rule": None, **_catalog()},
    )


@router.post("")
async def create_submit(
    request: Request,
    db: DbSession,
    _=write(PermissionCode.PRICING_WRITE),
    current=Depends(get_current_user),
):
    form = await request.form()

    def _render_error(msg: str, status_code: int = 400):
        return templates.render(
            request,
            "admin/pricing_rules/form.html",
            {
                "title": "New Pricing Rule",
                "mode": "create",
                "rule": None,
                "error": msg,
                "form_values": dict(form),
                **_catalog(),
            },
            status_code=status_code,
        )

    try:
        payload = PricingRuleCreate(
            name=(form.get("name") or "").strip(),
            notes=_clean_optional(form, "notes"),
            service_interest=_clean_optional(form, "service_interest"),
            vehicle_category=_clean_optional(form, "vehicle_category"),
            target_margin_pct=_safe_float(form.get("target_margin_pct")) or 50.0,
            min_margin_pct=_safe_float(form.get("min_margin_pct")) or 30.0,
            complexity_factor=_safe_float(form.get("complexity_factor")) or 1.0,
            min_price_floor=_safe_float(form.get("min_price_floor")),
        )
        rule = await PricingService(db).create_rule(payload, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return _render_error(_form_error(exc), getattr(exc, "status_code", 400))

    return RedirectResponse(url=f"/admin/pricing-rules/{rule.id}", status_code=303)


# ════════════════════════════════════════════════════════════════
# DETAIL
# ════════════════════════════════════════════════════════════════

@router.get("/{rule_id}", response_class=HTMLResponse)
async def detail_view(
    rule_id: UUID,
    request: Request,
    db: DbSession,
    error: str | None = Query(None),
    _=read(PermissionCode.PRICING_READ),
    current=Depends(get_current_user),
) -> HTMLResponse:
    rule = await PricingRuleRepository(db).get(rule_id)
    if not rule:
        raise NotFoundError("Pricing rule not found")

    spec = rule_specificity(rule.service_interest, rule.vehicle_category)
    example = _compute_example(rule)

    return templates.render(
        request,
        "admin/pricing_rules/detail.html",
        {
            "title": rule.name,
            "rule": rule,
            "specificity": spec,
            "example": example,
            "error": error,
            **_catalog(),
        },
    )


# ════════════════════════════════════════════════════════════════
# EDIT / UPDATE
# ════════════════════════════════════════════════════════════════

@router.get("/{rule_id}/edit", response_class=HTMLResponse)
async def edit_view(
    rule_id: UUID,
    request: Request,
    db: DbSession,
    error: str | None = Query(None),
    _=write(PermissionCode.PRICING_WRITE),
    current=Depends(get_current_user),
) -> HTMLResponse:
    rule = await PricingRuleRepository(db).get(rule_id)
    if not rule:
        raise NotFoundError("Pricing rule not found")
    return templates.render(
        request,
        "admin/pricing_rules/form.html",
        {
            "title": f"Edit {rule.name}",
            "mode": "edit",
            "rule": rule,
            "error": error,
            **_catalog(),
        },
    )


@router.post("/{rule_id}")
async def update_submit(
    rule_id: UUID,
    request: Request,
    db: DbSession,
    _=write(PermissionCode.PRICING_WRITE),
    current=Depends(get_current_user),
):
    form = await request.form()

    try:
        payload = PricingRuleUpdate(
            name=(form.get("name") or "").strip() or None,
            notes=_clean_optional(form, "notes"),
            service_interest=_clean_optional(form, "service_interest"),
            vehicle_category=_clean_optional(form, "vehicle_category"),
            target_margin_pct=_safe_float(form.get("target_margin_pct")),
            min_margin_pct=_safe_float(form.get("min_margin_pct")),
            complexity_factor=_safe_float(form.get("complexity_factor")),
            min_price_floor=_safe_float(form.get("min_price_floor")),
            is_active=(
                form.get("is_active") == "true"
                if form.get("_has_is_active") == "1"
                else None
            ),
        )
        await PricingService(db).update_rule(rule_id, payload, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return RedirectResponse(
            url=f"/admin/pricing-rules/{rule_id}?error="
                f"{quote(_form_error(exc), safe='')}",
            status_code=303,
        )

    return RedirectResponse(url=f"/admin/pricing-rules/{rule_id}", status_code=303)


# ════════════════════════════════════════════════════════════════
# DEACTIVATE
# ════════════════════════════════════════════════════════════════

@router.post("/{rule_id}/deactivate")
async def deactivate_submit(
    rule_id: UUID,
    request: Request,
    db: DbSession,
    _=write(PermissionCode.PRICING_WRITE),
    current=Depends(get_current_user),
):
    try:
        await PricingService(db).delete_rule(rule_id, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return RedirectResponse(
            url=f"/admin/pricing-rules/{rule_id}?error="
                f"{quote(_form_error(exc), safe='')}",
            status_code=303,
        )
    return RedirectResponse(url=f"/admin/pricing-rules/{rule_id}", status_code=303)