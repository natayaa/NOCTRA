# modules/payment/services.py
"""
Payment Service - FIXED Decimal Operations
"""
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import NotFoundError, ValidationError, BusinessError
from core.constants import PaymentStatus, InvoiceStatus, PaymentType
from modules.payment.models import (
    InquiryPayment,
    InquiryInvoice,
    InvoiceItem,
    PaymentReminder,
    PaymentReconciliation,
    InvoicePDF,
)
from modules.payment.repository import (
    PaymentRepository,
    InvoiceRepository,
    InvoiceItemRepository
)
from modules.payment.schemas import (
    PaymentCreate,
    PaymentUpdate,
    DepositCreate,
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceItemCreate,
    InvoiceReminderRequest,
    PaymentReconciliationCreate,
)


class PaymentService:
    """Service untuk Payment management."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.payment_repo = PaymentRepository(db)
        self.invoice_repo = InvoiceRepository(db)
        self.item_repo = InvoiceItemRepository(db)

    # =========================================================================
    # Repository Accessors (Lazy import untuk menghindari circular)
    # =========================================================================

    @property
    def inquiry_repo(self):
        """Lazy import untuk InquiryRepository."""
        from modules.inquiry.repository import InquiryRepository
        if not hasattr(self, '_inquiry_repo'):
            self._inquiry_repo = InquiryRepository(self.db)
        return self._inquiry_repo

    @property
    def project_repo(self):
        """Lazy import untuk ProjectRepository."""
        from modules.projects.repository import ProjectRepository
        if not hasattr(self, '_project_repo'):
            self._project_repo = ProjectRepository(self.db)
        return self._project_repo

    # =========================================================================
    # ✅ HELPER: Konversi ke Decimal
    # =========================================================================

    def _to_decimal(self, value) -> Decimal:
        """Safe conversion to Decimal."""
        if value is None:
            return Decimal('0')
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        if isinstance(value, str):
            return Decimal(value)
        return Decimal('0')

    def _calculate_item_totals(self, quantity: Decimal, unit_price: Decimal,
                               tax_rate: Decimal, discount_percentage: Decimal) -> dict:
        """
        Calculate item totals with proper Decimal operations.

        ✅ FIXED: Semua operasi menggunakan Decimal
        """
        # Konversi semua ke Decimal
        qty = self._to_decimal(quantity)
        price = self._to_decimal(unit_price)
        tax = self._to_decimal(tax_rate)
        discount = self._to_decimal(discount_percentage)

        # ✅ FIX: Decimal division
        total = qty * price
        tax_amount = total * (tax / Decimal('100'))
        subtotal_with_tax = total + tax_amount
        discount_amount = subtotal_with_tax * (discount / Decimal('100'))
        final_total = subtotal_with_tax - discount_amount

        return {
            "total_price": total,
            "tax_amount": tax_amount,
            "discount_amount": discount_amount,
            "final_total": final_total
        }

    # =========================================================================
    # Payment Management
    # =========================================================================

    async def create_payment(self, data: PaymentCreate) -> InquiryPayment:
        """Create a new payment."""
        inquiry = await self.inquiry_repo.get(data.inquiry_id)
        if not inquiry:
            raise NotFoundError(f"Inquiry {data.inquiry_id} not found")

        # ✅ FIX: Konversi amount ke Decimal
        amount = self._to_decimal(data.amount)
        if amount <= Decimal('0'):
            raise ValidationError("Amount must be greater than 0")

        if data.invoice_id:
            invoice = await self.invoice_repo.get(data.invoice_id)
            if not invoice:
                raise NotFoundError(f"Invoice {data.invoice_id} not found")
            if invoice.status == InvoiceStatus.PAID:
                raise ValidationError("Cannot add payment to paid invoice")

        # ✅ Gunakan repository.create (tanpa flush/commit)
        payment_data = data.model_dump()
        payment_data["amount"] = amount  # ✅ Pastikan Decimal
        payment_data["paid_at"] = payment_data.get("paid_at") or datetime.now()
        payment_data["status"] = PaymentStatus.PENDING

        payment = await self.payment_repo.create(payment_data)

        await self.inquiry_repo.add_activity(
            data.inquiry_id,
            f"{data.payment_type.title()} created: Rp {amount:,.2f} via {data.payment_method}",
            "payment_created",
            performed_by="system"
        )

        return payment

    async def create_deposit(self, data: DepositCreate) -> InquiryPayment:
        """Create a deposit payment."""
        payment_data = PaymentCreate(
            inquiry_id=data.inquiry_id,
            project_id=data.project_id,
            payment_type=PaymentType.DEPOSIT,
            amount=self._to_decimal(data.amount),  # ✅ FIX
            payment_method=data.payment_method,
            reference_number=data.reference_number,
            notes=data.notes,
            paid_at=datetime.now()
        )
        return await self.create_payment(payment_data)

    async def get_payment(self, payment_id: UUID) -> Optional[InquiryPayment]:
        """Get payment by ID."""
        return await self.payment_repo.get(payment_id)

    async def get_inquiry_payments(self, inquiry_id: UUID) -> List[InquiryPayment]:
        """Get all payments for an inquiry."""
        return await self.payment_repo.get_by_inquiry(inquiry_id)

    async def get_project_payments(self, project_id: UUID) -> List[InquiryPayment]:
        """Get all payments for a project."""
        return await self.payment_repo.get_by_project(project_id)

    async def get_pending_payments(self) -> List[InquiryPayment]:
        """Get all pending payments."""
        return await self.payment_repo.get_pending_payments()

    async def update_payment_status(
        self,
        payment_id: UUID,
        status: str,
        confirmed_by: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Optional[InquiryPayment]:
        """Update payment status."""
        if not payment_id:
            raise ValidationError("Payment ID is required")

        payment = await self.payment_repo.get(payment_id)
        if not payment:
            raise NotFoundError(f"Payment {payment_id} not found")

        # Update status via repository
        updated = await self.payment_repo.update_payment_status(
            payment_id, status, confirmed_by, notes
        )

        if updated and status == PaymentStatus.COMPLETED:
            # Update financials
            await self.payment_repo.update_inquiry_financials(payment.inquiry_id)
            if payment.project_id:
                await self.payment_repo.update_project_financials(payment.project_id)
            if payment.invoice_id:
                await self.payment_repo.update_invoice_payment(payment.invoice_id)

            await self.inquiry_repo.add_activity(
                payment.inquiry_id,
                f"Payment confirmed: Rp {payment.amount:,.2f} by {confirmed_by or 'system'}",
                "payment_confirmed",
                performed_by=confirmed_by or "system"
            )

        return updated

    async def confirm_payment(
        self,
        payment_id: UUID,
        confirmed_by: str,
        notes: Optional[str] = None
    ) -> Optional[InquiryPayment]:
        """Confirm a payment (mark as completed)."""
        if not payment_id:
            raise ValidationError("Payment ID is required")

        return await self.update_payment_status(
            payment_id,
            PaymentStatus.COMPLETED,
            confirmed_by,
            notes
        )

    async def cancel_payment(
        self,
        payment_id: UUID,
        reason: Optional[str] = None
    ) -> Optional[InquiryPayment]:
        """Cancel a pending payment."""
        payment = await self.payment_repo.get(payment_id)
        if not payment:
            raise NotFoundError(f"Payment {payment_id} not found")

        if payment.status == PaymentStatus.COMPLETED:
            raise BusinessError("Cannot cancel a completed payment")

        return await self.payment_repo.cancel_payment(payment_id, reason)

    # =========================================================================
    # Invoice Management
    # =========================================================================

    async def create_invoice(self, data: InvoiceCreate) -> InquiryInvoice:
        """
        Create a new invoice.

        ✅ FIXED: Semua operasi Decimal menggunakan Decimal division
        """
        # Validate inquiry exists
        inquiry = await self.inquiry_repo.get(data.inquiry_id)
        if not inquiry:
            raise NotFoundError(f"Inquiry {data.inquiry_id} not found")

        # Check invoice number uniqueness
        existing = await self.invoice_repo.get_by_number(data.invoice_number)
        if existing:
            raise ValidationError(
                f"Invoice number '{data.invoice_number}' already exists")

        # ✅ FIX: Initialize Decimal dengan benar
        subtotal_amount = Decimal('0')
        tax_amount = Decimal('0')
        discount_amount = Decimal('0')

        # ✅ FIX: Calculate totals dengan Decimal
        for item_data in data.items:
            # Konversi ke Decimal
            quantity = self._to_decimal(item_data.quantity)
            unit_price = self._to_decimal(item_data.unit_price)
            tax_rate = self._to_decimal(item_data.tax_rate)
            discount_percentage = self._to_decimal(
                item_data.discount_percentage or 0)

            # ✅ FIX: Decimal division
            item_total = quantity * unit_price
            item_tax = item_total * (tax_rate / Decimal('100'))
            item_subtotal = item_total + item_tax
            item_discount = item_subtotal * \
                (discount_percentage / Decimal('100'))

            subtotal_amount += item_total
            tax_amount += item_tax
            discount_amount += item_discount

        total_amount = subtotal_amount + tax_amount - discount_amount

        # ✅ CREATE INVOICE
        invoice_data = {
            "inquiry_id": data.inquiry_id,
            "project_id": data.project_id,
            "invoice_number": data.invoice_number,
            "invoice_date": data.invoice_date or datetime.now(),
            "due_date": data.due_date,
            "subtotal_amount": subtotal_amount,
            "total_amount": total_amount,
            "paid_amount": Decimal('0'),
            "tax_amount": tax_amount,
            "discount_amount": discount_amount,
            "notes": data.notes,
            "status": InvoiceStatus.DRAFT,
            "payment_terms": data.payment_terms
        }

        invoice = await self.invoice_repo.create(invoice_data)

        # ✅ FLUSH untuk mendapatkan ID
        await self.db.flush()
        await self.db.refresh(invoice)

        # ✅ CREATE ITEMS dengan invoice.id yang valid
        for idx, item_data in enumerate(data.items):
            # Konversi ke Decimal
            quantity = self._to_decimal(item_data.quantity)
            unit_price = self._to_decimal(item_data.unit_price)
            tax_rate = self._to_decimal(item_data.tax_rate)
            discount_percentage = self._to_decimal(
                item_data.discount_percentage or 0)

            # ✅ FIX: Decimal division
            item_total = quantity * unit_price
            item_tax = item_total * (tax_rate / Decimal('100'))
            item_subtotal = item_total + item_tax
            item_discount = item_subtotal * \
                (discount_percentage / Decimal('100'))

            item = InvoiceItem(
                invoice_id=invoice.id,
                description=item_data.description,
                quantity=quantity,
                unit=item_data.unit,
                unit_price=unit_price,
                total_price=item_total,
                tax_rate=tax_rate,
                tax_amount=item_tax,
                discount_percentage=discount_percentage,
                discount_amount=item_discount,
                notes=item_data.notes,
                sort_order=item_data.sort_order or idx,
                price_list_item_id=getattr(
                    item_data, 'price_list_item_id', None)
            )
            self.db.add(item)

        # Add activity
        await self.inquiry_repo.add_activity(
            data.inquiry_id,
            f"Invoice created: {data.invoice_number} (Rp {total_amount:,.2f})",
            "invoice_created",
            performed_by="system"
        )

        await self.db.flush()
        await self.db.refresh(invoice)

        return await self.invoice_repo.get_with_details(invoice.id)

    async def get_invoice(self, invoice_id: UUID) -> Optional[InquiryInvoice]:
        """Get invoice by ID."""
        return await self.invoice_repo.get_with_details(invoice_id)

    async def get_invoice_by_number(self, invoice_number: str) -> Optional[InquiryInvoice]:
        """Get invoice by number."""
        return await self.invoice_repo.get_by_number(invoice_number)

    async def get_invoices_by_inquiry(self, inquiry_id: UUID) -> List[InquiryInvoice]:
        """Get all invoices for an inquiry."""
        return await self.invoice_repo.get_by_inquiry(inquiry_id)

    async def get_invoices_by_project(self, project_id: UUID) -> List[InquiryInvoice]:
        """Get all invoices for a project."""
        return await self.invoice_repo.get_by_project(project_id)

    async def get_outstanding_invoices(self) -> List[InquiryInvoice]:
        """Get all outstanding invoices."""
        return await self.invoice_repo.get_outstanding_invoices()

    async def get_overdue_invoices(self) -> List[InquiryInvoice]:
        """Get all overdue invoices."""
        return await self.invoice_repo.get_overdue_invoices()

    async def update_invoice_status(
        self,
        invoice_id: UUID,
        status: str,
        notes: Optional[str] = None
    ) -> Optional[InquiryInvoice]:
        """Update invoice status."""
        invoice = await self.invoice_repo.update_status(invoice_id, status, notes)
        if not invoice:
            raise NotFoundError(f"Invoice {invoice_id} not found")

        await self.inquiry_repo.add_activity(
            invoice.inquiry_id,
            f"Invoice {invoice.invoice_number} status updated to {status}",
            "invoice_update",
            performed_by="system"
        )

        return invoice

    async def mark_invoice_sent(self, invoice_id: UUID) -> Optional[InquiryInvoice]:
        """Mark invoice as sent."""
        return await self.update_invoice_status(invoice_id, InvoiceStatus.SENT)

    async def mark_invoice_paid(
        self,
        invoice_id: UUID,
        payment_method: str,
        reference_number: Optional[str] = None,
        notes: Optional[str] = None
    ) -> InquiryInvoice:
        """Mark invoice as paid."""
        if not invoice_id:
            raise ValidationError("Invoice ID is required")

        invoice = await self.invoice_repo.get_with_details(invoice_id)
        if not invoice:
            raise NotFoundError(f"Invoice {invoice_id} not found")

        if invoice.status == InvoiceStatus.PAID:
            raise BusinessError("Invoice already paid")

        remaining = invoice.remaining_amount
        if remaining <= Decimal('0'):
            raise BusinessError("Invoice already fully paid")

        # Create payment record
        payment = await self.create_payment(
            PaymentCreate(
                inquiry_id=invoice.inquiry_id,
                project_id=invoice.project_id,
                invoice_id=invoice.id,
                payment_type=PaymentType.PAYMENT,
                amount=remaining,  # ✅ Sudah Decimal
                payment_method=payment_method,
                reference_number=reference_number,
                notes=notes or f"Payment for invoice {invoice.invoice_number}",
                paid_at=datetime.now()
            )
        )

        # Confirm payment
        await self.confirm_payment(
            payment.id,
            confirmed_by="system",
            notes="Auto-confirmed for invoice payment"
        )

        await self.db.flush()
        return await self.invoice_repo.get_with_details(invoice.id)

    async def send_reminder(self, invoice_id: UUID) -> Optional[InquiryInvoice]:
        """Send reminder for overdue invoice."""
        invoice = await self.invoice_repo.send_reminder(invoice_id)
        if not invoice:
            raise NotFoundError(f"Invoice {invoice_id} not found")

        await self.inquiry_repo.add_activity(
            invoice.inquiry_id,
            f"Reminder sent for invoice {invoice.invoice_number} (attempt {invoice.reminder_count})",
            "invoice_reminder",
            performed_by="system"
        )

        return invoice

    async def generate_invoice_number(self) -> str:
        """Generate a unique invoice number."""
        return await self.invoice_repo.generate_invoice_number()

    # =========================================================================
    # Invoice Items
    # =========================================================================

    async def add_invoice_item(
        self,
        invoice_id: UUID,
        item_data: InvoiceItemCreate
    ) -> InvoiceItem:
        """
        Add an item to invoice.

        ✅ FIXED: Decimal operations
        """
        invoice = await self.invoice_repo.get(invoice_id)
        if not invoice:
            raise NotFoundError(f"Invoice {invoice_id} not found")

        if invoice.status == InvoiceStatus.PAID:
            raise BusinessError("Cannot add items to paid invoice")

        # Konversi ke Decimal
        quantity = self._to_decimal(item_data.quantity)
        unit_price = self._to_decimal(item_data.unit_price)
        tax_rate = self._to_decimal(item_data.tax_rate)
        discount_percentage = self._to_decimal(
            item_data.discount_percentage or 0)

        # ✅ FIX: Decimal division
        item_total = quantity * unit_price
        item_tax = item_total * (tax_rate / Decimal('100'))
        item_subtotal = item_total + item_tax
        item_discount = item_subtotal * (discount_percentage / Decimal('100'))

        item = InvoiceItem(
            invoice_id=invoice_id,
            description=item_data.description,
            quantity=quantity,
            unit=item_data.unit,
            unit_price=unit_price,
            total_price=item_total,
            tax_rate=tax_rate,
            tax_amount=item_tax,
            discount_percentage=discount_percentage,
            discount_amount=item_discount,
            notes=item_data.notes,
            sort_order=item_data.sort_order,
            price_list_item_id=getattr(item_data, 'price_list_item_id', None)
        )
        self.db.add(item)

        # Update invoice total
        invoice.subtotal_amount += item_total
        invoice.tax_amount += item_tax
        invoice.discount_amount += item_discount
        invoice.total_amount = invoice.subtotal_amount + \
            invoice.tax_amount - invoice.discount_amount

        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def remove_invoice_item(self, item_id: UUID) -> bool:
        """Remove an item from invoice."""
        item = await self.item_repo.get(item_id)
        if not item:
            return False

        invoice = await self.invoice_repo.get(item.invoice_id)
        if invoice and invoice.status == InvoiceStatus.PAID:
            raise BusinessError("Cannot remove items from paid invoice")

        # Update invoice total
        if invoice:
            invoice.subtotal_amount -= item.total_price
            invoice.tax_amount -= item.tax_amount
            invoice.discount_amount -= item.discount_amount
            invoice.total_amount = invoice.subtotal_amount + \
                invoice.tax_amount - invoice.discount_amount

        await self.db.delete(item)
        await self.db.flush()
        return True

    # =========================================================================
    # Financial Summary
    # =========================================================================

    async def get_inquiry_financial_summary(
        self,
        inquiry_id: UUID
    ) -> dict:
        """Get comprehensive financial summary for an inquiry."""
        if not inquiry_id:
            raise ValidationError("Inquiry ID is required")

        inquiry = await self.inquiry_repo.get_with_details(inquiry_id)
        if not inquiry:
            raise NotFoundError(f"Inquiry {inquiry_id} not found")

        # Get payments
        payments = await self.payment_repo.get_by_inquiry(inquiry_id)

        # Get invoices
        invoices = await self.invoice_repo.get_by_inquiry(inquiry_id)

        # Calculate totals with Decimal
        total_deposit = Decimal('0')
        total_paid = Decimal('0')
        total_pending = Decimal('0')

        for p in payments:
            amount = self._to_decimal(p.amount)
            if p.status == PaymentStatus.COMPLETED:
                if p.payment_type == PaymentType.DEPOSIT:
                    total_deposit += amount
                else:
                    total_paid += amount
            elif p.status == PaymentStatus.PENDING:
                total_pending += amount

        estimated_budget = self._to_decimal(inquiry.estimated_budget)

        total_cost = Decimal('0')
        if inquiry.project:
            total_cost = self._to_decimal(inquiry.project.actual_cost)

        remaining = max(total_cost - total_paid - total_deposit, Decimal('0'))

        return {
            "inquiry_id": str(inquiry.id),
            "customer_name": inquiry.customer_name,
            "vehicle_info": f"{inquiry.vehicle_brand} {inquiry.vehicle_model}",
            "estimated_budget": float(estimated_budget),
            "total_cost": float(total_cost),
            "total_deposit": float(total_deposit),
            "total_paid": float(total_paid),
            "total_pending": float(total_pending),
            "remaining_payment": float(remaining),
            "deposit_paid": total_deposit > Decimal('0'),
            "is_paid_off": (total_paid + total_deposit) >= total_cost if total_cost > Decimal('0') else False,
            "has_invoices": len(invoices) > 0,
            "payments": [self._serialize_payment(p) for p in payments],
            "invoices": [self._serialize_invoice(inv) for inv in invoices]
        }

    async def get_payment_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> dict:
        """Get payment statistics."""
        return await self.payment_repo.get_statistics(start_date, end_date)

    async def get_invoice_summary(self) -> dict:
        """Get summary of all invoices."""
        return await self.invoice_repo.get_invoice_summary()

    # =========================================================================
    # Payment Reminder
    # =========================================================================

    async def send_invoice_reminder(
        self,
        invoice_id: UUID,
        data: InvoiceReminderRequest
    ) -> Optional[PaymentReminder]:
        """Send reminder for invoice."""
        invoice = await self.invoice_repo.get_with_details(invoice_id)
        if not invoice:
            raise NotFoundError(f"Invoice {invoice_id} not found")

        inquiry = invoice.inquiry
        if not inquiry:
            raise BusinessError("Inquiry not found for invoice")

        recipient = inquiry.customer_email or inquiry.customer_phone_number
        if not recipient:
            raise BusinessError("No contact information found for customer")

        remaining = self._to_decimal(invoice.remaining_amount)

        subject = f"Reminder: Invoice {invoice.invoice_number} is due soon"
        message = (
            f"Dear {inquiry.customer_name},\n\n"
            f"This is a reminder that invoice {invoice.invoice_number} "
            f"amounting to Rp {remaining:,.2f} "
            f"is due on {invoice.due_date.strftime('%d %B %Y') if invoice.due_date else 'soon'}.\n\n"
            f"Please make the payment to avoid any interruption.\n\n"
            f"Thank you."
        )

        if data.note:
            message += f"\n\nNote: {data.note}"

        reminder = PaymentReminder(
            invoice_id=invoice_id,
            reminder_type="manual",
            sent_at=datetime.now(),
            sent_via=data.sent_via,
            recipient=recipient,
            subject=subject,
            message=message,
            status="sent"
        )
        self.db.add(reminder)
        await self.db.flush()
        await self.db.refresh(reminder)

        # Update invoice
        invoice.reminder_count += 1
        invoice.reminder_sent_at = datetime.now()
        await self.db.flush()

        await self.inquiry_repo.add_activity(
            invoice.inquiry_id,
            f"Reminder sent for invoice {invoice.invoice_number} (attempt {invoice.reminder_count})",
            "invoice_reminder",
            performed_by="system"
        )

        return reminder

    async def send_auto_reminders(self) -> List[PaymentReminder]:
        """Send automatic reminders for upcoming due dates."""
        invoices = await self.invoice_repo.get_invoices_needing_reminder()
        reminders = []

        for invoice in invoices:
            try:
                reminder = await self.send_invoice_reminder(
                    invoice.id,
                    InvoiceReminderRequest(
                        note="Auto-generated reminder",
                        sent_via="email"
                    )
                )
                if reminder:
                    reminders.append(reminder)
            except Exception as e:
                print(
                    f"Failed to send reminder for invoice {invoice.id}: {str(e)}")

        return reminders

    async def get_invoice_reminders(self, invoice_id: UUID) -> List[PaymentReminder]:
        """Get all reminders for an invoice."""
        return await self.invoice_repo.get_reminders(invoice_id)

    # =========================================================================
    # Payment Reconciliation
    # =========================================================================

    async def create_reconciliation(
        self,
        payment_id: UUID,
        data: PaymentReconciliationCreate
    ) -> PaymentReconciliation:
        """Create payment reconciliation."""
        payment = await self.payment_repo.get(payment_id)
        if not payment:
            raise NotFoundError(f"Payment {payment_id} not found")

        reconciliation = PaymentReconciliation(
            payment_id=payment_id,
            bank_name=data.bank_name,
            bank_account=data.bank_account,
            reference_number=data.reference_number,
            reconciled_at=data.reconciled_at,
            reconciled_by=data.reconciled_by,
            status="pending",
            notes=data.notes
        )
        self.db.add(reconciliation)
        await self.db.flush()
        await self.db.refresh(reconciliation)
        return reconciliation

    async def get_reconciliation(self, payment_id: UUID) -> Optional[PaymentReconciliation]:
        """Get reconciliation for a payment."""
        return await self.payment_repo.get_reconciliation(payment_id)

    async def update_reconciliation_status(
        self,
        reconciliation_id: UUID,
        status: str,
        notes: Optional[str] = None
    ) -> Optional[PaymentReconciliation]:
        """Update reconciliation status."""
        reconciliation = await self.payment_repo.get(reconciliation_id)
        if not reconciliation:
            raise NotFoundError(
                f"Reconciliation {reconciliation_id} not found")

        reconciliation.status = status
        if notes:
            reconciliation.notes = notes

        await self.db.flush()
        await self.db.refresh(reconciliation)
        return reconciliation

    # =========================================================================
    # Invoice PDF
    # =========================================================================

    async def generate_invoice_pdf(
        self,
        invoice_id: UUID,
        generated_by: Optional[str] = None
    ) -> InvoicePDF:
        """Generate PDF for invoice."""
        invoice = await self.invoice_repo.get_with_details(invoice_id)
        if not invoice:
            raise NotFoundError(f"Invoice {invoice_id} not found")

        file_path = f"invoices/{invoice.invoice_number}.pdf"
        file_name = f"{invoice.invoice_number}.pdf"

        pdf = InvoicePDF(
            invoice_id=invoice_id,
            file_path=file_path,
            file_name=file_name,
            generated_by=generated_by or "system",
            version=1
        )
        self.db.add(pdf)
        await self.db.flush()
        await self.db.refresh(pdf)

        # Update invoice file_path
        invoice.file_path = file_path
        await self.db.flush()

        return pdf

    async def get_invoice_pdfs(self, invoice_id: UUID) -> List[InvoicePDF]:
        """Get all PDFs for an invoice."""
        return await self.invoice_repo.get_pdfs(invoice_id)

    # =========================================================================
    # Helpers
    # =========================================================================

    def _serialize_payment(self, payment: InquiryPayment) -> dict:
        """Serialize payment to dict."""
        return {
            "id": str(payment.id),
            "payment_type": payment.payment_type,
            "amount": float(payment.amount),
            "payment_method": payment.payment_method,
            "reference_number": payment.reference_number,
            "status": payment.status,
            "notes": payment.notes,
            "paid_at": payment.paid_at.isoformat() if payment.paid_at else None
        }

    def _serialize_invoice(self, invoice: InquiryInvoice) -> dict:
        """Serialize invoice to dict."""
        return {
            "id": str(invoice.id),
            "invoice_number": invoice.invoice_number,
            "total_amount": float(invoice.total_amount),
            "paid_amount": float(invoice.paid_amount),
            "remaining_amount": float(invoice.remaining_amount),
            "status": invoice.status,
            "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
            "is_overdue": invoice.is_overdue
        }
