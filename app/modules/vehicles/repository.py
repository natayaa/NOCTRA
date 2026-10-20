from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vehicles.models import Vehicle, VehicleBrand, VehicleModel


class VehicleRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, vid: UUID) -> Vehicle | None:
        return await self.db.get(Vehicle, vid)

    def query(
        self,
        *,
        customer_id: UUID | None = None,
        q: str | None = None,
        category: str | None = None,
        brand: str | None = None,
        sort: str = "created_desc",
    ) -> Select:
        stmt = select(Vehicle)
        conds = []
        if customer_id:
            conds.append(Vehicle.customer_id == customer_id)
        if q:
            like = f"%{q.strip()}%"
            conds.append(
                or_(
                    Vehicle.brand.ilike(like),
                    Vehicle.model.ilike(like),
                    Vehicle.plate_number.ilike(like),
                    Vehicle.vin.ilike(like),
                )
            )
        if category:
            conds.append(Vehicle.category == category)
        if brand:
            conds.append(Vehicle.brand == brand)
        if conds:
            stmt = stmt.where(and_(*conds))

        # Stable secondary sort on id prevents pagination drift.
        if sort == "created_asc":
            stmt = stmt.order_by(Vehicle.created_at.asc(), Vehicle.id.asc())
        elif sort == "brand_asc":
            stmt = stmt.order_by(
                Vehicle.brand.asc(), Vehicle.model.asc(), Vehicle.id.asc()
            )
        elif sort == "year_desc":
            stmt = stmt.order_by(
                Vehicle.year.desc().nulls_last(), Vehicle.id.asc()
            )
        elif sort == "plate_asc":
            stmt = stmt.order_by(
                Vehicle.plate_number.asc().nulls_last(), Vehicle.id.asc()
            )
        else:  # created_desc
            stmt = stmt.order_by(Vehicle.created_at.desc(), Vehicle.id.asc())

        return stmt

    async def find_by_plate_for_customer(
        self, customer_id: UUID, plate: str
    ) -> Vehicle | None:
        # `limit(1)` + deterministic order prevents MultipleResultsFound
        # from surfacing as a 500 when duplicate plates already exist in
        # the DB (pre-constraint legacy data).
        stmt = (
            select(Vehicle)
            .where(
                and_(
                    Vehicle.customer_id == customer_id,
                    Vehicle.plate_number == plate,
                )
            )
            .order_by(Vehicle.created_at.asc())
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_brand(self, brand_id: UUID) -> VehicleBrand | None:
        return await self.db.get(VehicleBrand, brand_id)

    async def get_model(self, model_id: UUID) -> VehicleModel | None:
        return await self.db.get(VehicleModel, model_id)

    async def stats(
        self, *, customer_id: UUID | None = None
    ) -> dict[str, int]:
        base = select(Vehicle.category, func.count(Vehicle.id)).group_by(Vehicle.category)
        if customer_id:
            base = base.where(Vehicle.customer_id == customer_id)
        rows = (await self.db.execute(base)).all()
        by_cat = {(c or "UNCATEGORIZED"): n for c, n in rows}

        total_stmt = select(func.count(Vehicle.id))
        if customer_id:
            total_stmt = total_stmt.where(Vehicle.customer_id == customer_id)
        total = (await self.db.execute(total_stmt)).scalar_one()

        return {
            "total": total,
            **{f"cat_{k}": v for k, v in by_cat.items()},
        }

    async def list_distinct_brands(
        self, *, customer_id: UUID | None = None
    ) -> list[str]:
        stmt = select(Vehicle.brand).distinct().order_by(Vehicle.brand)
        if customer_id:
            stmt = stmt.where(Vehicle.customer_id == customer_id)
        return [b for (b,) in (await self.db.execute(stmt)).all() if b]

    async def add(self, vehicle: Vehicle) -> Vehicle:
        self.db.add(vehicle)
        await self.db.flush()
        return vehicle

    async def delete(self, vehicle: Vehicle) -> None:
        await self.db.delete(vehicle)
        await self.db.flush()

    # ── Catalog ───────────────────────────────────────
    async def list_brands(self) -> list[VehicleBrand]:
        stmt = select(VehicleBrand).order_by(
            VehicleBrand.name.asc(), VehicleBrand.id.asc()
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_models(self, brand_id: UUID | None = None) -> list[VehicleModel]:
        stmt = select(VehicleModel).order_by(
            VehicleModel.name.asc(), VehicleModel.id.asc()
        )
        if brand_id:
            stmt = stmt.where(VehicleModel.brand_id == brand_id)
        return list((await self.db.execute(stmt)).scalars().all())