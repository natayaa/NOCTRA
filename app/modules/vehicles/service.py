from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import AuditAction
from app.core.exceptions import NotFoundError
from app.modules.audit.service import AuditService
from app.modules.auth.models import User
from app.modules.customers.repository import CustomerRepository
from app.modules.vehicles.models import Vehicle
from app.modules.vehicles.repository import VehicleRepository
from app.modules.vehicles.schemas import VehicleCreate, VehicleUpdate


class VehicleService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = VehicleRepository(db)
        self.customers = CustomerRepository(db)
        self.audit = AuditService(db)

    async def create(
        self, customer_id: UUID, payload: VehicleCreate, *, actor: User
    ) -> Vehicle:
        customer = await self.customers.get(customer_id)
        if not customer:
            raise NotFoundError("Customer not found")

        vehicle = Vehicle(
            customer_id=customer_id,
            plate_number=payload.plate_number,
            brand=payload.brand.strip(),
            model=payload.model.strip(),
            year=payload.year,
            color=payload.color,
            category=payload.category,
            vin=payload.vin,
            engine_number=payload.engine_number,
            notes=payload.notes,
        )
        await self.repo.add(vehicle)

        await self.audit.log(
            action=AuditAction.CREATE,
            table_name="vehicles",
            record_id=vehicle.id,
            user_id=actor.id,
            new_data={
                "customer_id": str(customer_id),
                "brand": vehicle.brand,
                "model": vehicle.model,
                "plate_number": vehicle.plate_number,
            },
        )
        return vehicle

    async def update(
        self, vehicle_id: UUID, payload: VehicleUpdate, *, actor: User
    ) -> Vehicle:
        vehicle = await self._get_or_404(vehicle_id)
        before = {
            "brand": vehicle.brand,
            "model": vehicle.model,
            "plate_number": vehicle.plate_number,
            "category": vehicle.category,
        }

        for field in (
            "plate_number", "brand", "model", "year",
            "color", "category", "vin", "engine_number", "notes",
        ):
            value = getattr(payload, field, None)
            if value is not None:
                setattr(vehicle, field, value)

        await self.db.flush()

        await self.audit.log(
            action=AuditAction.UPDATE,
            table_name="vehicles",
            record_id=vehicle.id,
            user_id=actor.id,
            old_data=before,
            new_data={
                "brand": vehicle.brand,
                "model": vehicle.model,
                "plate_number": vehicle.plate_number,
                "category": vehicle.category,
            },
        )
        return vehicle

    async def _get_or_404(self, vid: UUID) -> Vehicle:
        vehicle = await self.repo.get(vid)
        if not vehicle:
            raise NotFoundError("Vehicle not found")
        return vehicle