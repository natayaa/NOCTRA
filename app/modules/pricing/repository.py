"""Read/write helpers for the pricing module."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, and_, or_, select
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
        stmt = select(PricingRule).order_by(
            PricingRule.is_active.desc(),
            PricingRule.service_interest,
            PricingRule.vehicle_category,
            PricingRule.name,
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
        Find the most specific active rule for the given criteria.

        Specificity:
            3 — service + category match
            2 — service matches, category null (rule is service-wide)
            1 — category matches, service null (rule is category-wide)
            0 — both null (global default)

        Within the same specificity, the newest rule wins.
        """
        candidates = (
            await self.db.execute(
                select(PricingRule).where(PricingRule.is_active.is_(True))
            )
        ).scalars().all()

        best: tuple[int, PricingRule] | None = None
        for rule in candidates:
            matches = True
            specificity = 0

            if rule.service_interest is not None:
                if rule.service_interest != service_interest:
                    matches = False
                else:
                    specificity += 2
            if rule.vehicle_category is not None:
                if rule.vehicle_category != vehicle_category:
                    matches = False
                else:
                    specificity += 1

            if not matches:
                continue

            if best is None or specificity > best[0]:
                best = (specificity, rule)
            elif specificity == best[0]:
                # Tie: prefer newer
                if rule.created_at > best[1].created_at:
                    best = (specificity, rule)

        return best[1] if best else None

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
        stmt = select(PricingSnapshot).order_by(PricingSnapshot.created_at.desc())
        conds = []
        if inquiry_id:
            conds.append(PricingSnapshot.inquiry_id == inquiry_id)
        if project_id:
            conds.append(PricingSnapshot.project_id == project_id)
        if conds:
            stmt = stmt.where(and_(*conds))
        return stmt

    async def add(self, snap: PricingSnapshot) -> PricingSnapshot:
        self.db.add(snap)
        await self.db.flush()
        return snap