"""REST endpoints for the pricing engine."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.constants import PermissionCode
from app.core.deps import DbSession
from app.core.exceptions import NotFoundError
from app.core.pagination import Page, PageParams, paginate, page_params
from app.modules.auth.dependencies import CurrentUser, require_permission
from app.modules.pricing.repository import (
    PricingRuleRepository,
    PricingSnapshotRepository,
)
from app.modules.pricing.schemas import (
    MarginEvaluation,
    PricingPreviewRequest,
    PricingPreviewResponse,
    PricingRuleCreate,
    PricingRuleDetail,
    PricingRuleListItem,
    PricingRuleUpdate,
    PricingSnapshotCreate,
    PricingSnapshotOut,
)
from app.modules.pricing.service import PricingService

router = APIRouter(prefix="/pricing", tags=["pricing"])


# ════════════════════════════════════════════════════════════════
# ENGINE — recommend + evaluate
# ════════════════════════════════════════════════════════════════

@router.post("/preview", response_model=PricingPreviewResponse)
async def preview_pricing(
    payload: PricingPreviewRequest,
    db: DbSession,
    _=Depends(require_permission(PermissionCode.PRICING_READ)),
) -> PricingPreviewResponse:
    """
    Given an HPP and (optionally) a proposed price, return the
    recommendation and — if a proposed price is given — an evaluation.
    """
    svc = PricingService(db)
    rec = await svc.recommend(
        hpp=payload.hpp,
        service_interest=payload.service_interest,
        vehicle_category=payload.vehicle_category,
    )

    evaluation = None
    if payload.proposed_price is not None:
        evaluation = await svc.evaluate(
            hpp=payload.hpp,
            selling_price=payload.proposed_price,
            service_interest=payload.service_interest,
            vehicle_category=payload.vehicle_category,
        )

    return PricingPreviewResponse(recommendation=rec, evaluation=evaluation)


# ════════════════════════════════════════════════════════════════
# RULES
# ════════════════════════════════════════════════════════════════

@router.get("/rules", response_model=Page[PricingRuleListItem])
async def list_rules(
    db: DbSession,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, max_length=200),
    is_active: bool | None = Query(None),
    _=Depends(require_permission(PermissionCode.PRICING_READ)),
) -> Page[PricingRuleListItem]:
    stmt = PricingRuleRepository(db).query(q=q, is_active=is_active)
    rows, meta = await paginate(db, stmt, params)
    return Page[PricingRuleListItem](
        items=[PricingRuleListItem.model_validate(r) for r in rows], meta=meta
    )


@router.post("/rules", response_model=PricingRuleDetail, status_code=status.HTTP_201_CREATED)
async def create_rule(
    payload: PricingRuleCreate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.PRICING_WRITE)),
) -> PricingRuleDetail:
    rule = await PricingService(db).create_rule(payload, actor=actor)
    return PricingRuleDetail.model_validate(rule)


@router.get("/rules/{rule_id}", response_model=PricingRuleDetail)
async def get_rule(
    rule_id: UUID,
    db: DbSession,
    _=Depends(require_permission(PermissionCode.PRICING_READ)),
) -> PricingRuleDetail:
    rule = await PricingRuleRepository(db).get(rule_id)
    if not rule:
        raise NotFoundError("Pricing rule not found")
    detail = PricingRuleDetail.model_validate(rule)
    # Compute specificity for display
    spec = 0
    if rule.service_interest:
        spec += 2
    if rule.vehicle_category:
        spec += 1
    detail.specificity = spec
    return detail


@router.patch("/rules/{rule_id}", response_model=PricingRuleDetail)
async def update_rule(
    rule_id: UUID,
    payload: PricingRuleUpdate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.PRICING_WRITE)),
) -> PricingRuleDetail:
    rule = await PricingService(db).update_rule(rule_id, payload, actor=actor)
    return PricingRuleDetail.model_validate(rule)


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: UUID,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.PRICING_WRITE)),
) -> None:
    await PricingService(db).delete_rule(rule_id, actor=actor)


# ════════════════════════════════════════════════════════════════
# SNAPSHOTS
# ════════════════════════════════════════════════════════════════

@router.get("/snapshots", response_model=Page[PricingSnapshotOut])
async def list_snapshots(
    db: DbSession,
    params: PageParams = Depends(page_params),
    inquiry_id: UUID | None = Query(None),
    project_id: UUID | None = Query(None),
    _=Depends(require_permission(PermissionCode.PRICING_READ)),
) -> Page[PricingSnapshotOut]:
    stmt = PricingSnapshotRepository(db).query(inquiry_id=inquiry_id, project_id=project_id)
    rows, meta = await paginate(db, stmt, params)
    return Page[PricingSnapshotOut](
        items=[PricingSnapshotOut.model_validate(r) for r in rows], meta=meta
    )


@router.post(
    "/snapshots",
    response_model=PricingSnapshotOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_snapshot(
    payload: PricingSnapshotCreate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.PRICING_WRITE)),
) -> PricingSnapshotOut:
    snap = await PricingService(db).record_snapshot(payload, actor=actor)
    return PricingSnapshotOut.model_validate(snap)