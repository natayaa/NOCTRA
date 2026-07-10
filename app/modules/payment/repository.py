# modules/payment/repository.py
from uuid import UUID
from typing import Any, Dict, Optional, List
from decimal import Decimal
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload

from core.base import BaseRepository
from core.constants import PaymentStatus, InvoiceStatus
from .models import (
    InquiryPayment,
    InquiryInvoice,
    InvoiceItem,
    PaymentReminder,
    PaymentReconciliation,
    InvoicePDF,
)


class PaymentRepository(BaseRepository[InquiryPayment]):
    """Repository untuk Payment."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=InquiryPayment)

    # ==================== READ ====================

    async def get_by_inquiry(self, inquiry_id: UUID) -> List[InquiryPayment]:
        """Get all payments for an inquiry."""
        stmt = (
            select(InquiryPayment)
            .where(InquiryPayment.inquiry_id == inquiry_id)
            .options(
                selectinload(InquiryPayment.invoice),
                selectinload(InquiryPayment.reconciliation)
            )
            .order_by(desc(InquiryPayment.paid_at))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_project(self, project_id: UUID) -> List[InquiryPayment]:
        """Get all payments for a project."""
        stmt = (
            select(InquiryPayment)
            .where(InquiryPayment.project_id == project_id)
            .options(
                selectinload(InquiryPayment.invoice),
                selectinload(InquiryPayment.reconciliation)
            )
            .order_by(desc(InquiryPayment.paid_at))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_invoice(self, invoice_id: UUID) -> List[InquiryPayment]:
        """Get all payments for an invoice."""
        stmt = (
            select(InquiryPayment)
            .where(InquiryPayment.invoice_id == invoice_id)
            .order_by(desc(InquiryPayment.paid_at))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_completed_payments(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[InquiryPayment]:
        """Get completed payments within date range."""
        filters = [InquiryPayment.status == PaymentStatus.COMPLETED]
        if start_date:
            filters.append(InquiryPayment.paid_at >= start_date)
        if end_date:
            filters.append(InquiryPayment.paid_at <= end_date)

        stmt = (
            select(InquiryPayment)
            .where(and_(*filters))
            .options(
                selectinload(InquiryPayment.inquiry),
                selectinload(InquiryPayment.project)
            )
            .order_by(desc(InquiryPayment.paid_at))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_pending_payments(self) -> List[InquiryPayment]:
        """Get all pending payments."""
        stmt = (
            select(InquiryPayment)
            .where(InquiryPayment.status == PaymentStatus.PENDING)
            .options(
                selectinload(InquiryPayment.inquiry),
                selectinload(InquiryPayment.invoice),
            )
            .order_by(InquiryPayment.created_at)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_reconciliation(self, payment_id: UUID) -> Optional[PaymentReconciliation]:
        """Get reconciliation for a payment."""
        stmt = select(PaymentReconciliation).where(
            PaymentReconciliation.payment_id == payment_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_project_payments_summary(self, project_id: UUID) -> dict:
        """Get payment summary for a project."""
        payments = await self.get_by_project(project_id)

        completed = [p for p in payments if p.status ==
                     PaymentStatus.COMPLETED]
        pending = [p for p in payments if p.status == PaymentStatus.PENDING]
        failed = [p for p in payments if p.status == PaymentStatus.FAILED]

        return {
            "total_payments": len(payments),
            "completed_count": len(completed),
            "pending_count": len(pending),
            "failed_count": len(failed),
            "total_amount": sum(p.amount for p in completed),
            "total_pending": sum(p.amount for p in pending),
            "payment_methods": self._group_by_method(payments)
        }

    def _group_by_method(self, payments: List[InquiryPayment]) -> dict:
        """Group payments by method."""
        result = {}
        for p in payments:
            if p.payment_method not in result:
                result[p.payment_method] = {"count": 0, "total": Decimal(0)}
            if p.status == PaymentStatus.COMPLETED:
                result[p.payment_method]["count"] += 1
                result[p.payment_method]["total"] += p.amount
        return result

    # ==================== FINANCIAL ====================

    async def get_total_paid(self, inquiry_id: UUID) -> Decimal:
        """Get total paid amount for an inquiry."""
        stmt = select(func.sum(InquiryPayment.amount)).where(
            and_(
                InquiryPayment.inquiry_id == inquiry_id,
                InquiryPayment.status == PaymentStatus.COMPLETED
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar() or Decimal(0)

    async def get_total_deposit(self, inquiry_id: UUID) -> Decimal:
        """Get total deposit for an inquiry."""
        stmt = select(func.sum(InquiryPayment.amount)).where(
            and_(
                InquiryPayment.inquiry_id == inquiry_id,
                InquiryPayment.payment_type == "deposit",
                InquiryPayment.status == PaymentStatus.COMPLETED
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar() or Decimal(0)

    # ==================== UPDATE - OVERRIDE BASE ====================

    async def complete_payment(
        self,
        payment_id: UUID,
        confirmed_by: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Optional[InquiryPayment]:
        """Complete a pending payment."""
        payment = await self.get(payment_id)
        if not payment:
            return None

        if payment.status != PaymentStatus.PENDING:
            raise ValueError(
                f"Cannot complete payment with status: {payment.status}")

        payment.status = PaymentStatus.COMPLETED
        payment.paid_at = datetime.now()
        payment.confirmed_at = datetime.now()
        if confirmed_by:
            payment.confirmed_by = confirmed_by
        if notes:
            payment.notes = notes

        await self.db.flush()
        await self.db.refresh(payment)
        return payment

    async def cancel_payment(
        self,
        payment_id: UUID,
        reason: Optional[str] = None
    ) -> Optional[InquiryPayment]:
        """Cancel a payment."""
        payment = await self.get(payment_id)
        if not payment:
            return None

        if payment.status == PaymentStatus.COMPLETED:
            raise ValueError("Cannot cancel a completed payment")

        payment.status = PaymentStatus.CANCELLED
        if reason:
            payment.notes = reason

        await self.db.flush()
        await self.db.refresh(payment)
        return payment

    async def update_payment_status(
        self,
        payment_id: UUID,
        status: str,
        confirmed_by: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Optional[InquiryPayment]:
        """Update payment status."""
        payment = await self.get(payment_id)
        if not payment:
            return None

        old_status = payment.status
        payment.status = status

        if notes:
            payment.notes = notes

        if status == PaymentStatus.COMPLETED and confirmed_by:
            payment.confirmed_by = confirmed_by
            payment.confirmed_at = datetime.now()

        await self.db.flush()
        await self.db.refresh(payment)
        return payment

    # ==================== UPDATE FINANCIALS ====================

    async def update_inquiry_financials(self, inquiry_id: UUID) -> None:
        """Update inquiry financial fields."""
        from modules.inquiry.repository import InquiryRepository

        total_paid = await self.get_total_paid(inquiry_id)
        total_deposit = await self.get_total_deposit(inquiry_id)

        repo = InquiryRepository(self.db)
        inquiry = await repo.get(inquiry_id)
        if inquiry:
            inquiry.total_paid = total_paid
            inquiry.deposit_paid = total_deposit
            inquiry.balance_due = (
                inquiry.total_invoiced or Decimal(0)) - total_paid

    async def update_project_financials(self, project_id: UUID) -> None:
        """Update project deposit paid status."""
        from modules.projects.repository import ProjectRepository

        repo = ProjectRepository(self.db)
        project = await repo.get(project_id)
        if project and project.inquiry_id:
            total_deposit = await self.get_total_deposit(project.inquiry_id)
            project.deposit_paid = total_deposit >= (
                project.deposit_amount or Decimal(0))
            if project.deposit_paid and not project.deposit_paid_at:
                project.deposit_paid_at = datetime.now()

    async def update_invoice_payment(self, invoice_id: UUID) -> None:
        """Update invoice paid amount and status."""
        invoice_repo = InvoiceRepository(self.db)
        invoice = await invoice_repo.get(invoice_id)
        if not invoice:
            return

        # Get all completed payments for this invoice
        stmt = select(func.sum(InquiryPayment.amount)).where(
            and_(
                InquiryPayment.invoice_id == invoice_id,
                InquiryPayment.status == PaymentStatus.COMPLETED
            )
        )
        result = await self.db.execute(stmt)
        paid_amount = result.scalar() or Decimal('0')

        # ✅ FIX: Jangan biarkan paid_amount melebihi total_amount
        if paid_amount > invoice.total_amount:
            paid_amount = invoice.total_amount

        invoice.paid_amount = paid_amount

        # Update invoice status
        if paid_amount >= invoice.total_amount:
            invoice.status = InvoiceStatus.PAID
            invoice.paid_at = datetime.now()
        elif paid_amount > 0:
            invoice.status = InvoiceStatus.PARTIAL

    # ==================== STATISTICS ====================

    async def get_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> dict:
        """Get payment statistics."""
        filters = []
        if start_date:
            filters.append(InquiryPayment.paid_at >= start_date)
        if end_date:
            filters.append(InquiryPayment.paid_at <= end_date)

        # Total amount
        total_stmt = select(func.sum(InquiryPayment.amount)).where(
            InquiryPayment.status == PaymentStatus.COMPLETED
        )
        if filters:
            total_stmt = total_stmt.where(and_(*filters))
        total = await self.db.scalar(total_stmt) or Decimal(0)

        # By type
        type_stmt = select(
            InquiryPayment.payment_type,
            func.count().label('count'),
            func.sum(InquiryPayment.amount).label('total')
        ).where(InquiryPayment.status == PaymentStatus.COMPLETED)
        if filters:
            type_stmt = type_stmt.where(and_(*filters))
        type_stmt = type_stmt.group_by(InquiryPayment.payment_type)
        result_type = await self.db.execute(type_stmt)
        by_type = {row.payment_type: {"count": row.count,
                                      "total": row.total} for row in result_type}

        # By status
        status_stmt = select(
            InquiryPayment.status,
            func.count().label('count'),
            func.sum(InquiryPayment.amount).label('total')
        )
        if filters:
            status_stmt = status_stmt.where(and_(*filters))
        status_stmt = status_stmt.group_by(InquiryPayment.status)
        result_status = await self.db.execute(status_stmt)
        by_status = {row.status: {"count": row.count, "total": row.total}
                     for row in result_status}

        # By method
        method_stmt = select(
            InquiryPayment.payment_method,
            func.count().label('count'),
            func.sum(InquiryPayment.amount).label('total')
        ).where(InquiryPayment.status == PaymentStatus.COMPLETED)
        if filters:
            method_stmt = method_stmt.where(and_(*filters))
        method_stmt = method_stmt.group_by(InquiryPayment.payment_method)
        result_method = await self.db.execute(method_stmt)
        by_method = {row.payment_method: {"count": row.count,
                                          "total": row.total} for row in result_method}

        # Total count
        count_stmt = select(func.count(InquiryPayment.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total_count = await self.db.scalar(count_stmt) or 0

        return {
            "total_payments": total_count,
            "total_amount": float(total),
            "by_type": by_type,
            "by_status": by_status,
            "by_method": by_method
        }


class InvoiceRepository(BaseRepository[InquiryInvoice]):
    """Repository untuk Invoice."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=InquiryInvoice)

    # ==================== READ ====================

    async def get_by_inquiry(self, inquiry_id: UUID) -> List[InquiryInvoice]:
        """Get all invoices for an inquiry."""
        stmt = (
            select(InquiryInvoice)
            .where(InquiryInvoice.inquiry_id == inquiry_id)
            .options(
                selectinload(InquiryInvoice.items),
                selectinload(InquiryInvoice.payments),
                selectinload(InquiryInvoice.reminders),
            )
            .order_by(desc(InquiryInvoice.created_at))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_project(self, project_id: UUID) -> List[InquiryInvoice]:
        """Get all invoices for a project."""
        stmt = (
            select(InquiryInvoice)
            .where(InquiryInvoice.project_id == project_id)
            .options(
                selectinload(InquiryInvoice.items),
                selectinload(InquiryInvoice.payments),
            )
            .order_by(desc(InquiryInvoice.created_at))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_number(self, invoice_number: str) -> Optional[InquiryInvoice]:
        """Get invoice by number."""
        stmt = (
            select(InquiryInvoice)
            .where(InquiryInvoice.invoice_number == invoice_number)
            .options(selectinload(InquiryInvoice.items))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_details(self, invoice_id: UUID) -> Optional[InquiryInvoice]:
        """Get invoice with all details."""
        stmt = (
            select(InquiryInvoice)
            .where(InquiryInvoice.id == invoice_id)
            .options(
                selectinload(InquiryInvoice.items),
                selectinload(InquiryInvoice.payments),
                selectinload(InquiryInvoice.reminders),
                selectinload(InquiryInvoice.pdfs),
                selectinload(InquiryInvoice.inquiry),
                selectinload(InquiryInvoice.project),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_outstanding_invoices(self) -> List[InquiryInvoice]:
        """Get all outstanding invoices (not paid)."""
        stmt = (
            select(InquiryInvoice)
            .where(
                InquiryInvoice.status.in_([
                    InvoiceStatus.SENT,
                    InvoiceStatus.PARTIAL,
                    InvoiceStatus.VIEWED
                ])
            )
            .options(
                selectinload(InquiryInvoice.inquiry),
                selectinload(InquiryInvoice.items),
            )
            .order_by(InquiryInvoice.due_date)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_overdue_invoices(self) -> List[InquiryInvoice]:
        """Get all overdue invoices."""
        now = datetime.now()
        stmt = (
            select(InquiryInvoice)
            .where(
                InquiryInvoice.due_date < now,
                InquiryInvoice.status.in_([
                    InvoiceStatus.SENT,
                    InvoiceStatus.PARTIAL,
                    InvoiceStatus.VIEWED
                ])
            )
            .options(
                selectinload(InquiryInvoice.inquiry),
                selectinload(InquiryInvoice.items),
            )
            .order_by(InquiryInvoice.due_date)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_pdfs(self, invoice_id: UUID) -> List[InvoicePDF]:
        """Get all PDFs for an invoice."""
        stmt = (
            select(InvoicePDF)
            .where(InvoicePDF.invoice_id == invoice_id)
            .order_by(InvoicePDF.version.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    # ==================== FINANCIAL ====================

    async def get_total_unpaid(self, inquiry_id: UUID) -> Decimal:
        """Get total unpaid amount for an inquiry."""
        stmt = select(
            func.sum(InquiryInvoice.total_amount - InquiryInvoice.paid_amount)
        ).where(
            and_(
                InquiryInvoice.inquiry_id == inquiry_id,
                InquiryInvoice.status.in_([
                    InvoiceStatus.SENT,
                    InvoiceStatus.PARTIAL,
                    InvoiceStatus.VIEWED
                ])
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar() or Decimal(0)

    async def get_invoice_summary(self) -> dict:
        """Get summary of all invoices."""
        total_stmt = select(func.count()).select_from(InquiryInvoice)
        total = await self.db.scalar(total_stmt) or 0

        status_stmt = select(
            InquiryInvoice.status,
            func.count().label('count'),
            func.sum(InquiryInvoice.total_amount).label('total')
        ).group_by(InquiryInvoice.status)
        result_status = await self.db.execute(status_stmt)
        by_status = {row.status: {"count": row.count, "total": row.total}
                     for row in result_status}

        amount_stmt = select(func.sum(InquiryInvoice.total_amount))
        total_amount = await self.db.scalar(amount_stmt) or Decimal(0)

        unpaid_stmt = select(
            func.sum(InquiryInvoice.total_amount - InquiryInvoice.paid_amount)
        ).where(
            InquiryInvoice.status.in_([
                InvoiceStatus.SENT,
                InvoiceStatus.PARTIAL,
                InvoiceStatus.VIEWED
            ])
        )
        unpaid = await self.db.scalar(unpaid_stmt) or Decimal(0)

        return {
            "total_invoices": total,
            "total_amount": float(total_amount),
            "unpaid_amount": float(unpaid),
            "by_status": by_status,
        }

    # ==================== UPDATE ====================

    async def update_status(
        self,
        invoice_id: UUID,
        status: str,
        note: Optional[str] = None
    ) -> Optional[InquiryInvoice]:
        """Update invoice status."""
        invoice = await self.get(invoice_id)
        if not invoice:
            return None

        old_status = invoice.status
        invoice.status = status

        if note:
            invoice.notes = note

        # Track timestamps
        if status == InvoiceStatus.SENT and not invoice.sent_at:
            invoice.sent_at = datetime.now()
        elif status == InvoiceStatus.PAID:
            invoice.paid_at = datetime.now()
        elif status == InvoiceStatus.VIEWED:
            invoice.viewed_at = datetime.now()

        await self.db.flush()
        await self.db.refresh(invoice)
        return invoice

    async def send_reminder(self, invoice_id: UUID) -> Optional[InquiryInvoice]:
        """Send reminder for invoice."""
        invoice = await self.get(invoice_id)
        if not invoice:
            return None

        invoice.reminder_count += 1
        invoice.reminder_sent_at = datetime.now()

        await self.db.flush()
        await self.db.refresh(invoice)
        return invoice

    # ==================== REMINDERS ====================

    async def get_reminders(self, invoice_id: UUID) -> List[PaymentReminder]:
        """Get all reminders for an invoice."""
        stmt = (
            select(PaymentReminder)
            .where(PaymentReminder.invoice_id == invoice_id)
            .order_by(PaymentReminder.sent_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_invoices_needing_reminder(self, days_before: int = 3) -> List[InquiryInvoice]:
        """Get invoices that need reminder."""
        now = datetime.now()
        reminder_date = now + timedelta(days=days_before)

        stmt = (
            select(InquiryInvoice)
            .where(
                InquiryInvoice.status.in_(
                    [InvoiceStatus.SENT, InvoiceStatus.PARTIAL, InvoiceStatus.VIEWED]),
                InquiryInvoice.due_date <= reminder_date,
                InquiryInvoice.due_date >= now
            )
            .options(selectinload(InquiryInvoice.inquiry))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    # ==================== INVOICE NUMBER ====================

    async def generate_invoice_number(self) -> str:
        """Generate a unique invoice number."""
        year = datetime.now().strftime("%Y")
        month = datetime.now().strftime("%m")
        day = datetime.now().strftime("%d")

        stmt = select(func.max(InquiryInvoice.invoice_number)).where(
            InquiryInvoice.invoice_number.ilike(f"INV-{year}{month}{day}-%")
        )
        result = await self.db.execute(stmt)
        last_number = result.scalar()

        if last_number:
            parts = last_number.split("-")
            if len(parts) == 3:
                try:
                    seq = int(parts[2])
                    seq += 1
                except ValueError:
                    seq = 1
            else:
                seq = 1
        else:
            seq = 1

        return f"INV-{year}{month}{day}-{str(seq).zfill(4)}"


class InvoiceItemRepository(BaseRepository[InvoiceItem]):
    """Repository untuk Invoice Item."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=InvoiceItem)

    async def get_by_invoice(self, invoice_id: UUID) -> List[InvoiceItem]:
        """Get all items for an invoice."""
        stmt = (
            select(InvoiceItem)
            .where(InvoiceItem.invoice_id == invoice_id)
            .options(selectinload(InvoiceItem.price_list_item))
            .order_by(InvoiceItem.sort_order)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_total_by_invoice(self, invoice_id: UUID) -> Decimal:
        """Get total amount for an invoice."""
        stmt = select(func.sum(InvoiceItem.total_price)).where(
            InvoiceItem.invoice_id == invoice_id
        )
        result = await self.db.execute(stmt)
        return result.scalar() or Decimal(0)

    async def bulk_create(self, invoice_id: UUID, items: List[dict]) -> List[InvoiceItem]:
        """Bulk create invoice items."""
        created_items = []
        for item_data in items:
            item = InvoiceItem(invoice_id=invoice_id, **item_data)
            self.db.add(item)
            created_items.append(item)

        await self.db.flush()

        for item in created_items:
            await self.db.refresh(item)

        return created_items
