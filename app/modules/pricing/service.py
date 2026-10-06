"""Business logic for pricing recommendations and rule management."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import AuditAction
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.modules.audit.service import AuditService
from app.modules.auth.models import User
from app.modules.pricing.constants import (
    DEFAULT_COMPLEXITY_FACTOR,
    DEFAULT_MIN_MARGIN_PCT,
    DEFAULT_TARGET_MARGIN_PCT,
    SETTING_DEFAULT_TARGET_MARGIN,
    SETTING_MIN_MARGIN,
    margin_health_label,
)
from app.modules.pricing.models import PricingRule, PricingSnapshot
from app.modules.pricing.repository import (
    PricingRuleRepository,
    PricingSnapshotRepository,
)
from app.modules.pricing.schemas import (
    MarginEvaluation,
    PricingRecommendation,
    PricingRuleCreate,
    PricingRuleUpdate,
    PricingSnapshotCreate,
)
from app.modules.settings.service import SettingsService


# ════════════════════════════════════════════════════════════════
# MATH HELPERS
# ════════════════════════════════════════════════════════════════

def price_from_margin(hpp: float, margin_pct: float) -> float:
    """Price such that (price - hpp) / price = margin_pct / 100."""
    m = margin_pct / 100.0
    if m >= 1:
        raise ValueError("margin_pct must be < 100")
    return hpp / (1 - m)


def price_from_markup(hpp: float, markup_pct: float) -> float:
    """Price such that (price - hpp) / hpp = markup_pct / 100."""
    return hpp * (1 + markup_pct / 100.0)


def margin_of(price: float, hpp: float) -> float:
    """(price - hpp) / price × 100. Returns 0 if price is 0."""
    if price <= 0:
        return 0.0
    return ((price - hpp) / price) * 100.0


def markup_of(price: float, hpp: float) -> float:
    """(price - hpp) / hpp × 100. Returns 0 if hpp is 0."""
    if hpp <= 0:
        return 0.0
    return ((price - hpp) / hpp) * 100.0


# ════════════════════════════════════════════════════════════════
# PRICING ENGINE
# ════════════════════════════════════════════════════════════════

@dataclass
class _ResolvedRule:
    rule_id: UUID | None
    rule_name: str | None
    target_margin_pct: float
    min_margin_pct: float
    complexity_factor: float
    min_price_floor: float | None


class PricingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.rules = PricingRuleRepository(db)
        self.snapshots = PricingSnapshotRepository(db)
        self.settings = SettingsService(db)
        self.audit = AuditService(db)

    # ── Rule resolution ────────────────────────────────

    async def _resolve_rule(
        self,
        *,
        service_interest: str | None,
        vehicle_category: str | None,
    ) -> _ResolvedRule:
        rule = await self.rules.find_matching(
            service_interest=service_interest,
            vehicle_category=vehicle_category,
        )
        if rule:
            return _ResolvedRule(
                rule_id=rule.id,
                rule_name=rule.name,
                target_margin_pct=float(rule.target_margin_pct),
                min_margin_pct=float(rule.min_margin_pct),
                complexity_factor=float(rule.complexity_factor),
                min_price_floor=float(rule.min_price_floor) if rule.min_price_floor else None,
            )

        # Fallback to settings-based defaults
        t = await self.settings.get_value(SETTING_DEFAULT_TARGET_MARGIN, str(DEFAULT_TARGET_MARGIN_PCT))
        m = await self.settings.get_value(SETTING_MIN_MARGIN, str(DEFAULT_MIN_MARGIN_PCT))
        try:
            target = float(t) if t else DEFAULT_TARGET_MARGIN_PCT
            minimum = float(m) if m else DEFAULT_MIN_MARGIN_PCT
        except (TypeError, ValueError):
            target, minimum = DEFAULT_TARGET_MARGIN_PCT, DEFAULT_MIN_MARGIN_PCT

        return _ResolvedRule(
            rule_id=None,
            rule_name=None,
            target_margin_pct=target,
            min_margin_pct=minimum,
            complexity_factor=DEFAULT_COMPLEXITY_FACTOR,
            min_price_floor=None,
        )

    # ── Recommendations ────────────────────────────────

    async def recommend(
        self,
        *,
        hpp: float,
        service_interest: str | None = None,
        vehicle_category: str | None = None,
    ) -> PricingRecommendation:
        """
        Given an HPP, return the recommended and minimum selling prices.
        """
        if hpp < 0:
            raise ValidationError("hpp must be >= 0")

        rule = await self._resolve_rule(
            service_interest=service_interest,
            vehicle_category=vehicle_category,
        )

        adjusted_hpp = hpp * rule.complexity_factor

        recommended = price_from_margin(adjusted_hpp, rule.target_margin_pct)
        minimum = price_from_margin(adjusted_hpp, rule.min_margin_pct)

        if rule.min_price_floor and minimum < rule.min_price_floor:
            minimum = rule.min_price_floor
        if rule.min_price_floor and recommended < rule.min_price_floor:
            recommended = rule.min_price_floor

        return PricingRecommendation(
            hpp=hpp,
            complexity_factor=rule.complexity_factor,
            adjusted_hpp=adjusted_hpp,
            target_margin_pct=rule.target_margin_pct,
            min_margin_pct=rule.min_margin_pct,
            recommended_price=round(recommended, 2),
            minimum_price=round(minimum, 2),
            recommended_markup_pct=round(markup_of(recommended, adjusted_hpp), 2),
            rule_id=rule.rule_id,
            rule_name=rule.rule_name,
        )

    async def evaluate(
        self,
        *,
        hpp: float,
        selling_price: float,
        service_interest: str | None = None,
        vehicle_category: str | None = None,
    ) -> MarginEvaluation:
        """
        Evaluate a specific selling price against the applicable rule.
        """
        rule = await self._resolve_rule(
            service_interest=service_interest,
            vehicle_category=vehicle_category,
        )

        adjusted_hpp = hpp * rule.complexity_factor
        recommended = price_from_margin(adjusted_hpp, rule.target_margin_pct)
        minimum = price_from_margin(adjusted_hpp, rule.min_margin_pct)

        if rule.min_price_floor and minimum < rule.min_price_floor:
            minimum = rule.min_price_floor
        if rule.min_price_floor and recommended < rule.min_price_floor:
            recommended = rule.min_price_floor

        gross_profit = selling_price - hpp
        margin_pct = margin_of(selling_price, hpp)
        markup_pct = markup_of(selling_price, hpp)

        return MarginEvaluation(
            hpp=hpp,
            selling_price=selling_price,
            gross_profit=round(gross_profit, 2),
            margin_pct=round(margin_pct, 2),
            markup_pct=round(markup_pct, 2),
            target_margin_pct=rule.target_margin_pct,
            min_margin_pct=rule.min_margin_pct,
            health=margin_health_label(
                actual_margin_pct=margin_pct,
                target_margin_pct=rule.target_margin_pct,
                min_margin_pct=rule.min_margin_pct,
            ),
            meets_minimum=selling_price >= minimum,
            meets_target=selling_price >= recommended,
            price_vs_target=round(selling_price - recommended, 2),
            price_vs_minimum=round(selling_price - minimum, 2),
        )

    # ── Rule CRUD ──────────────────────────────────────

    async def create_rule(self, payload: PricingRuleCreate, *, actor: User) -> PricingRule:
        rule = PricingRule(**payload.model_dump())
        await self.rules.add(rule)
        await self.audit.log(
            action=AuditAction.CREATE,
            table_name="pricing_rules",
            record_id=rule.id,
            user_id=actor.id,
            new_data={"name": rule.name, "target_margin_pct": float(rule.target_margin_pct)},
        )
        return rule

    async def update_rule(
        self, rid: UUID, payload: PricingRuleUpdate, *, actor: User
    ) -> PricingRule:
        rule = await self._get_rule_or_404(rid)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(rule, field, value)
        await self.db.flush()
        await self.audit.log(
            action=AuditAction.UPDATE,
            table_name="pricing_rules",
            record_id=rule.id,
            user_id=actor.id,
            new_data={"name": rule.name},
        )
        return rule

    async def delete_rule(self, rid: UUID, *, actor: User) -> None:
        rule = await self._get_rule_or_404(rid)
        rule.is_active = False
        await self.db.flush()
        await self.audit.log(
            action=AuditAction.DELETE,
            table_name="pricing_rules",
            record_id=rule.id,
            user_id=actor.id,
            old_data={"is_active": True},
            new_data={"is_active": False},
        )

    async def _get_rule_or_404(self, rid: UUID) -> PricingRule:
        rule = await self.rules.get(rid)
        if not rule:
            raise NotFoundError("Pricing rule not found")
        return rule

    # ── Snapshots ──────────────────────────────────────

    async def record_snapshot(
        self,
        payload: PricingSnapshotCreate,
        *,
        actor: User,
    ) -> PricingSnapshot:
        """
        Freeze a pricing decision for later analysis.
        Called whenever a quote is sent or a project's approved price is set.
        """
        rec = await self.recommend(
            hpp=payload.hpp_estimate,
            service_interest=payload.service_interest,
            vehicle_category=payload.vehicle_category,
        )

        actual_margin = None
        if payload.actual_quoted_price is not None:
            actual_margin = margin_of(payload.actual_quoted_price, payload.hpp_estimate)

        snap = PricingSnapshot(
            inquiry_id=payload.inquiry_id,
            project_id=payload.project_id,
            service_interest=payload.service_interest,
            vehicle_category=payload.vehicle_category,
            hpp_estimate=payload.hpp_estimate,
            rule_id=rec.rule_id,
            rule_name=rec.rule_name,
            target_margin_pct=rec.target_margin_pct,
            min_margin_pct=rec.min_margin_pct,
            complexity_factor=rec.complexity_factor,
            recommended_price=rec.recommended_price,
            minimum_price=rec.minimum_price,
            actual_quoted_price=payload.actual_quoted_price,
            actual_margin_pct=actual_margin,
            notes=payload.notes,
            created_by_id=actor.id,
        )
        await self.snapshots.add(snap)
        return snap