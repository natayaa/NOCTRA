from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

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
        stmt = (
            select(Customer)
            .where(func.lower(Customer.email) == email.strip().lower())
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def find_by_phone(self, phone: str) -> Customer | None:
        stmt = select(Customer).where(Customer.phone == phone.strip()).limit(1)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    def query(
        self,
        *,
        q: str | None = None,
        status: str | None = None,
        is_active: bool | None = None,
        city: str | None = None,
        source: str | None = None,
        sort: str = "created_desc",
    ) -> Select:
        # `noload` prevents selectin from firing for `contacts` — list view
        # does not need them. Detail paths (get / create / update) load
        # contacts explicitly via the model's `selectin` lazy strategy.
        stmt = select(Customer).options(noload(Customer.contacts))
        conds = []
        if q:
            like = f"%{q.strip()}%"
            conds.append(
                or_(
                    Customer.name.ilike(like),
                    Customer.email.ilike(like),
                    Customer.phone.ilike(like),
                    Customer.alt_phone.ilike(like),
                    Customer.code.ilike(like),
                )
            )
        if status:
            conds.append(Customer.status == status)
        if is_active is not None:
            conds.append(Customer.is_active == is_active)
        if city:
            conds.append(Customer.city.ilike(f"%{city}%"))
        if source:
            conds.append(Customer.source == source)
        if conds:
            stmt = stmt.where(and_(*conds))

        # Stable secondary sort on id prevents pagination drift
        # when primary key ties (e.g. same created_at).
        if sort == "created_asc":
            stmt = stmt.order_by(Customer.created_at.asc(), Customer.id.asc())
        elif sort == "name_asc":
            stmt = stmt.order_by(Customer.name.asc(), Customer.id.asc())
        elif sort == "name_desc":
            stmt = stmt.order_by(Customer.name.desc(), Customer.id.asc())
        elif sort == "updated_desc":
            stmt = stmt.order_by(Customer.updated_at.desc(), Customer.id.asc())
        else:  # created_desc
            stmt = stmt.order_by(Customer.created_at.desc(), Customer.id.asc())

        return stmt

    async def list_contacts(self, customer_id: UUID) -> list[CustomerContact]:
        stmt = (
            select(CustomerContact)
            .where(CustomerContact.customer_id == customer_id)
            .order_by(CustomerContact.created_at.desc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_contact(self, contact_id: UUID) -> CustomerContact | None:
        return await self.db.get(CustomerContact, contact_id)

    async def stats(self) -> dict[str, int]:
        rows = await self.db.execute(
            select(Customer.status, func.count(Customer.id)).group_by(Customer.status)
        )
        by_status = {s: c for s, c in rows.all()}

        active_count = (
            await self.db.execute(
                select(func.count(Customer.id)).where(Customer.is_active.is_(True))
            )
        ).scalar_one()

        return {
            "total": sum(by_status.values()),
            "active_records": active_count,
            **{f"status_{k}": v for k, v in by_status.items()},
        }

    async def next_code(self) -> str:
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

    async def next_code_locked(self) -> str:
        """
        Generate the next customer code under a transaction-scoped advisory
        lock, serialising concurrent `create` calls. Prevents two parallel
        requests from picking the same code and colliding on the unique
        constraint (which would otherwise surface as a 500).
        """
        year = datetime.now(UTC).year
        # Two-int form: namespace + year → unique lock per calendar year.
        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(:ns, :yr)"),
            {"ns": 900, "yr": year},
        )
        return await self.next_code()

    # ── Writes ────────────────────────────────────────
    async def add(self, customer: Customer) -> Customer:
        self.db.add(customer)
        await self.db.flush()
        return customer

    async def add_contact(self, contact: CustomerContact) -> CustomerContact:
        self.db.add(contact)
        await self.db.flush()
        return contact