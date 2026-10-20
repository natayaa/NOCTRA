"""Read/write helpers for the finance module."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import Select, and_, case, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload, selectinload

from app.modules.finance.constants import (
    InvoiceStatus,
    PaymentDirection,
    PaymentReferenceType,
)
from app.modules.finance.models import (
    Account,
    Expense,
    Invoice,
    InvoiceItem,
    Payment,
)


# ════════════════════════════════════════════════════════════════
# ACCOUNTS
# ════════════════════════════════════════════════════════════════

class AccountRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, aid: UUID) -> Account | None:
        return await self.db.get(Account, aid)

    def query(self, *, account_type: str | None = None) -> Select:
        stmt = select(Account).order_by(Account.code)
        if account_type:
            stmt = stmt.where(Account.account_type == account_type)
        return stmt


# ════════════════════════════════════════════════════════════════
# INVOICES
# ════════════════════════════════════════════════════════════════

class InvoiceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, iid: UUID) -> Invoice | None:
        stmt = (
            select(Invoice)
            .options(selectinload(Invoice.items))
            .where(Invoice.id == iid)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def by_code(self, code: str) -> Invoice | None:
        stmt = (
            select(Invoice)
            .options(selectinload(Invoice.items))
            .where(Invoice.code == code)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    def query(
        self,
        *,
        q: str | None = None,
        status: str | None = None,
        customer_id: UUID | None = None,
        project_id: UUID | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        only_unpaid: bool = False,
    ) -> Select:
        # `noload` prevents `selectin` from firing for `Invoice.items` in
        # list views — not needed and costs 1 extra query per page.
        stmt = (
            select(Invoice)
            .options(noload(Invoice.items))
            .order_by(Invoice.issue_date.desc(), Invoice.created_at.desc())
        )
        conds = []
        if q:
            like = f"%{q.strip()}%"
            conds.append(or_(Invoice.code.ilike(like), Invoice.notes.ilike(like)))
        if status:
            conds.append(Invoice.status == status)
        if customer_id:
            conds.append(Invoice.customer_id == customer_id)
        if project_id:
            conds.append(Invoice.project_id == project_id)
        if from_date:
            conds.append(Invoice.issue_date >= from_date)
        if to_date:
            conds.append(Invoice.issue_date <= to_date)
        if only_unpaid:
            conds.append(
                Invoice.status.not_in([
                    InvoiceStatus.PAID.value, InvoiceStatus.CANCELLED.value,
                ])
            )
        if conds:
            stmt = stmt.where(and_(*conds))
        return stmt

    async def next_code(self) -> str:
        year = datetime.now(UTC).year
        prefix = f"INV-{year}-"
        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
            {"key": prefix},
        )
        stmt = (
            select(Invoice.code)
            .where(Invoice.code.like(f"{prefix}%"))
            .order_by(Invoice.code.desc())
            .limit(1)
        )
        last = (await self.db.execute(stmt)).scalar_one_or_none()
        n = 1 if last is None else int(last.rsplit("-", 1)[-1]) + 1
        return f"{prefix}{n:05d}"

    async def lock_project(self, project_id: UUID) -> None:
        """
        Serialize invoice-creation-for-project. Must be acquired BEFORE
        the existing-invoice check so two requests cannot both pass it.
        Released at transaction end.
        """
        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
            {"k": f"invoice-project:{project_id}"},
        )

    async def add(self, invoice: Invoice) -> Invoice:
        self.db.add(invoice)
        await self.db.flush()
        return invoice

    async def add_item(self, item: InvoiceItem) -> InvoiceItem:
        self.db.add(item)
        await self.db.flush()
        return item

    async def delete_item(self, item: InvoiceItem) -> None:
        await self.db.delete(item)
        await self.db.flush()

    async def payments_for(self, invoice_id: UUID) -> list[Payment]:
        stmt = (
            select(Payment)
            .where(Payment.reference_type == PaymentReferenceType.INVOICE.value)
            .where(Payment.reference_id == invoice_id)
            .order_by(Payment.payment_date, Payment.created_at)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def paid_amount(self, invoice_id: UUID) -> float:
        amount_expr = case(
            (Payment.direction == PaymentDirection.IN.value, Payment.amount),
            else_=-Payment.amount,
        )
        stmt = (
            select(func.coalesce(func.sum(amount_expr), 0))
            .where(Payment.reference_type == PaymentReferenceType.INVOICE.value)
            .where(Payment.reference_id == invoice_id)
        )
        return float((await self.db.execute(stmt)).scalar_one() or 0)

    async def batch_paid_amount(self, invoice_ids: list[UUID]) -> dict[UUID, float]:
        """Fetch paid_amount for many invoices in one query — kills the N+1
        in list endpoints."""
        if not invoice_ids:
            return {}
        amount_expr = case(
            (Payment.direction == PaymentDirection.IN.value, Payment.amount),
            else_=-Payment.amount,
        )
        stmt = (
            select(
                Payment.reference_id.label("invoice_id"),
                func.coalesce(func.sum(amount_expr), 0).label("paid"),
            )
            .where(Payment.reference_type == PaymentReferenceType.INVOICE.value)
            .where(Payment.reference_id.in_(invoice_ids))
            .group_by(Payment.reference_id)
        )
        rows = (await self.db.execute(stmt)).all()
        return {r.invoice_id: float(r.paid or 0) for r in rows}


# ════════════════════════════════════════════════════════════════
# PAYMENTS
# ════════════════════════════════════════════════════════════════

class PaymentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, pid: UUID) -> Payment | None:
        return await self.db.get(Payment, pid)

    def query(
        self,
        *,
        direction: str | None = None,
        customer_id: UUID | None = None,
        supplier_id: UUID | None = None,
        reference_type: str | None = None,
        reference_id: UUID | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> Select:
        stmt = select(Payment).order_by(
            Payment.payment_date.desc(), Payment.created_at.desc()
        )
        conds = []
        if direction:
            conds.append(Payment.direction == direction)
        if customer_id:
            conds.append(Payment.customer_id == customer_id)
        if supplier_id:
            conds.append(Payment.supplier_id == supplier_id)
        if reference_type:
            conds.append(Payment.reference_type == reference_type)
        if reference_id:
            conds.append(Payment.reference_id == reference_id)
        if from_date:
            conds.append(Payment.payment_date >= from_date)
        if to_date:
            conds.append(Payment.payment_date <= to_date)
        if conds:
            stmt = stmt.where(and_(*conds))
        return stmt

    async def next_code(self) -> str:
        year = datetime.now(UTC).year
        prefix = f"PAY-{year}-"
        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
            {"key": prefix},
        )
        stmt = (
            select(Payment.code)
            .where(Payment.code.like(f"{prefix}%"))
            .order_by(Payment.code.desc())
            .limit(1)
        )
        last = (await self.db.execute(stmt)).scalar_one_or_none()
        n = 1 if last is None else int(last.rsplit("-", 1)[-1]) + 1
        return f"{prefix}{n:05d}"

    async def add(self, payment: Payment) -> Payment:
        self.db.add(payment)
        await self.db.flush()
        return payment

    async def find_reversal_for(self, payment_id: UUID) -> Payment | None:
        """Find the reversal row that cancels the given payment (FK-based)."""
        stmt = (
            select(Payment)
            .where(Payment.reversal_of_id == payment_id)
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def is_reversal(self, payment_id: UUID) -> bool:
        """True if this payment is itself a reversal entry."""
        stmt = (
            select(func.count(Payment.id))
            .where(Payment.id == payment_id)
            .where(Payment.reversal_of_id.isnot(None))
        )
        return bool((await self.db.execute(stmt)).scalar_one())

    async def payments_for_project(self, project_id: UUID) -> list[Payment]:
        invoice_ids_subq = select(Invoice.id).where(Invoice.project_id == project_id)
        stmt = (
            select(Payment)
            .where(Payment.direction == PaymentDirection.IN.value)
            .where(
                or_(
                    and_(
                        Payment.reference_type == PaymentReferenceType.PROJECT.value,
                        Payment.reference_id == project_id,
                    ),
                    and_(
                        Payment.reference_type == PaymentReferenceType.INVOICE.value,
                        Payment.reference_id.in_(invoice_ids_subq),
                    ),
                )
            )
            .order_by(Payment.payment_date, Payment.created_at)
        )
        return list((await self.db.execute(stmt)).scalars().all())


# ════════════════════════════════════════════════════════════════
# EXPENSES
# ════════════════════════════════════════════════════════════════

class ExpenseRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, eid: UUID) -> Expense | None:
        return await self.db.get(Expense, eid)

    def query(
        self,
        *,
        q: str | None = None,
        category: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> Select:
        stmt = select(Expense).order_by(
            Expense.expense_date.desc(), Expense.created_at.desc()
        )
        conds = []
        if q:
            like = f"%{q.strip()}%"
            conds.append(
                or_(
                    Expense.description.ilike(like),
                    Expense.code.ilike(like),
                    Expense.reference_number.ilike(like),
                )
            )
        if category:
            conds.append(Expense.category == category)
        if from_date:
            conds.append(Expense.expense_date >= from_date)
        if to_date:
            conds.append(Expense.expense_date <= to_date)
        if conds:
            stmt = stmt.where(and_(*conds))
        return stmt

    async def next_code(self) -> str:
        year = datetime.now(UTC).year
        prefix = f"EXP-{year}-"
        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
            {"key": prefix},
        )
        stmt = (
            select(Expense.code)
            .where(Expense.code.like(f"{prefix}%"))
            .order_by(Expense.code.desc())
            .limit(1)
        )
        last = (await self.db.execute(stmt)).scalar_one_or_none()
        n = 1 if last is None else int(last.rsplit("-", 1)[-1]) + 1
        return f"{prefix}{n:05d}"

    async def add(self, expense: Expense) -> Expense:
        self.db.add(expense)
        await self.db.flush()
        return expense