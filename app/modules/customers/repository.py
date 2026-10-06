from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.customers.models import Customer, CustomerContact


class CustomerRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Reads ─────────────────────────────────────────
    async def get(self, cid: UUID) -> Customer | None:
        return await self.db.get(Customer, cid)

    async def get_by_code(self, code: str) -> Customer | None:
        stmt = select(Customer).where(Customer.code == code)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def find_by_email(self, email: str) -> Customer | None:
        stmt = select(Customer).where(Customer.email == email).limit(1)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def find_by_phone(self, phone: str) -> Customer | None:
        stmt = select(Customer).where(Customer.phone == phone).limit(1)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    def query(
        self,
        *,
        q: str | None = None,
        status: str | None = None,
        is_active: bool | None = None,
        city: str | None = None,
    ) -> Select:
        stmt = select(Customer).order_by(Customer.created_at.desc())
        conds = []
        if q:
            like = f"%{q.strip()}%"
            conds.append(
                or_(
                    Customer.name.ilike(like),
                    Customer.email.ilike(like),
                    Customer.phone.ilike(like),
                    Customer.code.ilike(like),
                )
            )
        if status:
            conds.append(Customer.status == status)
        if is_active is not None:
            conds.append(Customer.is_active == is_active)
        if city:
            conds.append(Customer.city.ilike(f"%{city}%"))
        if conds:
            stmt = stmt.where(and_(*conds))
        return stmt

    async def next_code(self) -> str:
        """
        Generate NOCTRA-C-YYYY-NNNNNN.
        Fine for the volume NOCTRA does. If you ever need high concurrency,
        swap for a Postgres sequence or an advisory lock.
        """
        year = datetime.now(UTC).year
        prefix = f"NOCTRA-C-{year}-"
        stmt = (
            select(Customer.code)
            .where(Customer.code.like(f"{prefix}%"))
            .order_by(Customer.code.desc())
            .limit(1)
        )
        last = (await self.db.execute(stmt)).scalar_one_or_none()
        next_n = 1 if last is None else int(last.rsplit("-", 1)[-1]) + 1
        return f"{prefix}{next_n:06d}"

    # ── Writes ────────────────────────────────────────
    async def add(self, customer: Customer) -> Customer:
        self.db.add(customer)
        await self.db.flush()
        return customer

    async def add_contact(self, contact: CustomerContact) -> CustomerContact:
        self.db.add(contact)
        await self.db.flush()
        return contact

    async def list_contacts(self, customer_id: UUID) -> list[CustomerContact]:
        stmt = (
            select(CustomerContact)
            .where(CustomerContact.customer_id == customer_id)
            .order_by(CustomerContact.created_at.desc())
        )
        return list((await self.db.execute(stmt)).scalars().all())