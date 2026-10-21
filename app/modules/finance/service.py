"""Business logic for the finance module."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import AuditAction
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.modules.audit.service import AuditService
from app.modules.auth.models import User
from app.modules.finance.constants import (
    EXPENSE_CATEGORY_LABELS,
    INVOICE_STATUSES,
    InvoiceStatus,
    PaymentDirection,
    PaymentReferenceType,
    TERMINAL_INVOICE_STATUSES,
    day_range_bounds,
    today_local,
)
from app.modules.finance.models import (
    Expense,
    Invoice,
    InvoiceItem,
    Payment,
)
from app.modules.finance.repository import (
    ExpenseRepository,
    InvoiceRepository,
    PaymentRepository,
)
from app.modules.finance.schemas import (
    CashFlowSummary,
    ExpenseCreate,
    ExpenseUpdate,
    InvoiceCreate,
    InvoiceFromProject,
    InvoiceUpdate,
    PaymentCreate,
    PayablesSummary,
    PnLLine,
    PnLReport,
    ReceivablesSummary,
)


# ════════════════════════════════════════════════════════════════
# INVOICE SERVICE
# ════════════════════════════════════════════════════════════════

class InvoiceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = InvoiceRepository(db)
        self.audit = AuditService(db)

    async def create(self, payload: InvoiceCreate, *, actor: User) -> Invoice:
        from app.modules.customers.repository import CustomerRepository

        if not await CustomerRepository(self.db).get(payload.customer_id):
            raise NotFoundError("Customer not found")

        if payload.project_id:
            await self.repo.lock_project(payload.project_id)

            from app.modules.projects.repository import ProjectRepository

            project = await ProjectRepository(self.db).get(payload.project_id)
            if not project:
                raise NotFoundError("Project not found")

            if project.customer_id != payload.customer_id:
                raise ConflictError(
                    f"Project {project.code} belongs to a different customer. "
                    f"Invoice customer must match the project's customer."
                )

            existing = (await self.db.execute(
                select(Invoice)
                .where(Invoice.project_id == payload.project_id)
                .where(Invoice.status != InvoiceStatus.CANCELLED.value)
                .limit(1)
            )).scalar_one_or_none()
            if existing:
                raise ConflictError(
                    f"Project {project.code} already has invoice "
                    f"{existing.code}. Cancel it first if you need to re-issue."
                )

        invoice = Invoice(
            code=await self.repo.next_code(),
            customer_id=payload.customer_id,
            project_id=payload.project_id,
            issue_date=payload.issue_date,
            due_date=payload.due_date,
            discount_amount=payload.discount_amount,
            tax_rate_pct=payload.tax_rate_pct,
            notes=payload.notes,
            terms=payload.terms,
            status=InvoiceStatus.DRAFT.value,
            created_by_id=actor.id,
        )

        for item_in in payload.items:
            invoice.items.append(
                InvoiceItem(
                    description=item_in.description,
                    quantity=item_in.quantity,
                    unit_price=item_in.unit_price,
                    amount=item_in.quantity * item_in.unit_price,
                )
            )

        await self.repo.add(invoice)
        await self._recalc_totals(invoice)

        if invoice.project_id:
            await PaymentService(self.db).link_project_payments_to_invoice(
                project_id=invoice.project_id,
                invoice_id=invoice.id,
                actor=actor,
            )

        await self.audit.log(
            action=AuditAction.CREATE,
            table_name="invoices",
            record_id=invoice.id,
            user_id=actor.id,
            new_data={
                "code": invoice.code,
                "customer_id": str(payload.customer_id),
                "total": float(invoice.total),
            },
        )
        await self.db.refresh(invoice, ["items"])
        return invoice

    async def create_from_project(
        self, payload: InvoiceFromProject, *, actor: User
    ) -> Invoice:
        from app.modules.projects.repository import ProjectRepository

        await self.repo.lock_project(payload.project_id)

        project = await ProjectRepository(self.db).get(payload.project_id)
        if not project:
            raise NotFoundError("Project not found")
        if project.approved_price is None and project.quoted_price is None:
            raise ValidationError("Project has no approved or quoted price")

        existing = (await self.db.execute(
            select(Invoice)
            .where(Invoice.project_id == project.id)
            .where(Invoice.status != InvoiceStatus.CANCELLED.value)
            .limit(1)
        )).scalar_one_or_none()
        if existing:
            raise ConflictError(
                f"Project {project.code} already has invoice {existing.code}. "
                f"Cancel it first if you need to re-issue."
            )

        price = float(project.approved_price or project.quoted_price)
        description = project.title or f"Project {project.code}"
        issue = payload.issue_date or today_local()

        invoice = Invoice(
            code=await self.repo.next_code(),
            customer_id=project.customer_id,
            project_id=project.id,
            issue_date=issue,
            due_date=payload.due_date,
            discount_amount=0,
            tax_rate_pct=payload.tax_rate_pct,
            status=InvoiceStatus.DRAFT.value,
            terms="Payment due on receipt.",
            notes=f"Auto-generated from project {project.code}.",
            created_by_id=actor.id,
        )

        invoice.items.append(
            InvoiceItem(
                description=description,
                quantity=1,
                unit_price=price,
                amount=price,
            )
        )

        await self.repo.add(invoice)
        await self._recalc_totals(invoice)

        await PaymentService(self.db).link_project_payments_to_invoice(
            project_id=project.id,
            invoice_id=invoice.id,
            actor=actor,
        )

        await self.audit.log(
            action=AuditAction.CREATE,
            table_name="invoices",
            record_id=invoice.id,
            user_id=actor.id,
            new_data={
                "code": invoice.code,
                "project_id": str(project.id),
                "total": float(invoice.total),
            },
        )
        await self.db.refresh(invoice, ["items"])
        return invoice

    # ── UPDATE — now supports item replacement + serializes with payments
    async def update(
        self, iid: UUID, payload: InvoiceUpdate, *, actor: User
    ) -> Invoice:
        # Serialize with record()/reverse()/change_status() so that the
        # recalc + apply_payment_status sequence is not interleaved with a
        # concurrent payment or status change. A plain `SELECT ... FOR UPDATE`
        # on the invoice row would not help — payments don't touch that row.
        await self.repo.lock_for_payment(iid)

        invoice = await self.repo.get(iid)
        if not invoice:
            raise NotFoundError("Invoice not found")

        # Reload after acquiring the lock. If we waited on a concurrent
        # payment that committed while we blocked, our identity map still
        # holds the pre-payment snapshot.
        await self.db.refresh(invoice)

        if invoice.status in TERMINAL_INVOICE_STATUSES:
            raise ConflictError(f"Cannot edit a {invoice.status} invoice")

        # items=null is rejected by the schema; reaching here with a
        # non-None value means the caller really wants to replace the list.
        items_supplied = "items" in payload.model_fields_set

        if items_supplied:
            paid = await self.repo.paid_amount(iid)
            if paid > 0.01:
                raise ConflictError(
                    f"Cannot modify invoice items — {paid:,.0f} already paid. "
                    f"Reverse the payments first."
                )

        # Apply scalar field changes. `items` is handled separately so we
        # don't try `setattr(invoice, "items", [InvoiceItemIn, ...])` which
        # would confuse the ORM relationship.
        for field in payload.model_fields_set:
            if field == "items":
                continue
            setattr(invoice, field, getattr(payload, field))

        if items_supplied and payload.items is not None:
            # `clear()` triggers cascade="all, delete-orphan" — old items are
            # deleted on flush. Append new items, then flush once so both the
            # DELETEs and INSERTs are batched.
            invoice.items.clear()
            for item_in in payload.items:
                invoice.items.append(
                    InvoiceItem(
                        description=item_in.description,
                        quantity=item_in.quantity,
                        unit_price=item_in.unit_price,
                        amount=item_in.quantity * item_in.unit_price,
                    )
                )
            await self.db.flush()

        await self._recalc_totals(invoice)
        await self.apply_payment_status(iid)

        await self.audit.log(
            action=AuditAction.UPDATE,
            table_name="invoices",
            record_id=invoice.id,
            user_id=actor.id,
            new_data={
                "code": invoice.code,
                "items_replaced": items_supplied,
            },
        )
        return invoice

    # ── CHANGE STATUS — now serializes with payments too
    async def change_status(
        self, iid: UUID, new_status: str, *, actor: User
    ) -> Invoice:
        if new_status not in INVOICE_STATUSES:
            raise ValidationError(f"status must be one of {INVOICE_STATUSES}")

        # Serialize with record()/reverse()/update() so status flips can't
        # race a concurrent payment and lose the PAID→OVERDUE downgrade.
        await self.repo.lock_for_payment(iid)

        invoice = await self.repo.get(iid)
        if not invoice:
            raise NotFoundError("Invoice not found")
        await self.db.refresh(invoice)

        current = invoice.status

        if current == InvoiceStatus.CANCELLED.value:
            raise ConflictError("Cancelled invoices cannot be modified")
        if current == InvoiceStatus.PAID.value and new_status != InvoiceStatus.PAID.value:
            raise ConflictError("Paid invoices cannot be un-paid via status change")

        if new_status == InvoiceStatus.CANCELLED.value:
            paid = await self.repo.paid_amount(iid)
            if paid > 0.01:
                raise ConflictError(
                    f"Cannot cancel invoice — {paid:,.0f} already collected. "
                    f"Reverse the payments first."
                )

        if new_status == InvoiceStatus.PAID.value and current != InvoiceStatus.PAID.value:
            paid = await self.repo.paid_amount(iid)
            total = float(invoice.total)
            if paid < total - 0.01:
                raise ConflictError(
                    f"Cannot mark as PAID — outstanding balance is "
                    f"{total - paid:,.0f}. Record a payment instead."
                )

        invoice.status = new_status

        action = (
            AuditAction.INVOICE_SENT if new_status == InvoiceStatus.SENT.value
            else AuditAction.STATUS_CHANGE
        )
        await self.db.flush()
        await self.audit.log(
            action=action,
            table_name="invoices",
            record_id=invoice.id,
            user_id=actor.id,
            old_data={"status": current},
            new_data={"status": new_status},
        )
        return invoice

    async def apply_payment_status(self, iid: UUID) -> Invoice:
        invoice = await self._get_or_404(iid)
        if invoice.status == InvoiceStatus.CANCELLED.value:
            return invoice

        paid = await self.repo.paid_amount(iid)
        total = float(invoice.total)
        today = today_local()
        is_past_due = bool(invoice.due_date and today > invoice.due_date)

        if total > 0 and paid >= total - 0.01:
            new_status = InvoiceStatus.PAID.value
        elif paid > 0:
            new_status = (
                InvoiceStatus.OVERDUE.value
                if is_past_due
                else InvoiceStatus.PARTIALLY_PAID.value
            )
        elif invoice.status in (
            InvoiceStatus.PAID.value,
            InvoiceStatus.PARTIALLY_PAID.value,
            InvoiceStatus.OVERDUE.value,
        ):
            new_status = (
                InvoiceStatus.OVERDUE.value
                if is_past_due
                else InvoiceStatus.SENT.value
            )
        elif invoice.status == InvoiceStatus.SENT.value and is_past_due:
            new_status = InvoiceStatus.OVERDUE.value
        else:
            new_status = invoice.status

        if new_status != invoice.status:
            invoice.status = new_status
            await self.db.flush()
        return invoice

    async def _recalc_totals(self, invoice: Invoice) -> None:
        items = (
            await self.db.execute(
                select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id)
            )
        ).scalars().all()

        subtotal = sum(float(i.amount) for i in items)
        invoice.subtotal = subtotal
        after_discount = subtotal - float(invoice.discount_amount or 0)
        tax = after_discount * (float(invoice.tax_rate_pct) / 100.0)
        invoice.tax_amount = tax
        invoice.total = after_discount + tax
        await self.db.flush()

    async def _get_or_404(self, iid: UUID) -> Invoice:
        inv = await self.repo.get(iid)
        if not inv:
            raise NotFoundError("Invoice not found")
        return inv


# ════════════════════════════════════════════════════════════════
# PAYMENT SERVICE
# ════════════════════════════════════════════════════════════════

class PaymentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = PaymentRepository(db)
        self.invoices = InvoiceRepository(db)
        self.audit = AuditService(db)

    async def record(self, payload: PaymentCreate, *, actor: User) -> Payment:
        if payload.direction == PaymentDirection.IN.value:
            if not payload.customer_id and not payload.reference_id:
                raise ValidationError("Direction IN requires a customer or a reference")
        elif payload.direction == PaymentDirection.OUT.value:
            if not payload.supplier_id and not payload.reference_id:
                raise ValidationError("Direction OUT requires a supplier or a reference")

        # ── Project-referenced payment ─────────────────────────────────
        if (
            payload.reference_type == PaymentReferenceType.PROJECT.value
            and payload.reference_id
        ):
            from app.modules.projects.repository import ProjectRepository

            project = await ProjectRepository(self.db).get(payload.reference_id)
            if not project:
                raise NotFoundError("Referenced project not found")

            if payload.customer_id and payload.customer_id != project.customer_id:
                raise ConflictError(
                    f"Project {project.code} belongs to a different customer."
                )

            if not payload.customer_id:
                payload = payload.model_copy(
                    update={"customer_id": project.customer_id}
                )

            # If the project already has an active invoice, redirect the
            # payment to that invoice. Otherwise it would be a phantom:
            # recorded against the project but never seen by any invoice's
            # balance. The invoice is the only place `paid_amount` is
            # computed, so leaving it as PROJECT silently drops the payment
            # from receivables and the invoice's status never updates.
            existing_invoice = (await self.db.execute(
                select(Invoice)
                .where(Invoice.project_id == project.id)
                .where(Invoice.status != InvoiceStatus.CANCELLED.value)
                .limit(1)
            )).scalar_one_or_none()
            if existing_invoice:
                payload = payload.model_copy(update={
                    "reference_type": PaymentReferenceType.INVOICE.value,
                    "reference_id": existing_invoice.id,
                })

        # ── Invoice-referenced payment ────────────────────────────────
        if (
            payload.reference_type == PaymentReferenceType.INVOICE.value
            and payload.reference_id
        ):
            # Serialize concurrent payments against the same invoice — a
            # plain `SELECT ... FOR UPDATE` on `invoices` is useless here
            # because payment inserts don't touch that row. Two parallel
            # IN payments would otherwise both read the same "remaining"
            # balance and overpay the invoice.
            await self.invoices.lock_for_payment(payload.reference_id)

            inv = await self.invoices.get(payload.reference_id)
            if not inv:
                raise NotFoundError("Referenced invoice not found")
            if inv.status == InvoiceStatus.CANCELLED.value:
                raise ConflictError("Cannot apply a payment to a cancelled invoice")

            # Inherit customer from the invoice for both IN and OUT so that
            # refunds also appear in per-customer reports.
            if not payload.customer_id:
                payload = payload.model_copy(
                    update={"customer_id": inv.customer_id}
                )
            elif payload.customer_id != inv.customer_id:
                raise ConflictError(
                    "Payment customer does not match the invoice's customer."
                )

            already_paid = await self.invoices.paid_amount(payload.reference_id)

            if payload.direction == PaymentDirection.IN.value:
                remaining = float(inv.total) - already_paid
                if payload.amount > remaining + 0.01:
                    raise ConflictError(
                        f"Payment of {payload.amount:,.0f} exceeds the outstanding "
                        f"balance of {remaining:,.0f}. Record the excess as a "
                        f"separate unapplied payment."
                    )
            else:
                if payload.amount > already_paid + 0.01:
                    raise ConflictError(
                        f"Refund of {payload.amount:,.0f} exceeds the amount already "
                        f"paid ({already_paid:,.0f})."
                    )

        payment = Payment(
            code=await self.repo.next_code(),
            direction=payload.direction,
            method=payload.method,
            amount=payload.amount,
            payment_date=payload.payment_date,
            customer_id=payload.customer_id,
            supplier_id=payload.supplier_id,
            account_id=payload.account_id,
            reference_type=payload.reference_type,
            reference_id=payload.reference_id,
            reference_number=payload.reference_number,
            notes=payload.notes,
            created_by_id=actor.id,
        )
        await self.repo.add(payment)

        if (
            payload.reference_type == PaymentReferenceType.INVOICE.value
            and payload.reference_id
        ):
            await InvoiceService(self.db).apply_payment_status(payload.reference_id)

        await self.audit.log(
            action=(
                AuditAction.PAYMENT_RECEIVED
                if payload.direction == PaymentDirection.IN.value
                else AuditAction.PAYMENT_MADE
            ),
            table_name="payments",
            record_id=payment.id,
            user_id=actor.id,
            new_data={
                "code": payment.code,
                "direction": payment.direction,
                "amount": float(payment.amount),
                "reference_type": payment.reference_type,
                "reference_id": str(payment.reference_id) if payment.reference_id else None,
            },
        )
        return payment

    async def reverse(
        self, payment_id: UUID, *, actor: User, reason: str
    ) -> Payment:
        original = await self.repo.get(payment_id)
        if not original:
            raise NotFoundError("Payment not found")

        if original.reversal_of_id is not None:
            raise ConflictError("Cannot reverse a reversal entry")

        if await self.repo.find_reversal_for(payment_id):
            raise ConflictError(f"Payment {original.code} has already been reversed")

        if (
            original.reference_type == PaymentReferenceType.INVOICE.value
            and original.reference_id
        ):
            await self.invoices.lock_for_payment(original.reference_id)

        opposite = (
            PaymentDirection.OUT.value
            if original.direction == PaymentDirection.IN.value
            else PaymentDirection.IN.value
        )

        # Snapshot attributes BEFORE the insert — a rollback would expire
        # `original` and any lazy access afterwards could fail or return
        # stale data.
        original_code = original.code
        original_amount = float(original.amount)
        original_reference_id = original.reference_id
        original_reference_type = original.reference_type

        reversal = Payment(
            code=await self.repo.next_code(),
            direction=opposite,
            method=original.method,
            amount=original.amount,
            payment_date=today_local(),
            customer_id=original.customer_id,
            supplier_id=original.supplier_id,
            account_id=original.account_id,
            reference_type=original_reference_type,
            reference_id=original_reference_id,
            reference_number=original.reference_number,
            reversal_of_id=original.id,
            notes=f"Reversal of {original_code} — {reason}",
            created_by_id=actor.id,
        )

        try:
            await self.repo.add(reversal)
        except IntegrityError as exc:
            # Two concurrent `reverse(payment_id)` calls both passed the
            # `find_reversal_for` check — the unique index on
            # `reversal_of_id` rejected the loser. Surface as 409, not 500.
            await self.db.rollback()
            raise ConflictError(
                f"Payment {original_code} has already been reversed"
            ) from exc

        if (
            original_reference_type == PaymentReferenceType.INVOICE.value
            and original_reference_id
        ):
            await InvoiceService(self.db).apply_payment_status(original_reference_id)

        await self.audit.log(
            action=AuditAction.DELETE,
            table_name="payments",
            record_id=original.id,
            user_id=actor.id,
            old_data={"code": original_code, "amount": original_amount},
            new_data={
                "reversal_code": reversal.code,
                "reversal_id": str(reversal.id),
                "reversed_direction": opposite,
                "reason": reason,
            },
        )
        return reversal

    async def link_project_payments_to_invoice(
        self, *, project_id: UUID, invoice_id: UUID, actor: User
    ) -> int:
        stmt = (
            select(Payment)
            .where(Payment.reference_type == PaymentReferenceType.PROJECT.value)
            .where(Payment.reference_id == project_id)
        )
        payments = list((await self.db.execute(stmt)).scalars().all())
        if not payments:
            return 0

        for p in payments:
            p.reference_type = PaymentReferenceType.INVOICE.value
            p.reference_id = invoice_id

        await self.db.flush()

        await InvoiceService(self.db).apply_payment_status(invoice_id)

        await self.audit.log(
            action=AuditAction.UPDATE,
            table_name="payments",
            record_id=invoice_id,
            user_id=actor.id,
            new_data={
                "relinked_count": len(payments),
                "invoice_id": str(invoice_id),
                "project_id": str(project_id),
                "payment_codes": [p.code for p in payments],
            },
        )
        return len(payments)


# ════════════════════════════════════════════════════════════════
# EXPENSE SERVICE (unchanged)
# ════════════════════════════════════════════════════════════════

class ExpenseService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ExpenseRepository(db)
        self.audit = AuditService(db)

    async def create(self, payload: ExpenseCreate, *, actor: User) -> Expense:
        exp = Expense(
            code=await self.repo.next_code(),
            category=payload.category,
            description=payload.description,
            amount=payload.amount,
            expense_date=payload.expense_date,
            account_id=payload.account_id,
            reference_number=payload.reference_number,
            notes=payload.notes,
            created_by_id=actor.id,
        )
        await self.repo.add(exp)
        await self.audit.log(
            action=AuditAction.EXPENSE_RECORDED,
            table_name="expenses",
            record_id=exp.id,
            user_id=actor.id,
            new_data={"code": exp.code, "category": exp.category, "amount": float(exp.amount)},
        )
        return exp

    async def update(
        self, eid: UUID, payload: ExpenseUpdate, *, actor: User
    ) -> Expense:
        exp = await self.repo.get(eid)
        if not exp:
            raise NotFoundError("Expense not found")

        if exp.payment_id:
            changed: list[str] = []
            if "amount" in payload.model_fields_set:
                if abs(float(payload.amount) - float(exp.amount)) > 0.001:
                    changed.append("amount")
            if "expense_date" in payload.model_fields_set:
                if payload.expense_date != exp.expense_date:
                    changed.append("expense_date")
            if changed:
                raise ConflictError(
                    f"Cannot modify {', '.join(changed)} of an expense that is "
                    f"linked to a payment. Reverse the payment first."
                )

        for field in payload.model_fields_set:
            setattr(exp, field, getattr(payload, field))

        await self.db.flush()
        await self.audit.log(
            action=AuditAction.UPDATE,
            table_name="expenses",
            record_id=exp.id,
            user_id=actor.id,
            new_data={"code": exp.code},
        )
        return exp

    async def delete(self, eid: UUID, *, actor: User) -> None:
        exp = await self.repo.get(eid)
        if not exp:
            raise NotFoundError("Expense not found")
        await self.db.delete(exp)
        await self.db.flush()
        await self.audit.log(
            action=AuditAction.DELETE,
            table_name="expenses",
            record_id=exp.id,
            user_id=actor.id,
            old_data={"code": exp.code, "amount": float(exp.amount)},
        )


# ════════════════════════════════════════════════════════════════
# REPORTS (unchanged)
# ════════════════════════════════════════════════════════════════

class FinanceReportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def pnl(self, *, from_date: date, to_date: date) -> PnLReport:
        start, end_exclusive = day_range_bounds(from_date, to_date)

        amount_expr = case(
            (Payment.direction == PaymentDirection.IN.value, Payment.amount),
            else_=-Payment.amount,
        )
        rev_stmt = (
            select(func.coalesce(func.sum(amount_expr), 0))
            .where(Payment.reference_type == PaymentReferenceType.INVOICE.value)
            .where(Payment.payment_date >= from_date)
            .where(Payment.payment_date <= to_date)
        )
        total_revenue = float((await self.db.execute(rev_stmt)).scalar_one() or 0)

        revenue_lines = [
            PnLLine(label="Customer payments received", amount=total_revenue)
        ]

        from app.modules.inventory.models import InventoryTransaction
        from app.modules.inventory.constants import TransactionType, ReferenceType

        cogs_materials_stmt = (
            select(func.coalesce(func.sum(
                InventoryTransaction.quantity * InventoryTransaction.unit_cost
            ), 0))
            .where(InventoryTransaction.transaction_type == TransactionType.CONSUMPTION.value)
            .where(InventoryTransaction.created_at >= start)
            .where(InventoryTransaction.created_at < end_exclusive)
        )
        cogs_materials = float(
            (await self.db.execute(cogs_materials_stmt)).scalar_one() or 0
        )

        reversal_stmt = (
            select(func.coalesce(func.sum(
                InventoryTransaction.quantity * InventoryTransaction.unit_cost
            ), 0))
            .where(InventoryTransaction.transaction_type == TransactionType.ADJUSTMENT_IN.value)
            .where(InventoryTransaction.reference_type == ReferenceType.PROJECT.value)
            .where(InventoryTransaction.created_at >= start)
            .where(InventoryTransaction.created_at < end_exclusive)
        )
        cogs_materials -= float(
            (await self.db.execute(reversal_stmt)).scalar_one() or 0
        )

        from app.modules.projects.models import ProjectItem
        from app.modules.projects.constants import CostCategory

        cogs_stmt = (
            select(
                ProjectItem.category,
                func.coalesce(func.sum(ProjectItem.actual_cost), 0).label("total"),
            )
            .where(ProjectItem.category.in_([
                CostCategory.LABOR.value,
                CostCategory.OUTSOURCE.value,
            ]))
            .where(ProjectItem.created_at >= start)
            .where(ProjectItem.created_at < end_exclusive)
            .group_by(ProjectItem.category)
        )
        cogs_rows = (await self.db.execute(cogs_stmt)).all()
        cogs_by_cat = {r.category: float(r.total or 0) for r in cogs_rows}
        cogs_labor = cogs_by_cat.get(CostCategory.LABOR.value, 0.0)
        cogs_outsource = cogs_by_cat.get(CostCategory.OUTSOURCE.value, 0.0)

        cogs_lines = [
            PnLLine(label="Materials consumed", amount=cogs_materials),
            PnLLine(label="Labor", amount=cogs_labor),
            PnLLine(label="Outsourcing", amount=cogs_outsource),
        ]
        total_cogs = cogs_materials + cogs_labor + cogs_outsource

        gross_profit = total_revenue - total_cogs
        gross_margin_pct = (
            (gross_profit / total_revenue) * 100 if total_revenue > 0 else 0.0
        )

        opex_stmt = (
            select(
                Expense.category,
                func.coalesce(func.sum(Expense.amount), 0).label("total"),
            )
            .where(Expense.expense_date >= from_date)
            .where(Expense.expense_date <= to_date)
            .group_by(Expense.category)
        )
        opex_rows = (await self.db.execute(opex_stmt)).all()
        opex_lines = [
            PnLLine(
                label=EXPENSE_CATEGORY_LABELS.get(row.category, row.category),
                amount=float(row.total),
            )
            for row in opex_rows
        ]
        total_opex = sum(l.amount for l in opex_lines)

        net_profit = gross_profit - total_opex
        net_margin_pct = (
            (net_profit / total_revenue) * 100 if total_revenue > 0 else 0.0
        )

        if total_revenue > 0:
            for line in revenue_lines + cogs_lines + opex_lines:
                line.pct_of_revenue = round((line.amount / total_revenue) * 100, 2)

        return PnLReport(
            period_start=from_date,
            period_end=to_date,
            revenue_lines=revenue_lines,
            total_revenue=total_revenue,
            cogs_lines=cogs_lines,
            total_cogs=total_cogs,
            gross_profit=gross_profit,
            gross_margin_pct=round(gross_margin_pct, 2),
            opex_lines=opex_lines,
            total_opex=total_opex,
            net_profit=net_profit,
            net_margin_pct=round(net_margin_pct, 2),
        )

    async def cash_flow(self, *, from_date: date, to_date: date) -> CashFlowSummary:
        agg_stmt = select(
            func.coalesce(func.sum(case(
                (Payment.direction == PaymentDirection.IN.value, Payment.amount),
                else_=0,
            )), 0).label("inflow"),
            func.coalesce(func.sum(case(
                (Payment.direction == PaymentDirection.OUT.value, Payment.amount),
                else_=0,
            )), 0).label("outflow"),
        ).where(Payment.payment_date >= from_date).where(Payment.payment_date <= to_date)

        row = (await self.db.execute(agg_stmt)).one()
        inflow = float(row.inflow or 0)
        outflow = float(row.outflow or 0)

        return CashFlowSummary(
            period_start=from_date,
            period_end=to_date,
            total_inflow=inflow,
            total_outflow=outflow,
            net_cash_flow=inflow - outflow,
        )

    async def receivables(self) -> ReceivablesSummary:
        paid_subq = (
            select(
                Payment.reference_id.label("invoice_id"),
                func.coalesce(func.sum(case(
                    (Payment.direction == PaymentDirection.IN.value, Payment.amount),
                    else_=-Payment.amount,
                )), 0).label("paid"),
            )
            .where(Payment.reference_type == PaymentReferenceType.INVOICE.value)
            .group_by(Payment.reference_id)
            .subquery()
        )

        balance = func.greatest(
            func.coalesce(Invoice.total, 0) - func.coalesce(paid_subq.c.paid, 0),
            0,
        )
        today = today_local()
        is_overdue = Invoice.due_date.isnot(None) & (Invoice.due_date < today)

        stmt = (
            select(
                func.coalesce(func.sum(balance), 0).label("total"),
                func.coalesce(func.sum(case(
                    (is_overdue, balance),
                    else_=0,
                )), 0).label("overdue"),
                func.count(Invoice.id).label("count"),
                func.coalesce(func.sum(case(
                    (is_overdue, 1),
                    else_=0,
                )), 0).label("overdue_count"),
            )
            .outerjoin(paid_subq, paid_subq.c.invoice_id == Invoice.id)
            .where(Invoice.status.not_in([
                InvoiceStatus.PAID.value, InvoiceStatus.CANCELLED.value,
            ]))
        )
        row = (await self.db.execute(stmt)).one()

        return ReceivablesSummary(
            total_outstanding=float(row.total or 0),
            total_overdue=float(row.overdue or 0),
            invoice_count=int(row.count or 0),
            overdue_count=int(row.overdue_count or 0),
        )

    async def payables(self) -> PayablesSummary:
        from app.modules.inventory.constants import PurchaseOrderStatus
        from app.modules.inventory.models import PurchaseOrder

        paid_subq = (
            select(
                Payment.reference_id.label("po_id"),
                func.coalesce(func.sum(case(
                    (Payment.direction == PaymentDirection.OUT.value, Payment.amount),
                    else_=-Payment.amount,
                )), 0).label("paid"),
            )
            .where(Payment.reference_type == PaymentReferenceType.PURCHASE_ORDER.value)
            .group_by(Payment.reference_id)
            .subquery()
        )

        balance = func.greatest(
            func.coalesce(PurchaseOrder.total_amount, 0)
            - func.coalesce(paid_subq.c.paid, 0),
            0,
        )

        stmt = (
            select(
                func.coalesce(func.sum(balance), 0).label("total"),
                func.count(PurchaseOrder.id).label("count"),
            )
            .outerjoin(paid_subq, paid_subq.c.po_id == PurchaseOrder.id)
            .where(PurchaseOrder.status.in_([
                PurchaseOrderStatus.RECEIVED.value,
                PurchaseOrderStatus.SENT.value,
            ]))
        )
        row = (await self.db.execute(stmt)).one()

        return PayablesSummary(
            total_outstanding=float(row.total or 0),
            po_count=int(row.count or 0),
        )