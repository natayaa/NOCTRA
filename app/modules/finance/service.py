"""Business logic for the finance module.

- Invoices: create, send, apply payments, cancel
- Payments: record in/out, apply to invoices, update invoice status
- Expenses: record operational spending
- Reports: P&L, cash flow, receivables, payables
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import AuditAction
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.modules.audit.service import AuditService
from app.modules.auth.models import User
from app.modules.finance.constants import (
    EXPENSE_CATEGORY_LABELS,
    InvoiceStatus,
    PaymentDirection,
    PaymentReferenceType,
    TERMINAL_INVOICE_STATUSES,
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
from app.modules.finance.constants import ExpenseCategory


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
        await self.repo.add(invoice)

        for item_in in payload.items:
            await self.repo.add_item(
                InvoiceItem(
                    invoice_id=invoice.id,
                    description=item_in.description,
                    quantity=item_in.quantity,
                    unit_price=item_in.unit_price,
                    amount=item_in.quantity * item_in.unit_price,
                )
            )

        await self._recalc_totals(invoice)

        await self.audit.log(
            action=AuditAction.CREATE,
            table_name="invoices",
            record_id=invoice.id,
            user_id=actor.id,
            new_data={"code": invoice.code, "customer_id": str(payload.customer_id), "total": float(invoice.total)},
        )
        return invoice

    async def create_from_project(
        self, payload: InvoiceFromProject, *, actor: User
    ) -> Invoice:
        from app.modules.projects.repository import ProjectRepository

        project = await ProjectRepository(self.db).get(payload.project_id)
        if not project:
            raise NotFoundError("Project not found")
        if project.approved_price is None and project.quoted_price is None:
            raise ValidationError("Project has no approved or quoted price")

        price = float(project.approved_price or project.quoted_price)

        # Build a sensible default line item from the project
        description = project.title or f"Project {project.code}"
        issue = payload.issue_date or datetime.now(UTC).date()

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
        await self.repo.add(invoice)

        await self.repo.add_item(
            InvoiceItem(
                invoice_id=invoice.id,
                description=description,
                quantity=1,
                unit_price=price,
                amount=price,
            )
        )

        await self._recalc_totals(invoice)

        await self.audit.log(
            action=AuditAction.CREATE,
            table_name="invoices",
            record_id=invoice.id,
            user_id=actor.id,
            new_data={"code": invoice.code, "project_id": str(project.id), "total": float(invoice.total)},
        )
        return invoice

    async def update(
        self, iid: UUID, payload: InvoiceUpdate, *, actor: User
    ) -> Invoice:
        invoice = await self._get_or_404(iid)
        if invoice.status in TERMINAL_INVOICE_STATUSES:
            raise ConflictError(f"Cannot edit a {invoice.status} invoice")

        for field, value in payload.model_dump(exclude_unset=True).items():
            if value is not None:
                setattr(invoice, field, value)

        await self._recalc_totals(invoice)
        await self.audit.log(
            action=AuditAction.UPDATE,
            table_name="invoices",
            record_id=invoice.id,
            user_id=actor.id,
            new_data={"code": invoice.code},
        )
        return invoice

    async def change_status(
        self, iid: UUID, new_status: str, *, actor: User
    ) -> Invoice:
        invoice = await self._get_or_404(iid)
        current = invoice.status

        # Validate transition
        if current == InvoiceStatus.CANCELLED.value:
            raise ConflictError("Cancelled invoices cannot be modified")
        if current == InvoiceStatus.PAID.value and new_status != InvoiceStatus.PAID.value:
            raise ConflictError("Paid invoices cannot be un-paid via status change")

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
        """
        Recompute the invoice status based on its payments.
        Called after a payment is recorded against it.
        """
        invoice = await self._get_or_404(iid)
        if invoice.status in TERMINAL_INVOICE_STATUSES:
            return invoice

        paid = await self.repo.paid_amount(iid)
        total = float(invoice.total)

        if paid <= 0:
            # No payments — leave at current status (SENT or DRAFT)
            pass
        elif paid >= total - 0.01:
            invoice.status = InvoiceStatus.PAID.value
        else:
            invoice.status = InvoiceStatus.PARTIALLY_PAID.value

        # Check for overdue
        if invoice.status not in TERMINAL_INVOICE_STATUSES and invoice.due_date:
            if datetime.now(UTC).date() > invoice.due_date:
                invoice.status = InvoiceStatus.OVERDUE.value

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
        # Validation
        if payload.direction == PaymentDirection.IN.value:
            if not payload.customer_id and not payload.reference_id:
                raise ValidationError("Direction IN requires a customer or a reference")
        elif payload.direction == PaymentDirection.OUT.value:
            if not payload.supplier_id and not payload.reference_id:
                raise ValidationError("Direction OUT requires a supplier or a reference")

        # Validate reference exists if given
        if payload.reference_type == PaymentReferenceType.INVOICE.value and payload.reference_id:
            inv = await self.invoices.get(payload.reference_id)
            if not inv:
                raise NotFoundError("Referenced invoice not found")
            if inv.status == InvoiceStatus.CANCELLED.value:
                raise ConflictError("Cannot apply a payment to a cancelled invoice")

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

        # Auto-apply to invoice status
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


# ════════════════════════════════════════════════════════════════
# EXPENSE SERVICE
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
        for field, value in payload.model_dump(exclude_unset=True).items():
            if value is not None:
                setattr(exp, field, value)
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
# REPORTS
# ════════════════════════════════════════════════════════════════

class FinanceReportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def pnl(self, *, from_date: date, to_date: date) -> PnLReport:
        """
        Compute a Profit & Loss statement for the period.

        Revenue  = sum of payments IN with reference_type=INVOICE
                   (cash-basis, not accrual — matches how a workshop thinks)
        COGS     = materials consumed + labor + outsourcing on projects
                   delivered in the period (from inventory_transactions
                   and project_items)
        OpEx     = sum of expenses in the period
        """
        # ── Revenue (cash received) ────────────────────
        rev_stmt = (
            select(func.coalesce(func.sum(Payment.amount), 0))
            .where(Payment.direction == PaymentDirection.IN.value)
            .where(Payment.payment_date >= from_date)
            .where(Payment.payment_date <= to_date)
        )
        total_revenue = float((await self.db.execute(rev_stmt)).scalar_one() or 0)

        revenue_lines = [
            PnLLine(label="Customer payments received", amount=total_revenue)
        ]

        # ── COGS (materials consumed in period) ────────
        from app.modules.inventory.models import InventoryTransaction
        from app.modules.inventory.constants import TransactionType

        cogs_materials_stmt = (
            select(func.coalesce(func.sum(InventoryTransaction.quantity * InventoryTransaction.unit_cost), 0))
            .where(InventoryTransaction.transaction_type == TransactionType.CONSUMPTION.value)
            .where(func.date(InventoryTransaction.created_at) >= from_date)
            .where(func.date(InventoryTransaction.created_at) <= to_date)
        )
        cogs_materials = float((await self.db.execute(cogs_materials_stmt)).scalar_one() or 0)

        # Labor + outsource from project items where actual_cost is set
        # and the project was delivered/started in the period
        from app.modules.projects.models import ProjectItem
        from app.modules.projects.constants import CostCategory

        cogs_labor_stmt = (
            select(func.coalesce(func.sum(ProjectItem.actual_cost), 0))
            .where(ProjectItem.category == CostCategory.LABOR.value)
            .where(ProjectItem.created_at >= datetime.combine(from_date, datetime.min.time(), tzinfo=UTC))
            .where(ProjectItem.created_at <= datetime.combine(to_date, datetime.max.time(), tzinfo=UTC))
        )
        cogs_labor = float((await self.db.execute(cogs_labor_stmt)).scalar_one() or 0)

        cogs_outsource_stmt = (
            select(func.coalesce(func.sum(ProjectItem.actual_cost), 0))
            .where(ProjectItem.category == CostCategory.OUTSOURCE.value)
            .where(ProjectItem.created_at >= datetime.combine(from_date, datetime.min.time(), tzinfo=UTC))
            .where(ProjectItem.created_at <= datetime.combine(to_date, datetime.max.time(), tzinfo=UTC))
        )
        cogs_outsource = float((await self.db.execute(cogs_outsource_stmt)).scalar_one() or 0)

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

        # ── Operating expenses ─────────────────────────
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

        # Fill in pct_of_revenue for all lines
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
        inflow_stmt = (
            select(func.coalesce(func.sum(Payment.amount), 0))
            .where(Payment.direction == PaymentDirection.IN.value)
            .where(Payment.payment_date >= from_date)
            .where(Payment.payment_date <= to_date)
        )
        inflow = float((await self.db.execute(inflow_stmt)).scalar_one() or 0)

        outflow_stmt = (
            select(func.coalesce(func.sum(Payment.amount), 0))
            .where(Payment.direction == PaymentDirection.OUT.value)
            .where(Payment.payment_date >= from_date)
            .where(Payment.payment_date <= to_date)
        )
        outflow = float((await self.db.execute(outflow_stmt)).scalar_one() or 0)

        return CashFlowSummary(
            period_start=from_date,
            period_end=to_date,
            total_inflow=inflow,
            total_outflow=outflow,
            net_cash_flow=inflow - outflow,
        )

    async def receivables(self) -> ReceivablesSummary:
        """Sum of unpaid invoices."""
        stmt = select(Invoice).where(
            Invoice.status.not_in([InvoiceStatus.PAID.value, InvoiceStatus.CANCELLED.value])
        )
        invoices = list((await self.db.execute(stmt)).scalars().all())

        repo = InvoiceRepository(self.db)
        total = 0.0
        overdue = 0.0
        overdue_count = 0
        today = datetime.now(UTC).date()

        for inv in invoices:
            paid = await repo.paid_amount(inv.id)
            balance = float(inv.total) - paid
            total += balance
            if inv.due_date and today > inv.due_date:
                overdue += balance
                overdue_count += 1

        return ReceivablesSummary(
            total_outstanding=total,
            total_overdue=overdue,
            invoice_count=len(invoices),
            overdue_count=overdue_count,
        )

    async def payables(self) -> PayablesSummary:
        """Sum of unpaid purchase orders."""
        from app.modules.inventory.constants import PurchaseOrderStatus
        from app.modules.inventory.models import PurchaseOrder

        stmt = select(PurchaseOrder).where(
            PurchaseOrder.status.in_([
                PurchaseOrderStatus.RECEIVED.value,
                PurchaseOrderStatus.SENT.value,
            ])
        )
        pos = list((await self.db.execute(stmt)).scalars().all())

        total = 0.0
        for po in pos:
            # Payments out referencing this PO
            paid_stmt = (
                select(func.coalesce(func.sum(Payment.amount), 0))
                .where(Payment.direction == PaymentDirection.OUT.value)
                .where(Payment.reference_type == PaymentReferenceType.PURCHASE_ORDER.value)
                .where(Payment.reference_id == po.id)
            )
            paid = float((await self.db.execute(paid_stmt)).scalar_one() or 0)
            total += max(0, float(po.total_amount) - paid)

        return PayablesSummary(total_outstanding=total, po_count=len(pos))