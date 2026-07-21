# modules/payment/repository.py
"""
Payment Repository - REFACTORED

✅ Soft delete support (is_deleted filter di semua query)
✅ Clear separation: PaymentRepository, InvoiceRepository, InvoiceItemRepository
✅ Lazy loading with selectinload
✅ Financial calculations dengan Decimal
"""

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
    """Repository untuk Payment - TANPA FLUSH/REFRESH/COMMIT."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=InquiryPayment)

    # ============================================================
    # READ OPERATIONS
    # ============================================================

    async def get(self, pk: UUID, include_deleted: bool = False) -> Optional[InquiryPayment]:
        """Get payment by ID with soft delete filter."""
        stmt = select(self.model).where(self.model.id == pk)
        if not include_deleted:
            stmt = stmt.where(self.model.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_details(self, payment_id: UUID) -> Optional[InquiryPayment]:
        """Get payment with all related data."""
        stmt = (
            select(InquiryPayment)
            .where(
                InquiryPayment.id == payment_id,
                InquiryPayment.is_deleted == False
            )
            .options(
                selectinload(InquiryPayment.inquiry),
                selectinload(InquiryPayment.project),
                selectinload(InquiryPayment.invoice),
                selectinload(InquiryPayment.reconciliation),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_inquiry(
        self,
        inquiry_id: UUID,
        include_deleted: bool = False
    ) -> List[InquiryPayment]:
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
        if not include_deleted:
            stmt = stmt.where(InquiryPayment.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_project(
        self,
        project_id: UUID,
        include_deleted: bool = False
    ) -> List[InquiryPayment]:
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
        if not include_deleted:
            stmt = stmt.where(InquiryPayment.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_invoice(
        self,
        invoice_id: UUID,
        include_deleted: bool = False
    ) -> List[InquiryPayment]:
        """Get all payments for an invoice."""
        stmt = (
            select(InquiryPayment)
            .where(InquiryPayment.invoice_id == invoice_id)
            .order_by(desc(InquiryPayment.paid_at))
        )
        if not include_deleted:
            stmt = stmt.where(InquiryPayment.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_completed_payments(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        include_deleted: bool = False
    ) -> List[InquiryPayment]:
        """Get completed payments within date range."""
        filters = [
            InquiryPayment.status == PaymentStatus.COMPLETED,
            InquiryPayment.is_deleted == False
        ]
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

    async def get_pending_payments(self, include_deleted: bool = False) -> List[InquiryPayment]:
        """Get all pending payments."""
        filters = [
            InquiryPayment.status == PaymentStatus.PENDING,
            InquiryPayment.is_deleted == False
        ]
        stmt = (
            select(InquiryPayment)
            .where(and_(*filters))
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
            PaymentReconciliation.payment_id == payment_id,
            PaymentReconciliation.is_deleted == False
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_project_payments_summary(self, project_id: UUID) -> dict:
        """Get payment summary for a project."""
        payments = await self.get_by_project(project_id)

        completed = [p for p in payments if p.status == PaymentStatus.COMPLETED]
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

    # ============================================================
    # FINANCIAL CALCULATIONS
    # ============================================================

    async def get_total_paid(self, inquiry_id: UUID) -> Decimal:
        """Get total paid amount for an inquiry."""
        stmt = select(func.sum(InquiryPayment.amount)).where(
            and_(
                InquiryPayment.inquiry_id == inquiry_id,
                InquiryPayment.status == PaymentStatus.COMPLETED,
                InquiryPayment.is_deleted == False
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
                InquiryPayment.status == PaymentStatus.COMPLETED,
                InquiryPayment.is_deleted == False
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar() or Decimal(0)

    async def get_total_by_type(
        self,
        inquiry_id: UUID,
        payment_type: str,
        status: Optional[str] = None
    ) -> Decimal:
        """Get total by payment type."""
        filters = [
            InquiryPayment.inquiry_id == inquiry_id,
            InquiryPayment.payment_type == payment_type,
            InquiryPayment.is_deleted == False
        ]
        if status:
            filters.append(InquiryPayment.status == status)

        stmt = select(func.sum(InquiryPayment.amount)).where(and_(*filters))
        result = await self.db.execute(stmt)
        return result.scalar() or Decimal(0)

    # ============================================================
    # UPDATE OPERATIONS
    # ============================================================

    async def complete_payment(
        self,
        payment_id: UUID,
        confirmed_by: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Optional[InquiryPayment]:
        """Complete a pending payment - TANPA flush."""
        payment = await self.get(payment_id)
        if not payment or payment.is_deleted:
            return None

        if payment.status != PaymentStatus.PENDING:
            raise ValueError(f"Cannot complete payment with status: {payment.status}")

        payment.status = PaymentStatus.COMPLETED
        payment.paid_at = datetime.now()
        payment.confirmed_at = datetime.now()
        if confirmed_by:
            payment.confirmed_by = confirmed_by
        if notes:
            payment.notes = notes

        return payment

    async def cancel_payment(
        self,
        payment_id: UUID,
        reason: Optional[str] = None
    ) -> Optional[InquiryPayment]:
        """Cancel a payment - TANPA flush."""
        payment = await self.get(payment_id)
        if not payment or payment.is_deleted:
            return None

        if payment.status == PaymentStatus.COMPLETED:
            raise ValueError("Cannot cancel a completed payment")

        payment.status = PaymentStatus.CANCELLED
        if reason:
            payment.notes = reason

        return payment

    async def update_payment_status(
        self,
        payment_id: UUID,
        status: str,
        confirmed_by: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Optional[InquiryPayment]:
        """Update payment status - TANPA flush."""
        payment = await self.get(payment_id)
        if not payment or payment.is_deleted:
            return None

        payment.status = status
        if notes:
            payment.notes = notes

        if status == PaymentStatus.COMPLETED and confirmed_by:
            payment.confirmed_by = confirmed_by
            payment.confirmed_at = datetime.now()

        return payment

    # ============================================================
    # UPDATE FINANCIALS (Cross-module updates)
    # ============================================================

    async def update_inquiry_financials(self, inquiry_id: UUID) -> None:
        """Update inquiry financial fields - TANPA flush."""
        from modules.inquiry.repository import InquiryRepository

        total_paid = await self.get_total_paid(inquiry_id)
        total_deposit = await self.get_total_deposit(inquiry_id)

        repo = InquiryRepository(self.db)
        inquiry = await repo.get(inquiry_id)
        if inquiry and not inquiry.is_deleted:
            inquiry.total_paid = total_paid
            inquiry.deposit_paid = total_deposit
            inquiry.balance_due = (inquiry.total_invoiced or Decimal(0)) - total_paid

    async def update_project_financials(self, project_id: UUID) -> None:
        """Update project deposit paid status - TANPA flush."""
        from modules.project.repository import ProjectRepository

        repo = ProjectRepository(self.db)
        project = await repo.get(project_id)
        if project and not project.is_deleted and project.inquiry_id:
            total_deposit = await self.get_total_deposit(project.inquiry_id)
            project.deposit_paid = total_deposit >= (project.deposit_amount or Decimal(0))
            if project.deposit_paid and not project.deposit_paid_at:
                project.deposit_paid_at = datetime.now()

    async def update_invoice_payment(self, invoice_id: UUID) -> None:
        """Update invoice paid amount and status - TANPA flush."""
        invoice_repo = InvoiceRepository(self.db)
        invoice = await invoice_repo.get(invoice_id)
        if not invoice or invoice.is_deleted:
            return

        # Get all completed payments for this invoice
        stmt = select(func.sum(InquiryPayment.amount)).where(
            and_(
                InquiryPayment.invoice_id == invoice_id,
                InquiryPayment.status == PaymentStatus.COMPLETED,
                InquiryPayment.is_deleted == False
            )
        )
        result = await self.db.execute(stmt)
        paid_amount = result.scalar() or Decimal('0')

        if paid_amount > invoice.total_amount:
            paid_amount = invoice.total_amount

        invoice.paid_amount = paid_amount

        if paid_amount >= invoice.total_amount:
            invoice.status = InvoiceStatus.PAID
            invoice.paid_at = datetime.now()
        elif paid_amount > 0:
            invoice.status = InvoiceStatus.PARTIAL

    # ============================================================
    # DELETE OPERATIONS
    # ============================================================

    async def delete(self, pk: UUID) -> bool:
        """Soft delete payment - TANPA flush."""
        payment = await self.get(pk)
        if not payment:
            return False

        payment.is_deleted = True
        payment.deleted_at = datetime.now()
        return True

    async def hard_delete(self, pk: UUID) -> bool:
        """Hard delete payment - TANPA flush."""
        payment = await self.get(pk, include_deleted=True)
        if not payment:
            return False

        await self.db.delete(payment)
        return True

    # ============================================================
    # STATISTICS
    # ============================================================

    async def get_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> dict:
        """Get payment statistics."""
        filters = [InquiryPayment.is_deleted == False]
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
        type_stmt = (
            select(
                InquiryPayment.payment_type,
                func.count().label('count'),
                func.sum(InquiryPayment.amount).label('total')
            )
            .where(InquiryPayment.status == PaymentStatus.COMPLETED)
        )
        if filters:
            type_stmt = type_stmt.where(and_(*filters))
        type_stmt = type_stmt.group_by(InquiryPayment.payment_type)
        result_type = await self.db.execute(type_stmt)
        by_type = {row.payment_type: {"count": row.count, "total": row.total} for row in result_type}

        # By status
        status_stmt = (
            select(
                InquiryPayment.status,
                func.count().label('count'),
                func.sum(InquiryPayment.amount).label('total')
            )
        )
        if filters:
            status_stmt = status_stmt.where(and_(*filters))
        status_stmt = status_stmt.group_by(InquiryPayment.status)
        result_status = await self.db.execute(status_stmt)
        by_status = {row.status: {"count": row.count, "total": row.total} for row in result_status}

        # By method
        method_stmt = (
            select(
                InquiryPayment.payment_method,
                func.count().label('count'),
                func.sum(InquiryPayment.amount).label('total')
            )
            .where(InquiryPayment.status == PaymentStatus.COMPLETED)
        )
        if filters:
            method_stmt = method_stmt.where(and_(*filters))
        method_stmt = method_stmt.group_by(InquiryPayment.payment_method)
        result_method = await self.db.execute(method_stmt)
        by_method = {row.payment_method: {"count": row.count, "total": row.total} for row in result_method}

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
    """Repository untuk Invoice - TANPA FLUSH/REFRESH/COMMIT."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=InquiryInvoice)

    # ============================================================
    # READ OPERATIONS
    # ============================================================

    async def get(self, pk: UUID, include_deleted: bool = False) -> Optional[InquiryInvoice]:
        """Get invoice by ID with soft delete filter."""
        stmt = select(self.model).where(self.model.id == pk)
        if not include_deleted:
            stmt = stmt.where(self.model.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_details(self, invoice_id: UUID) -> Optional[InquiryInvoice]:
        """Get invoice with all details."""
        stmt = (
            select(InquiryInvoice)
            .where(
                InquiryInvoice.id == invoice_id,
                InquiryInvoice.is_deleted == False
            )
            .options(
                selectinload(InquiryInvoice.items).selectinload(InvoiceItem.price_list_item),
                selectinload(InquiryInvoice.payments),
                selectinload(InquiryInvoice.reminders),
                selectinload(InquiryInvoice.pdfs),
                selectinload(InquiryInvoice.inquiry),
                selectinload(InquiryInvoice.project),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_inquiry(
        self,
        inquiry_id: UUID,
        include_deleted: bool = False
    ) -> List[InquiryInvoice]:
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
        if not include_deleted:
            stmt = stmt.where(InquiryInvoice.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_project(
        self,
        project_id: UUID,
        include_deleted: bool = False
    ) -> List[InquiryInvoice]:
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
        if not include_deleted:
            stmt = stmt.where(InquiryInvoice.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_number(self, invoice_number: str) -> Optional[InquiryInvoice]:
        """Get invoice by number."""
        stmt = (
            select(InquiryInvoice)
            .where(
                InquiryInvoice.invoice_number == invoice_number,
                InquiryInvoice.is_deleted == False
            )
            .options(selectinload(InquiryInvoice.items))
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
                ]),
                InquiryInvoice.is_deleted == False
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
                ]),
                InquiryInvoice.is_deleted == False
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
            .where(
                InvoicePDF.invoice_id == invoice_id,
                InvoicePDF.is_deleted == False
            )
            .order_by(InvoicePDF.version.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    # ============================================================
    # FINANCIAL CALCULATIONS
    # ============================================================

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
                ]),
                InquiryInvoice.is_deleted == False
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar() or Decimal(0)

    async def get_invoice_summary(self) -> dict:
        """Get summary of all invoices."""
        total_stmt = select(func.count()).select_from(InquiryInvoice).where(
            InquiryInvoice.is_deleted == False
        )
        total = await self.db.scalar(total_stmt) or 0

        status_stmt = (
            select(
                InquiryInvoice.status,
                func.count().label('count'),
                func.sum(InquiryInvoice.total_amount).label('total')
            )
            .where(InquiryInvoice.is_deleted == False)
            .group_by(InquiryInvoice.status)
        )
        result_status = await self.db.execute(status_stmt)
        by_status = {row.status: {"count": row.count, "total": row.total} for row in result_status}

        amount_stmt = select(func.sum(InquiryInvoice.total_amount)).where(
            InquiryInvoice.is_deleted == False
        )
        total_amount = await self.db.scalar(amount_stmt) or Decimal(0)

        unpaid_stmt = select(
            func.sum(InquiryInvoice.total_amount - InquiryInvoice.paid_amount)
        ).where(
            InquiryInvoice.status.in_([
                InvoiceStatus.SENT,
                InvoiceStatus.PARTIAL,
                InvoiceStatus.VIEWED
            ]),
            InquiryInvoice.is_deleted == False
        )
        unpaid = await self.db.scalar(unpaid_stmt) or Decimal(0)

        return {
            "total_invoices": total,
            "total_amount": float(total_amount),
            "unpaid_amount": float(unpaid),
            "by_status": by_status,
        }

    # ============================================================
    # UPDATE OPERATIONS
    # ============================================================

    async def update_status(
        self,
        invoice_id: UUID,
        status: str,
        note: Optional[str] = None
    ) -> Optional[InquiryInvoice]:
        """Update invoice status - TANPA flush."""
        invoice = await self.get(invoice_id)
        if not invoice or invoice.is_deleted:
            return None

        invoice.status = status
        if note:
            invoice.notes = note

        if status == InvoiceStatus.SENT and not invoice.sent_at:
            invoice.sent_at = datetime.now()
        elif status == InvoiceStatus.PAID:
            invoice.paid_at = datetime.now()
        elif status == InvoiceStatus.VIEWED:
            invoice.viewed_at = datetime.now()

        return invoice

    async def send_reminder(self, invoice_id: UUID) -> Optional[InquiryInvoice]:
        """Send reminder for invoice - TANPA flush."""
        invoice = await self.get(invoice_id)
        if not invoice or invoice.is_deleted:
            return None

        invoice.reminder_count += 1
        invoice.reminder_sent_at = datetime.now()

        return invoice

    # ============================================================
    # DELETE OPERATIONS
    # ============================================================

    async def delete(self, pk: UUID) -> bool:
        """Soft delete invoice - TANPA flush."""
        invoice = await self.get(pk)
        if not invoice:
            return False

        invoice.is_deleted = True
        invoice.deleted_at = datetime.now()
        return True

    async def hard_delete(self, pk: UUID) -> bool:
        """Hard delete invoice - TANPA flush."""
        invoice = await self.get(pk, include_deleted=True)
        if not invoice:
            return False

        await self.db.delete(invoice)
        return True

    # ============================================================
    # REMINDERS
    # ============================================================

    async def get_reminders(self, invoice_id: UUID) -> List[PaymentReminder]:
        """Get all reminders for an invoice."""
        stmt = (
            select(PaymentReminder)
            .where(
                PaymentReminder.invoice_id == invoice_id,
                PaymentReminder.is_deleted == False
            )
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
                InquiryInvoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.PARTIAL, InvoiceStatus.VIEWED]),
                InquiryInvoice.due_date <= reminder_date,
                InquiryInvoice.due_date >= now,
                InquiryInvoice.is_deleted == False
            )
            .options(selectinload(InquiryInvoice.inquiry))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    # ============================================================
    # INVOICE NUMBER GENERATION
    # ============================================================

    async def generate_invoice_number(self) -> str:
        """Generate a unique invoice number."""
        year = datetime.now().strftime("%Y")
        month = datetime.now().strftime("%m")
        day = datetime.now().strftime("%d")

        stmt = select(func.max(InquiryInvoice.invoice_number)).where(
            InquiryInvoice.invoice_number.ilike(f"INV-{year}{month}{day}-%"),
            InquiryInvoice.is_deleted == False
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
    """Repository untuk Invoice Item - TANPA FLUSH/REFRESH/COMMIT."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=InvoiceItem)

    # ============================================================
    # READ OPERATIONS
    # ============================================================

    async def get(self, pk: UUID, include_deleted: bool = False) -> Optional[InvoiceItem]:
        """Get invoice item by ID with soft delete filter."""
        stmt = select(self.model).where(self.model.id == pk)
        if not include_deleted:
            stmt = stmt.where(self.model.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_invoice(
        self,
        invoice_id: UUID,
        include_deleted: bool = False
    ) -> List[InvoiceItem]:
        """Get all items for an invoice."""
        stmt = (
            select(InvoiceItem)
            .where(InvoiceItem.invoice_id == invoice_id)
            .options(selectinload(InvoiceItem.price_list_item))
            .order_by(InvoiceItem.sort_order)
        )
        if not include_deleted:
            stmt = stmt.where(InvoiceItem.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_total_by_invoice(self, invoice_id: UUID) -> Decimal:
        """Get total amount for an invoice."""
        stmt = select(func.sum(InvoiceItem.total_price)).where(
            InvoiceItem.invoice_id == invoice_id,
            InvoiceItem.is_deleted == False
        )
        result = await self.db.execute(stmt)
        return result.scalar() or Decimal(0)

    # ============================================================
    # BULK OPERATIONS
    # ============================================================

    async def bulk_create(
        self,
        invoice_id: UUID,
        items: List[dict]
    ) -> List[InvoiceItem]:
        """Bulk create invoice items - TANPA flush."""
        created_items = []
        for item_data in items:
            item = InvoiceItem(invoice_id=invoice_id, **item_data)
            self.db.add(item)
            created_items.append(item)

        return created_items

    # ============================================================
    # DELETE OPERATIONS
    # ============================================================

    async def delete(self, pk: UUID) -> bool:
        """Soft delete invoice item - TANPA flush."""
        item = await self.get(pk)
        if not item:
            return False

        item.is_deleted = True
        item.deleted_at = datetime.now()
        return True

    async def hard_delete(self, pk: UUID) -> bool:
        """Hard delete invoice item - TANPA flush."""
        item = await self.get(pk, include_deleted=True)
        if not item:
            return False

        await self.db.delete(item)
        return True