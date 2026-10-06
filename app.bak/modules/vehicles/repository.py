from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.vehicles.models import Vehicle, VehicleBrand, VehicleModel


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
    ) -> Select:
        stmt = select(Vehicle).order_by(Vehicle.created_at.desc())
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
        if conds:
            stmt = stmt.where(and_(*conds))
        return stmt

    async def find_by_plate_for_customer(
        self, customer_id: UUID, plate: str
    ) -> Vehicle | None:
        stmt = select(Vehicle).where(
            and_(Vehicle.customer_id == customer_id, Vehicle.plate_number == plate)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def add(self, vehicle: Vehicle) -> Vehicle:
        self.db.add(vehicle)
        await self.db.flush()
        return vehicle

    async def list_brands(self) -> list[VehicleBrand]:
        stmt = select(VehicleBrand).order_by(VehicleBrand.name)
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_models(self, brand_id: UUID | None = None) -> list[VehicleModel]:
        stmt = select(VehicleModel).order_by(VehicleModel.name)
        if brand_id:
            stmt = stmt.where(VehicleModel.brand_id == brand_id)
        return list((await self.db.execute(stmt)).scalars().all())