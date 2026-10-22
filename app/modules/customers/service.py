from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import AuditAction
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
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
        # Fast path: fail before doing any work.
        if payload.email and (
            existing := await self.repo.find_by_email(str(payload.email))
        ):
            raise ConflictError(
                f"Customer with this email already exists ({existing.code})",
                context={"existing_id": str(existing.id)},
            )
        if payload.phone and (
            existing := await self.repo.find_by_phone(payload.phone)
        ):
            raise ConflictError(
                f"Customer with this phone already exists ({existing.code})",
                context={"existing_id": str(existing.id)},
            )

        # Advisory lock serialises code generation across transactions.
        code = await self.repo.next_code_locked()

        customer = Customer(
            code=code,
            name=payload.name,
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
            # Seed the collection before flush; assigning it afterwards
            # triggers an async lazy load (MissingGreenlet).
            contacts=[],
        )
        try:
            await self.repo.add(customer)
        except IntegrityError as exc:
            # Concurrent request inserted the same email/phone between our
            # pre-check and this flush. Roll back the failed transaction,
            # re-query to find the winning row, and surface the same
            # ConflictError the fast path would have raised.
            await self.db.rollback()
            if payload.email and (
                existing := await self.repo.find_by_email(str(payload.email))
            ):
                raise ConflictError(
                    f"Customer with this email already exists ({existing.code})",
                    context={"existing_id": str(existing.id)},
                ) from exc
            if payload.phone and (
                existing := await self.repo.find_by_phone(payload.phone)
            ):
                raise ConflictError(
                    f"Customer with this phone already exists ({existing.code})",
                    context={"existing_id": str(existing.id)},
                ) from exc
            raise ConflictError("Duplicate customer") from exc

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

        # New customer has no contacts; the empty collection was seeded in
        # the constructor so the response DTO can read it without IO.
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
        name_clean = name.strip() if name else ""
        if not name_clean:
            raise ValidationError("name cannot be blank")

        # Fast path — most calls hit an existing customer.
        if email and (existing := await self.repo.find_by_email(email)):
            return existing, False
        if phone and (existing := await self.repo.find_by_phone(phone)):
            return existing, False

        code = await self.repo.next_code_locked()

        customer = Customer(
            code=code,
            name=name_clean,
            email=email,
            phone=phone,
            source=source,
            status=CustomerStatus.LEAD.value,
            is_active=True,
            contacts=[],
        )
        try:
            await self.repo.add(customer)
        except IntegrityError:
            # Lost the race — another request created this email/phone
            # between our pre-check and this insert. Roll back and return
            # the winner (find-or-create semantics).
            await self.db.rollback()
            if email and (existing := await self.repo.find_by_email(email)):
                return existing, False
            if phone and (existing := await self.repo.find_by_phone(phone)):
                return existing, False
            raise

        await self.audit.log(
            action=AuditAction.CREATE,
            table_name="customers",
            record_id=customer.id,
            new_data={"code": customer.code, "name": customer.name, "source": source},
        )

        return customer, True

    # ── Update ────────────────────────────────────────
    async def update(
        self, customer_id: UUID, payload: CustomerUpdate, *, actor: User
    ) -> Customer:
        customer = await self._get_or_404(customer_id)
        before = self._snapshot(customer)
        fields = payload.model_fields_set

        # Non-nullable columns must reject explicit null.
        if "name" in fields:
            if payload.name is None:
                raise ValidationError("name cannot be null")
            customer.name = payload.name

        if "country" in fields:
            if payload.country is None:
                raise ValidationError("country cannot be null")
            customer.country = payload.country

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
            "alt_phone",
            "address_line1", "address_line2", "city", "province",
            "postal_code", "tax_id", "notes",
            "status", "is_active",
        ):
            if field in fields:
                setattr(customer, field, getattr(payload, field))

        try:
            await self.db.flush()
        except IntegrityError as exc:
            # Concurrent update set the same email/phone between our
            # pre-check and this flush.
            await self.db.rollback()
            raise ConflictError(
                "Email or phone already in use by another customer"
            ) from exc

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
            name=payload.name,
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

    async def delete_contact(
        self, customer_id: UUID, contact_id: UUID, *, actor: User
    ) -> None:
        """Remove a contact. Verifies the contact belongs to the given customer."""
        contact = await self.repo.get_contact(contact_id)
        if not contact or contact.customer_id != customer_id:
            raise NotFoundError("Contact not found")

        old_data = {
            "customer_id": str(customer_id),
            "name": contact.name,
            "role": contact.role,
        }
        await self.db.delete(contact)
        await self.db.flush()
        await self.audit.log(
            action=AuditAction.DELETE,
            table_name="customer_contacts",
            record_id=contact_id,
            user_id=actor.id,
            old_data=old_data,
        )

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

    async def reactivate(self, customer_id: UUID, *, actor: User) -> Customer:
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
        return customer

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