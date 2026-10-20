from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import AuditAction
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.modules.audit.service import AuditService
from app.modules.auth.models import User
from app.modules.customers.models import Customer
from app.modules.customers.repository import CustomerRepository
from app.modules.inquiries.models import Inquiry
from app.modules.vehicles.models import Vehicle
from app.modules.vehicles.repository import VehicleRepository
from app.modules.vehicles.schemas import VehicleCreate, VehicleUpdate


class VehicleService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = VehicleRepository(db)
        self.customers = CustomerRepository(db)
        self.audit = AuditService(db)

    # ── Create ────────────────────────────────────────

    async def create(
        self, customer_id: UUID, payload: VehicleCreate, *, actor: User
    ) -> Vehicle:
        # Lock the customer row so two concurrent creates for the same
        # customer serialize their plate-uniqueness check.
        locked = (
            await self.db.execute(
                select(Customer.id).where(Customer.id == customer_id).with_for_update()
            )
        ).scalar_one_or_none()
        if locked is None:
            raise NotFoundError("Customer not found")

        # Validate optional catalog references before touching the vehicle.
        brand_id, model_id = await self._resolve_catalog_refs(
            brand_id=payload.brand_id,
            model_id=payload.model_id,
        )

        if payload.plate_number:
            existing = await self.repo.find_by_plate_for_customer(
                customer_id, payload.plate_number
            )
            if existing:
                raise ConflictError(
                    f"A vehicle with plate {payload.plate_number} already "
                    f"exists for this customer"
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
            brand_id=brand_id,
            model_id=model_id,
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

    # ── Update ────────────────────────────────────────

    async def update(
        self, vehicle_id: UUID, payload: VehicleUpdate, *, actor: User
    ) -> Vehicle:
        # Row lock prevents two concurrent updates from racing the plate
        # uniqueness check.
        vehicle = await self._get_or_404_for_update(vehicle_id)
        before = self._snapshot(vehicle)
        fields = payload.model_fields_set

        # Catalog ref validation FIRST — prevents half-valid state.
        if "brand_id" in fields or "model_id" in fields:
            new_brand_id = (
                payload.brand_id if "brand_id" in fields else vehicle.brand_id
            )
            new_model_id = (
                payload.model_id if "model_id" in fields else vehicle.model_id
            )
            new_brand_id, new_model_id = await self._resolve_catalog_refs(
                brand_id=new_brand_id,
                model_id=new_model_id,
            )
            vehicle.brand_id = new_brand_id
            vehicle.model_id = new_model_id

        if "plate_number" in fields:
            new_plate = payload.plate_number
            if new_plate and new_plate != vehicle.plate_number:
                existing = await self.repo.find_by_plate_for_customer(
                    vehicle.customer_id, new_plate
                )
                if existing and existing.id != vehicle.id:
                    raise ConflictError(
                        f"A vehicle with plate {new_plate} already exists "
                        f"for this customer"
                    )
            vehicle.plate_number = new_plate

        # `brand` and `model` are NOT NULL — schema rejects explicit null.
        # Defence-in-depth skip: if somehow reached with None, skip rather
        # than crash with a 500.
        for field in (
            "brand", "model", "year", "color", "category",
            "vin", "engine_number", "notes",
        ):
            if field in fields:
                value = getattr(payload, field)
                if field in ("brand", "model") and value is None:
                    continue
                setattr(vehicle, field, value)

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

    # ── Delete ────────────────────────────────────────

    async def delete(self, vehicle_id: UUID, *, actor: User) -> None:
        """Hard delete — blocked when inquiries reference this vehicle."""
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

    # ── Helpers ───────────────────────────────────────

    async def _resolve_catalog_refs(
        self,
        *,
        brand_id: UUID | None,
        model_id: UUID | None,
    ) -> tuple[UUID | None, UUID | None]:
        """
        Validate brand/model FK references and normalize their relationship.

        - If `model_id` provided without `brand_id`, derive `brand_id` from model.
        - If both provided, verify `model.brand_id == brand_id`.
        - Each FK is verified to exist in the catalog.
        """
        if model_id is not None:
            model = await self.repo.get_model(model_id)
            if model is None:
                raise ValidationError(f"Vehicle model {model_id} not found")

            if brand_id is None:
                brand_id = model.brand_id
            elif brand_id != model.brand_id:
                raise ValidationError(
                    f"Vehicle model {model_id} does not belong to brand {brand_id}"
                )

        if brand_id is not None:
            brand = await self.repo.get_brand(brand_id)
            if brand is None:
                raise ValidationError(f"Vehicle brand {brand_id} not found")

        return brand_id, model_id

    async def _get_or_404(self, vid: UUID) -> Vehicle:
        vehicle = await self.repo.get(vid)
        if not vehicle:
            raise NotFoundError("Vehicle not found")
        return vehicle

    async def _get_or_404_for_update(self, vid: UUID) -> Vehicle:
        stmt = select(Vehicle).where(Vehicle.id == vid).with_for_update()
        vehicle = (await self.db.execute(stmt)).scalar_one_or_none()
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
            "notes": v.notes,
            "brand_id": str(v.brand_id) if v.brand_id else None,
            "model_id": str(v.model_id) if v.model_id else None,
        }