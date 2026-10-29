"""Business logic for the finance module."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import AuditAction
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.logging import log
from app.modules.audit.service import AuditService
from app.modules.auth.models import User
from app.modules.finance.constants import (
    DEFAULT_DP_PERCENT,
    EXPENSE_CATEGORY_LABELS,
    INVOICE_STATUSES,
    InvoiceKind,
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

        project = None
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

        # Validate money fields before touching the ORM object: AppError
        # responses still commit pending changes in DBSessionMiddleware, so a
        # rejected update must not leave a mutated invoice behind.
        subtotal = sum(
            float(i.quantity) * float(i.unit_price) for i in payload.items
        )
        discount = float(payload.discount_amount)
        if discount > subtotal + 0.01:
            raise ValidationError(
                f"Discount ({discount:,.0f}) cannot exceed "
                f"the subtotal ({subtotal:,.0f})."
            )

        if project is not None:
            await self._assert_within_contract(
                project, new_net=subtotal - discount
            )

        # A project can be billed in stages. When the caller did not pick a
        # kind, a project invoice is a final bill by default; invoices
        # without a project are always OTHER.
        if payload.project_id and "kind" in payload.model_fields_set:
            kind = payload.kind
        elif payload.project_id:
            kind = InvoiceKind.FINAL.value
        else:
            kind = InvoiceKind.OTHER.value

        invoice = Invoice(
            code=await self.repo.next_code(),
            customer_id=payload.customer_id,
            project_id=payload.project_id,
            kind=kind,
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
            await PaymentService(self.db).apply_project_advances(
                project_id=invoice.project_id,
                invoice=invoice,
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
                "kind": invoice.kind,
                "total": float(invoice.total),
            },
        )
        await self.db.refresh(invoice, ["items"])
        return invoice

    async def create_from_project(
        self, payload: InvoiceFromProject, *, actor: User
    ) -> Invoice:
        """Bill a project stage: a DP up front or the final remainder.

        Amounts are pre-tax net amounts (subtotal - discount). The contract
        value is the ceiling on everything billed across the project, so a
        DP of 50% plus a final bill of the remainder lands exactly on the
        contract regardless of tax.
        """
        from app.modules.projects.repository import ProjectRepository

        await self.repo.lock_project(payload.project_id)

        project = await ProjectRepository(self.db).get(payload.project_id)
        if not project:
            raise NotFoundError("Project not found")

        contract = self._contract_value(project)
        if contract is None:
            raise ValidationError("Project has no approved or quoted price")
        if contract <= 0.01:
            raise ValidationError(
                "Project contract value is 0 — create the invoice manually."
            )

        active = await self._active_project_invoices(project.id)
        invoiced = sum(self._net_billed(i) for i in active)
        remaining = contract - invoiced
        if remaining <= 0.01:
            raise ConflictError(
                f"Project {project.code} is fully invoiced "
                f"({invoiced:,.0f} of {contract:,.0f})."
            )

        kind = payload.kind
        if kind == InvoiceKind.FINAL.value and any(
            i.kind == InvoiceKind.FINAL.value for i in active
        ):
            raise ConflictError(
                f"Project {project.code} already has a final invoice."
            )

        if payload.amount is not None and payload.amount > remaining + 0.01:
            raise ValidationError(
                f"Amount ({payload.amount:,.0f}) exceeds the uninvoiced "
                f"remainder ({remaining:,.0f}) of project {project.code}."
            )

        if payload.amount is not None:
            amount = payload.amount
        elif kind == InvoiceKind.DP.value:
            percent = (
                payload.percent
                if payload.percent is not None
                else DEFAULT_DP_PERCENT
            )
            amount = contract * percent / 100.0
            # Never bill past the contract: a DP after a partial bill is
            # capped at what is still uninvoiced.
            amount = min(amount, remaining)
        else:
            amount = remaining

        amount = round(amount, 2)
        title = project.title or f"Project {project.code}"
        label = {
            InvoiceKind.DP.value: "DP",
            InvoiceKind.FINAL.value: "Pelunasan",
            InvoiceKind.OTHER.value: "Tagihan",
        }[kind]
        issue = payload.issue_date or today_local()

        invoice = Invoice(
            code=await self.repo.next_code(),
            customer_id=project.customer_id,
            project_id=project.id,
            kind=kind,
            issue_date=issue,
            due_date=payload.due_date,
            discount_amount=0,
            tax_rate_pct=payload.tax_rate_pct,
            status=InvoiceStatus.DRAFT.value,
            terms="Payment due on receipt.",
            notes=(
                f"Auto-generated from project {project.code} "
                f"({label.lower()}, {invoiced:,.0f} already invoiced)."
            ),
            created_by_id=actor.id,
        )

        invoice.items.append(
            InvoiceItem(
                description=f"{label} — {title}",
                quantity=1,
                unit_price=amount,
                amount=amount,
            )
        )

        await self.repo.add(invoice)
        await self._recalc_totals(invoice)

        await PaymentService(self.db).apply_project_advances(
            project_id=project.id,
            invoice=invoice,
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
                "kind": kind,
                "total": float(invoice.total),
                "uninvoiced_before": remaining,
            },
        )
        await self.db.refresh(invoice, ["items"])
        return invoice

    # ── Billing math helpers ─────────────────────────────────────

    @staticmethod
    def _contract_value(project) -> float | None:
        price = (
            project.approved_price
            if project.approved_price is not None
            else project.quoted_price
        )
        return float(price) if price is not None else None

    @staticmethod
    def _net_billed(invoice: Invoice) -> float:
        """Pre-tax amount an invoice bills: subtotal minus discount."""
        return float(invoice.subtotal or 0) - float(invoice.discount_amount or 0)

    async def _active_project_invoices(self, project_id: UUID) -> list[Invoice]:
        stmt = (
            select(Invoice)
            .where(Invoice.project_id == project_id)
            .where(Invoice.status != InvoiceStatus.CANCELLED.value)
            .order_by(Invoice.issue_date, Invoice.created_at)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def _assert_within_contract(
        self,
        project,
        *,
        new_net: float,
        exclude_invoice_id: UUID | None = None,
    ) -> None:
        """Reject billing that would push the project past its contract.

        A project with no price (or an explicit zero) is not guarded — the
        operator is invoicing something the system cannot bound.
        """
        contract = self._contract_value(project)
        if contract is None or contract <= 0.01:
            return
        active = await self._active_project_invoices(project.id)
        invoiced = sum(
            self._net_billed(i)
            for i in active
            if i.id != exclude_invoice_id
        )
        if invoiced + new_net > contract + 0.01:
            raise ValidationError(
                f"This invoice would bill {invoiced + new_net:,.0f} against "
                f"project {project.code}, over its {contract:,.0f} contract "
                f"value ({invoiced:,.0f} already invoiced)."
            )

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
        money_fields = payload.model_fields_set & {
            "items", "discount_amount", "tax_rate_pct",
        }

        # Compute the prospective money values and validate them BEFORE the
        # `setattr` loop. AppError responses still commit pending changes, so
        # `raise` after mutating would persist the invalid edit.
        paid = await self.repo.paid_amount(iid) if money_fields else 0.0

        if items_supplied and paid > 0.01:
            raise ConflictError(
                f"Cannot modify invoice items — {paid:,.0f} already paid. "
                f"Reverse the payments first."
            )

        if items_supplied and payload.items is not None:
            prospective_subtotal = sum(
                float(i.quantity) * float(i.unit_price) for i in payload.items
            )
        else:
            prospective_subtotal = float(invoice.subtotal or 0)

        prospective_discount = (
            float(payload.discount_amount)
            if "discount_amount" in payload.model_fields_set
            else float(invoice.discount_amount or 0)
        )
        if prospective_discount > prospective_subtotal + 0.01:
            raise ValidationError(
                f"Discount ({prospective_discount:,.0f}) cannot exceed the "
                f"subtotal ({prospective_subtotal:,.0f})."
            )

        # Keep staged billing within the contract even when items or the
        # discount change after creation.
        if money_fields and invoice.project_id:
            from app.modules.projects.repository import ProjectRepository

            project = await ProjectRepository(self.db).get(invoice.project_id)
            if project is not None:
                await self._assert_within_contract(
                    project,
                    new_net=prospective_subtotal - prospective_discount,
                    exclude_invoice_id=invoice.id,
                )

        if paid > 0.01:
            # Changing discount/tax on a partially paid invoice must not drop
            # the total below what has already been collected.
            prospective_tax = (
                float(payload.tax_rate_pct)
                if "tax_rate_pct" in payload.model_fields_set
                else float(invoice.tax_rate_pct or 0)
            )
            prospective_total = (
                prospective_subtotal - prospective_discount
            ) * (1 + prospective_tax / 100.0)
            if prospective_total < paid - 0.01:
                raise ConflictError(
                    f"This change would drop the invoice total to "
                    f"{prospective_total:,.0f}, below the {paid:,.0f} already "
                    f"paid. Reverse the payments first."
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

            # If the project already has an open invoice, redirect the
            # payment to it. Otherwise it would be a phantom: recorded
            # against the project but never seen by any invoice's balance.
            # The invoice is the only place `paid_amount` is computed, so
            # leaving it as PROJECT silently drops the payment from
            # receivables and the invoice's status never updates. With
            # staged billing there may be several invoices — pick the
            # oldest one that still owes money.
            existing_invoice = (await self.db.execute(
                select(Invoice)
                .where(Invoice.project_id == project.id)
                .where(Invoice.status.not_in([
                    InvoiceStatus.CANCELLED.value,
                    InvoiceStatus.PAID.value,
                ]))
                .order_by(Invoice.issue_date, Invoice.created_at)
                .limit(1)
            )).scalar_one_or_none()
            if (
                existing_invoice is not None
                and payload.direction == PaymentDirection.IN.value
            ):
                # Only absorb the payment when it fits this invoice. A
                # larger advance stays at project level so it can cover a
                # later bill instead of being rejected as an overpayment.
                inv_paid = await self.invoices.paid_amount(existing_invoice.id)
                inv_remaining = float(existing_invoice.total) - inv_paid
                if inv_remaining > 0.01 and payload.amount <= inv_remaining + 0.01:
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

            # Money received means the bill was issued. Recording a payment
            # against a DRAFT invoice used to skip SENT and jump straight to
            # PARTIALLY_PAID/PAID — issue it first so the lifecycle is honest.
            if inv.status == InvoiceStatus.DRAFT.value:
                inv.status = InvoiceStatus.SENT.value
                await self.db.flush()
                await self.audit.log(
                    action=AuditAction.INVOICE_SENT,
                    table_name="invoices",
                    record_id=inv.id,
                    user_id=actor.id,
                    old_data={"status": InvoiceStatus.DRAFT.value},
                    new_data={
                        "status": InvoiceStatus.SENT.value,
                        "reason": "payment recorded",
                    },
                )

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
                        f"project advance (DP) instead."
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

    async def apply_project_advances(
        self, *, project_id: UUID, invoice: Invoice, actor: User
    ) -> int:
        """Move project-level advances onto a freshly created invoice.

        Advances are payments received before any bill existed (the classic
        DP). They are applied only when the whole advance set fits inside
        this invoice: relinking a larger advance would leave the invoice
        "paid" beyond its total and silently consume money that belongs to
        a later bill. Leftover advances stay at project level.
        """
        stmt = (
            select(Payment)
            .where(Payment.reference_type == PaymentReferenceType.PROJECT.value)
            .where(Payment.reference_id == project_id)
        )
        payments = list((await self.db.execute(stmt)).scalars().all())
        if not payments:
            return 0

        advance_net = sum(
            float(p.amount)
            if p.direction == PaymentDirection.IN.value
            else -float(p.amount)
            for p in payments
        )
        if advance_net <= 0.01:
            return 0
        if advance_net > float(invoice.total) + 0.01:
            # UI warning; the operator can still record the bill for at
            # least the advance amount or refund the excess.
            log.warning(
                "project_advance_exceeds_invoice",
                project_id=str(project_id),
                invoice_code=invoice.code,
                advance=advance_net,
                invoice_total=float(invoice.total),
            )
            return 0

        for p in payments:
            p.reference_type = PaymentReferenceType.INVOICE.value
            p.reference_id = invoice.id

        # An invoice that received money was issued, exactly like a manual
        # payment against a DRAFT invoice.
        if invoice.status == InvoiceStatus.DRAFT.value:
            invoice.status = InvoiceStatus.SENT.value

        await self.db.flush()

        await InvoiceService(self.db).apply_payment_status(invoice.id)

        await self.audit.log(
            action=AuditAction.UPDATE,
            table_name="payments",
            record_id=invoice.id,
            user_id=actor.id,
            new_data={
                "relinked_count": len(payments),
                "invoice_id": str(invoice.id),
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
            .where(InventoryTransaction.occurred_at >= start)
            .where(InventoryTransaction.occurred_at < end_exclusive)
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
            .where(InventoryTransaction.occurred_at >= start)
            .where(InventoryTransaction.occurred_at < end_exclusive)
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
            .where(ProjectItem.occurred_at >= start)
            .where(ProjectItem.occurred_at < end_exclusive)
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
            .where(Invoice.status.in_([
                # Only issued, still-open invoices are receivables. DRAFT
                # invoices are internal and must not inflate AR.
                InvoiceStatus.SENT.value,
                InvoiceStatus.PARTIALLY_PAID.value,
                InvoiceStatus.OVERDUE.value,
            ]))
            # A fully-paid invoice may still carry an open status if legacy
            # data never ran apply_payment_status; don't count zero balances.
            .where(balance > 0.01)
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
                PurchaseOrderStatus.SENT.value,
                PurchaseOrderStatus.RECEIVED.value,
                # CLOSED means the workflow finished, not that the supplier
                # was paid. An unpaid closed PO is still a liability.
                PurchaseOrderStatus.CLOSED.value,
            ]))
            .where(balance > 0.01)
        )
        row = (await self.db.execute(stmt)).one()

        return PayablesSummary(
            total_outstanding=float(row.total or 0),
            po_count=int(row.count or 0),
        )