from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import AuditAction
from app.core.exceptions import ConflictError, NotFoundError
from app.modules.audit.service import AuditService
from app.modules.auth.models import User
from app.modules.customers.constants import CustomerSource, CustomerStatus
from app.modules.customers.models import Customer, CustomerContact
from app.modules.customers.repository import CustomerRepository
from app.modules.customers.schemas import (
    CustomerContactIn,
    CustomerCreate,
    CustomerUpdate,
)


class CustomerService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CustomerRepository(db)
        self.audit = AuditService(db)

    # ── Create ────────────────────────────────────────
    async def create(
        self, payload: CustomerCreate, *, actor: User | None = None
    ) -> Customer:
        if payload.email and (existing := await self.repo.find_by_email(str(payload.email))):
            raise ConflictError(
                f"Customer with this email already exists ({existing.code})",
                context={"existing_id": str(existing.id)},
            )
        if payload.phone and (existing := await self.repo.find_by_phone(payload.phone)):
            raise ConflictError(
                f"Customer with this phone already exists ({existing.code})",
                context={"existing_id": str(existing.id)},
            )

        customer = Customer(
            code=await self.repo.next_code(),
            name=payload.name.strip(),
            email=payload.email,
            phone=payload.phone,
            alt_phone=payload.alt_phone,
            address_line1=payload.address_line1,
            address_line2=payload.address_line2,
            city=payload.city,
            province=payload.province,
            postal_code=payload.postal_code,
            country=payload.country,
            tax_id=payload.tax_id,
            notes=payload.notes,
            source=payload.source or CustomerSource.ADMIN.value,
            status=CustomerStatus.LEAD.value,
            is_active=True,
        )
        await self.repo.add(customer)

        await self.audit.log(
            action=AuditAction.CREATE,
            table_name="customers",
            record_id=customer.id,
            user_id=actor.id if actor else None,
            new_data={
                "code": customer.code,
                "name": customer.name,
                "email": customer.email,
                "phone": customer.phone,
            },
        )

        # `lazy="selectin"` only fires on objects loaded from a query,
        # not on freshly created+flushed objects. Force the load here.
        await self.db.refresh(customer, ["contacts"])
        return customer

    # ── Find-or-create (used by public intake) ─────────
    async def find_or_create(
        self,
        *,
        name: str,
        email: str | None,
        phone: str | None,
        source: str = CustomerSource.WEBSITE.value,
    ) -> tuple[Customer, bool]:
        if email and (existing := await self.repo.find_by_email(email)):
            return existing, False
        if phone and (existing := await self.repo.find_by_phone(phone)):
            return existing, False

        customer = Customer(
            code=await self.repo.next_code(),
            name=name.strip(),
            email=email,
            phone=phone,
            source=source,
            status=CustomerStatus.LEAD.value,
            is_active=True,
        )
        await self.repo.add(customer)

        await self.audit.log(
            action=AuditAction.CREATE,
            table_name="customers",
            record_id=customer.id,
            new_data={"code": customer.code, "name": customer.name, "source": source},
        )

        await self.db.refresh(customer, ["contacts"])
        return customer, True

    # ── Update ────────────────────────────────────────
    async def update(
        self, customer_id: UUID, payload: CustomerUpdate, *, actor: User
    ) -> Customer:
        customer = await self._get_or_404(customer_id)
        before = self._snapshot(customer)
        fields = payload.model_fields_set

        if "email" in fields:
            new_email = str(payload.email) if payload.email else None
            if new_email and new_email != customer.email:
                existing = await self.repo.find_by_email(new_email)
                if existing and existing.id != customer.id:
                    raise ConflictError("Email already in use by another customer")
            customer.email = new_email

        if "phone" in fields:
            new_phone = payload.phone or None
            if new_phone and new_phone != customer.phone:
                existing = await self.repo.find_by_phone(new_phone)
                if existing and existing.id != customer.id:
                    raise ConflictError("Phone already in use by another customer")
            customer.phone = new_phone

        for field in (
            "name", "alt_phone",
            "address_line1", "address_line2", "city", "province",
            "postal_code", "country", "tax_id", "notes",
            "status", "is_active",
        ):
            if field in fields:
                setattr(customer, field, getattr(payload, field))

        await self.db.flush()

        after = self._snapshot(customer)
        if before != after:
            await self.audit.log(
                action=AuditAction.UPDATE,
                table_name="customers",
                record_id=customer.id,
                user_id=actor.id,
                old_data=before,
                new_data=after,
            )
        return customer

    # ── Contacts ──────────────────────────────────────
    async def add_contact(
        self, customer_id: UUID, payload: CustomerContactIn, *, actor: User
    ) -> CustomerContact:
        customer = await self._get_or_404(customer_id)
        contact = CustomerContact(
            customer_id=customer.id,
            name=payload.name.strip(),
            role=payload.role,
            phone=payload.phone,
            email=payload.email,
            notes=payload.notes,
        )
        await self.repo.add_contact(contact)
        await self.audit.log(
            action=AuditAction.CREATE,
            table_name="customer_contacts",
            record_id=contact.id,
            user_id=actor.id,
            new_data={"customer_id": str(customer.id), "name": contact.name},
        )
        return contact

    async def list_contacts(self, customer_id: UUID) -> list[CustomerContact]:
        await self._get_or_404(customer_id)
        return await self.repo.list_contacts(customer_id)

    # ── Delete (soft) ─────────────────────────────────
    async def deactivate(self, customer_id: UUID, *, actor: User) -> None:
        customer = await self._get_or_404(customer_id)
        customer.is_active = False
        await self.db.flush()
        await self.audit.log(
            action=AuditAction.DELETE,
            table_name="customers",
            record_id=customer.id,
            user_id=actor.id,
            old_data={"is_active": True},
            new_data={"is_active": False},
        )

    async def reactivate(self, customer_id: UUID, *, actor: User) -> None:
        customer = await self._get_or_404(customer_id)
        customer.is_active = True
        await self.db.flush()
        await self.audit.log(
            action=AuditAction.UPDATE,
            table_name="customers",
            record_id=customer.id,
            user_id=actor.id,
            old_data={"is_active": False},
            new_data={"is_active": True},
        )

    # ── Helpers ───────────────────────────────────────
    async def _get_or_404(self, customer_id: UUID) -> Customer:
        customer = await self.repo.get(customer_id)
        if not customer:
            raise NotFoundError("Customer not found")
        return customer

    @staticmethod
    def _snapshot(c: Customer) -> dict:
        return {
            "name": c.name,
            "email": c.email,
            "phone": c.phone,
            "alt_phone": c.alt_phone,
            "city": c.city,
            "province": c.province,
            "status": c.status,
            "source": c.source,
            "tax_id": c.tax_id,
            "is_active": c.is_active,
        }