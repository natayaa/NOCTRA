"""Orchestrator for public inquiry intake.

Combines customer, vehicle, and inquiry creation into a single
transaction. Finds existing records where possible to avoid duplicates.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import AuditAction
from app.core.exceptions import ValidationError
from app.core.upload import save_inquiry_photos
from app.modules.audit.service import AuditService
from app.modules.customers.constants import CustomerSource, CustomerStatus
from app.modules.customers.models import Customer
from app.modules.customers.repository import CustomerRepository
from app.modules.inquiries.constants import InquirySource, InquiryStatus
from app.modules.inquiries.models import Inquiry, InquiryPhoto
from app.modules.inquiries.repository import InquiryRepository
from app.modules.vehicles.models import Vehicle
from app.modules.vehicles.repository import VehicleRepository


@dataclass
class PublicIntakePayload:
    # Contact
    name: str
    phone: str
    email: str | None = None

    # Vehicle
    vehicle_brand: str | None = None
    vehicle_model: str | None = None
    vehicle_year: int | None = None
    vehicle_plate: str | None = None
    vehicle_category: str | None = None

    # Request
    service_interest: str | None = None
    description: str = ""
    color_preference: str | None = None
    color_family: str | None = None
    finish_preference: str | None = None
    has_custom_graphics: bool = False

    # Preferences (JSONB extras from the form)
    preferences: dict | None = None

    # Logistics
    budget_range: str | None = None
    desired_date: date | None = None


class PublicIntakeService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.customers = CustomerRepository(db)
        self.vehicles = VehicleRepository(db)
        self.inquiries = InquiryRepository(db)
        self.audit = AuditService(db)

    async def submit(
        self,
        payload: PublicIntakePayload,
        photos: list[UploadFile] | None = None,
    ) -> Inquiry:
        """
        Create the customer (find-or-create), vehicle (find-or-create),
        inquiry (always new), and photos (if any) in one transaction.
        """
        if not payload.name.strip():
            raise ValidationError("Name is required")
        if not payload.phone.strip():
            raise ValidationError("Phone is required")
        if len(payload.description.strip()) < 20:
            raise ValidationError("Description must be at least 20 characters")

        # ── Find or create customer ─────────────────────
        customer, customer_created = await self._find_or_create_customer(
            name=payload.name.strip(),
            phone=payload.phone.strip(),
            email=(payload.email or "").strip() or None,
        )

        # ── Find or create vehicle (if we have enough info) ──
        vehicle: Vehicle | None = None
        if payload.vehicle_brand and payload.vehicle_model:
            vehicle = await self._find_or_create_vehicle(
                customer_id=customer.id,
                brand=payload.vehicle_brand.strip(),
                model=payload.vehicle_model.strip(),
                year=payload.vehicle_year,
                plate=(payload.vehicle_plate or "").strip() or None,
                category=payload.vehicle_category,
            )

        # ── Create inquiry ──────────────────────────────
        inquiry = Inquiry(
            code=await self.inquiries.next_code(),
            customer_id=customer.id,
            vehicle_id=vehicle.id if vehicle else None,
            service_interest=payload.service_interest,
            description=payload.description.strip(),
            color_preference=payload.color_preference,
            color_family=payload.color_family,
            finish_preference=payload.finish_preference,
            has_custom_graphics=payload.has_custom_graphics,
            preferences=payload.preferences,
            status=InquiryStatus.NEW.value,
            source=InquirySource.WEBSITE.value,
            budget_range=payload.budget_range,
            desired_date=payload.desired_date,
            # Seed before flush so nothing can trigger a lazy load
            # (MissingGreenlet) on the new inquiry.
            photos=[],
        )
        await self.inquiries.add(inquiry)

        await self.audit.log(
            action=AuditAction.CREATE,
            table_name="inquiries",
            record_id=inquiry.id,
            new_data={
                "code": inquiry.code,
                "source": "WEBSITE",
                "customer_id": str(customer.id),
                "customer_created": customer_created,
            },
        )

        # ── Photos ──────────────────────────────────────
        photo_count = 0
        if photos:
            photo_payloads = await save_inquiry_photos(photos)
            for pp in photo_payloads:
                photo = InquiryPhoto(
                    inquiry_id=inquiry.id,
                    file_path=pp["file_path"],
                    file_name=pp["file_name"],
                    is_primary=pp["is_primary"],
                )
                self.db.add(photo)
                photo_count += 1

        await self.db.flush()
        # ── Dispatch notifications (fire-and-forget) ────
        # We delay until after commit so we never email about an inquiry
        # that failed to persist. The caller commits, then triggers this.
        # To keep it simple we stage the info on the inquiry object and
        # let the caller schedule the dispatch.
        inquiry._notify_context = {  # type: ignore[attr-defined]
            "customer_name": customer.name,
            "customer_phone": customer.phone or "",
            "customer_email": customer.email,
            "customer_code": customer.code,
            "customer_is_new": customer_created,
            "vehicle_label": (
                f"{vehicle.brand} {vehicle.model}"
                + (f" — {vehicle.plate_number}" if vehicle.plate_number else "")
                if vehicle else None
            ),
            "photo_count": photo_count,
        }
        return inquiry

    # ── helpers ───────────────────────────────────────

    async def _find_or_create_customer(
        self,
        *,
        name: str,
        phone: str,
        email: str | None,
    ) -> tuple[Customer, bool]:
        existing = None
        if email:
            existing = await self.customers.find_by_email(email)
        if existing is None and phone:
            existing = await self.customers.find_by_phone(phone)
        if existing is not None:
            return existing, False

        customer = Customer(
            code=await self.customers.next_code(),
            name=name,
            email=email,
            phone=phone,
            source=CustomerSource.WEBSITE.value,
            status=CustomerStatus.LEAD.value,
            is_active=True,
        )
        await self.customers.add(customer)

        await self.audit.log(
            action=AuditAction.CREATE,
            table_name="customers",
            record_id=customer.id,
            new_data={
                "code": customer.code,
                "name": customer.name,
                "source": "WEBSITE",
            },
        )
        return customer, True

    async def _find_or_create_vehicle(
        self,
        *,
        customer_id: UUID,
        brand: str,
        model: str,
        year: int | None,
        plate: str | None,
        category: str | None,
    ) -> Vehicle:
        # 1. Match by plate (if provided)
        if plate:
            existing = await self.vehicles.find_by_plate_for_customer(customer_id, plate)
            if existing is not None:
                return existing

        # 2. Match by brand + model + year
        from sqlalchemy import and_, select
        stmt = select(Vehicle).where(
            and_(
                Vehicle.customer_id == customer_id,
                Vehicle.brand == brand,
                Vehicle.model == model,
            )
        )
        if year:
            stmt = stmt.where(Vehicle.year == year)
        existing = (await self.db.execute(stmt)).scalars().first()
        if existing is not None:
            return existing

        # 3. Create new
        vehicle = Vehicle(
            customer_id=customer_id,
            brand=brand,
            model=model,
            year=year,
            plate_number=plate,
            category=category,
        )
        await self.vehicles.add(vehicle)

        await self.audit.log(
            action=AuditAction.CREATE,
            table_name="vehicles",
            record_id=vehicle.id,
            new_data={
                "customer_id": str(customer_id),
                "brand": brand,
                "model": model,
                "plate": plate,
            },
        )
        return vehicle