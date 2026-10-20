"""Read/write helpers for the pricing module."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, and_, case, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.pricing.models import PricingRule, PricingSnapshot


class PricingRuleRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, rid: UUID) -> PricingRule | None:
        return await self.db.get(PricingRule, rid)

    def query(
        self,
        *,
        q: str | None = None,
        is_active: bool | None = None,
    ) -> Select:
        # Stable secondary sort on id prevents pagination drift.
        stmt = select(PricingRule).order_by(
            PricingRule.is_active.desc(),
            PricingRule.service_interest.asc().nulls_first(),
            PricingRule.vehicle_category.asc().nulls_first(),
            PricingRule.name.asc(),
            PricingRule.id.asc(),
        )
        conds = []
        if q:
            like = f"%{q.strip()}%"
            conds.append(
                or_(
                    PricingRule.name.ilike(like),
                    PricingRule.notes.ilike(like),
                )
            )
        if is_active is not None:
            conds.append(PricingRule.is_active == is_active)
        if conds:
            stmt = stmt.where(and_(*conds))
        return stmt

    async def find_matching(
        self,
        *,
        service_interest: str | None,
        vehicle_category: str | None,
    ) -> PricingRule | None:
        """
        Find the most specific active rule for the given criteria — done
        entirely in SQL. Specificity is computed via a CASE expression so
        the DB does the filtering AND ordering; we only pull one row.

        Match semantics:
          - Rule field NULL means "any value"
          - Rule field NOT NULL must exactly match the input
          - Most specific rule wins; ties broken by newest first
        """
        # Rule matches when its field is NULL (any) OR equals the input.
        # If the input is None, `field = NULL` becomes `field IS NULL` in
        # SQL — this correctly excludes non-NULL rules that would otherwise
        # silently match a None input.
        service_match = or_(
            PricingRule.service_interest.is_(None),
            PricingRule.service_interest == service_interest,
        )
        category_match = or_(
            PricingRule.vehicle_category.is_(None),
            PricingRule.vehicle_category == vehicle_category,
        )

        specificity = case(
            (
                and_(
                    PricingRule.service_interest.isnot(None),
                    PricingRule.vehicle_category.isnot(None),
                ),
                3,
            ),
            (PricingRule.service_interest.isnot(None), 2),
            (PricingRule.vehicle_category.isnot(None), 1),
            else_=0,
        ).label("specificity")

        stmt = (
            select(PricingRule, specificity)
            .where(PricingRule.is_active.is_(True))
            .where(service_match)
            .where(category_match)
            .order_by(
                specificity.desc(),
                PricingRule.created_at.desc(),
                PricingRule.id.desc(),
            )
            .limit(1)
        )
        row = (await self.db.execute(stmt)).first()
        return row[0] if row else None

    async def add(self, rule: PricingRule) -> PricingRule:
        self.db.add(rule)
        await self.db.flush()
        return rule


class PricingSnapshotRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, sid: UUID) -> PricingSnapshot | None:
        return await self.db.get(PricingSnapshot, sid)

    def query(
        self,
        *,
        inquiry_id: UUID | None = None,
        project_id: UUID | None = None,
    ) -> Select:
        # Stable secondary sort on id prevents pagination drift.
        stmt = select(PricingSnapshot).order_by(
            PricingSnapshot.created_at.desc(), PricingSnapshot.id.desc()
        )
        conds = []
        if inquiry_id is not None:
            conds.append(PricingSnapshot.inquiry_id == inquiry_id)
        if project_id is not None:
            conds.append(PricingSnapshot.project_id == project_id)
        if conds:
            stmt = stmt.where(and_(*conds))
        return stmt

    async def add(self, snap: PricingSnapshot) -> PricingSnapshot:
        self.db.add(snap)
        await self.db.flush()
        return snap