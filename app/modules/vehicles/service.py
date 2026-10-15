from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import AuditAction
from app.core.exceptions import ConflictError, NotFoundError
from app.modules.audit.service import AuditService
from app.modules.auth.models import User
from app.modules.customers.repository import CustomerRepository
from app.modules.inquiries.models import Inquiry
from app.modules.vehicles.models import Vehicle
from app.modules.vehicles.repository import VehicleRepository
from app.modules.vehicles.schemas import VehicleCreate, VehicleUpdate

from sqlalchemy import func, select


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

        if payload.plate_number:
            existing = await self.repo.find_by_plate_for_customer(
                customer_id, payload.plate_number
            )
            if existing:
                raise ConflictError(
                    f"A vehicle with plate {payload.plate_number} already exists for this customer"
                )

        vehicle = Vehicle(
            customer_id=customer_id,
            plate_number=payload.plate_number,
            brand=payload.brand,
            model=payload.model,
            year=payload.year,
            color=payload.color,
            category=payload.category,
            vin=payload.vin,
            engine_number=payload.engine_number,
            notes=payload.notes,
            brand_id=payload.brand_id,
            model_id=payload.model_id,
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
        before = self._snapshot(vehicle)
        fields = payload.model_fields_set

        if "plate_number" in fields:
            new_plate = payload.plate_number
            if new_plate and new_plate != vehicle.plate_number:
                existing = await self.repo.find_by_plate_for_customer(
                    vehicle.customer_id, new_plate
                )
                if existing and existing.id != vehicle.id:
                    raise ConflictError(
                        f"A vehicle with plate {new_plate} already exists for this customer"
                    )
            vehicle.plate_number = new_plate

        for field in (
            "brand", "model", "year", "color", "category",
            "vin", "engine_number", "notes",
            "brand_id", "model_id",
        ):
            if field in fields:
                setattr(vehicle, field, getattr(payload, field))

        await self.db.flush()

        after = self._snapshot(vehicle)
        if before != after:
            await self.audit.log(
                action=AuditAction.UPDATE,
                table_name="vehicles",
                record_id=vehicle.id,
                user_id=actor.id,
                old_data=before,
                new_data=after,
            )
        return vehicle

    async def delete(self, vehicle_id: UUID, *, actor: User) -> None:
        """Hard delete — only allowed if the vehicle has no inquiries."""
        vehicle = await self._get_or_404(vehicle_id)

        inq_count = (
            await self.db.execute(
                select(func.count(Inquiry.id)).where(Inquiry.vehicle_id == vehicle_id)
            )
        ).scalar_one()
        if inq_count > 0:
            raise ConflictError(
                f"Cannot delete: {inq_count} inquiry(ies) reference this vehicle"
            )

        snapshot = self._snapshot(vehicle)
        await self.repo.delete(vehicle)

        await self.audit.log(
            action=AuditAction.DELETE,
            table_name="vehicles",
            record_id=vehicle_id,
            user_id=actor.id,
            old_data=snapshot,
        )

    async def _get_or_404(self, vid: UUID) -> Vehicle:
        vehicle = await self.repo.get(vid)
        if not vehicle:
            raise NotFoundError("Vehicle not found")
        return vehicle

    @staticmethod
    def _snapshot(v: Vehicle) -> dict:
        return {
            "brand": v.brand,
            "model": v.model,
            "plate_number": v.plate_number,
            "year": v.year,
            "color": v.color,
            "category": v.category,
            "vin": v.vin,
            "engine_number": v.engine_number,
            "brand_id": str(v.brand_id) if v.brand_id else None,
            "model_id": str(v.model_id) if v.model_id else None,
        }