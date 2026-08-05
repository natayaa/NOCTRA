# modules/payment/router.py
"""
Payment Router - COMPLETE

✅ Semua endpoint untuk Payment, Invoice, InvoiceItem
✅ Financial summary endpoints
✅ Reconciliation endpoints
✅ Reminder endpoints
✅ PDF generation endpoints
✅ Urutan route: STATIS dulu, baru yang ada path parameter
"""

from decimal import Decimal
from uuid import UUID
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession

from modules.settings.services import SettingsService
from core.constants import PaymentStatus, PaymentType
from core.database import get_db
from core.base import BaseResponse
from core.dependencies import success_response, get_service
from core.exceptions import NotFoundError, ValidationError, BusinessError
from modules.payment.schemas import (
    # Payment
    PaymentCreate,
    PaymentUpdate,
    PaymentResponse,
    DepositCreate,
    # Invoice
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceResponse,
    InvoiceItemCreate,
    InvoiceItemResponse,
    InvoiceMarkPaid,
    InvoiceSendReminder,
    InvoiceReminderRequest,
    # Financial Summary
    InquiryFinancialSummaryResponse,
    PaymentStatisticsResponse,
    InvoiceSummaryResponse,
    ProjectPaymentSummaryResponse,
    # Reconciliation
    PaymentReconciliationCreate,
    PaymentReconciliationUpdate,
    PaymentReconciliationResponse,
    # Reminder
    PaymentReminderCreate,
    PaymentReminderResponse,
    # PDF
    InvoicePDFResponse,
)
from modules.payment.services import PaymentService


payment_router = APIRouter(
    prefix="/api/payments",
    tags=["Payments"]
)


# =============================================================================
# ⚠️ URUTAN ROUTE PENTING!
# Route STATIS (tanpa {parameter}) HARUS di ATAS route dengan path parameter
# =============================================================================


# =============================================================================
# 1. PAYMENT ROUTES - STATIS DULUAN
# =============================================================================

@payment_router.get("/pending", response_model=BaseResponse)
async def get_pending_payments(service: PaymentService = Depends(get_service(PaymentService))):
    """Get all pending payments."""
    try:
        payments = await service.get_pending_payments()
        return success_response(
            [PaymentResponse.model_validate(p).model_dump() for p in payments],
            message="Pending payments retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@payment_router.get("/statistics", response_model=BaseResponse)
async def get_payment_statistics(
    start_date: Optional[datetime] = Query(None, description="Tanggal mulai"),
    end_date: Optional[datetime] = Query(None, description="Tanggal akhir"),
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Get payment statistics."""
    try:
        stats = await service.get_payment_statistics(start_date, end_date)
        return success_response(stats, message="Payment statistics retrieved successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@payment_router.get("/payment-methods", response_model=BaseResponse)
async def get_payment_methods(
    settings_service: SettingsService = Depends(get_service(SettingsService))
):
    """Get active payment methods dari settings."""
    try:
        methods = await settings_service.list_payment_methods(include_inactive=False)
        return success_response([
            {
                "id": str(m.id),
                "name": m.name,
                "code": m.code,
                "icon": m.icon,
                "is_active": m.is_active,
                "sort_order": m.sort_order,
                "description": m.description
            }
            for m in methods
        ], message="Payment methods retrieved")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 2. PAYMENT ROUTES - DENGAN PATH PARAMETER
# =============================================================================

@payment_router.post("/", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    request: PaymentCreate,
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Create a new payment."""
    try:
        payment = await service.create_payment(request)
        await service.db.commit()
        return success_response(
            {"id": str(payment.id)},
            message="Payment created successfully"
        )
    except (NotFoundError, ValidationError) as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@payment_router.post("/deposit", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_deposit(
    request: DepositCreate,
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Create a deposit payment."""
    try:
        payment = await service.create_deposit(request)
        await service.db.commit()
        return success_response(
            {"id": str(payment.id)},
            message="Deposit created successfully"
        )
    except (NotFoundError, ValidationError) as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@payment_router.get("/inquiry/{inquiry_id}", response_model=BaseResponse)
async def get_inquiry_payments(
    inquiry_id: UUID,
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Get all payments for an inquiry."""
    try:
        payments = await service.get_inquiry_payments(inquiry_id)
        return success_response(
            [PaymentResponse.model_validate(p).model_dump() for p in payments],
            message="Payments retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@payment_router.get("/project/{project_id}", response_model=BaseResponse)
async def get_project_payments(
    project_id: UUID,
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Get all payments for a project."""
    try:
        payments = await service.get_project_payments(project_id)
        return success_response(
            [PaymentResponse.model_validate(p).model_dump() for p in payments],
            message="Payments retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@payment_router.get("/{payment_id}", response_model=BaseResponse)
async def get_payment(
    payment_id: UUID,
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Get payment by ID."""
    try:
        payment = await service.get_payment(payment_id)
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )
        return success_response(
            PaymentResponse.model_validate(payment).model_dump(),
            message="Payment retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@payment_router.patch("/{payment_id}", response_model=BaseResponse)
async def update_payment(
    payment_id: UUID,
    request: PaymentUpdate,
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Update payment."""
    try:
        payment = await service.update_payment_status(
            payment_id,
            request.status,
            request.confirmed_by,
            request.notes
        )
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )
        await service.db.commit()
        return success_response(
            {"id": str(payment.id), "status": payment.status},
            message="Payment updated successfully"
        )
    except (NotFoundError, ValidationError) as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@payment_router.post("/{payment_id}/confirm", response_model=BaseResponse)
async def confirm_payment(
    payment_id: UUID,
    confirmed_by: str = Body("system", embed=True),
    notes: Optional[str] = Body(None, embed=True),
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Confirm a payment."""
    try:
        payment = await service.confirm_payment(payment_id, confirmed_by, notes)
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )
        await service.db.commit()
        return success_response(
            {"id": str(payment.id), "status": payment.status},
            message="Payment confirmed successfully"
        )
    except (NotFoundError, ValidationError, BusinessError) as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@payment_router.post("/{payment_id}/cancel", response_model=BaseResponse)
async def cancel_payment(
    payment_id: UUID,
    reason: Optional[str] = Body(None, embed=True),
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Cancel a pending payment."""
    try:
        payment = await service.cancel_payment(payment_id, reason)
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )
        await service.db.commit()
        return success_response(
            {"id": str(payment.id), "status": "cancelled"},
            message="Payment cancelled"
        )
    except (NotFoundError, ValidationError, BusinessError) as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# =============================================================================
# 3. INVOICE ROUTES - STATIS DULUAN (SEBELUM /invoices/{invoice_id})
# =============================================================================

@payment_router.get("/invoices/generate-number", response_model=BaseResponse)
async def generate_invoice_number(
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Generate a unique invoice number."""
    try:
        number = await service.generate_invoice_number()
        return success_response(
            {"invoice_number": number},
            message="Invoice number generated"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@payment_router.get("/invoices/summary", response_model=BaseResponse)
async def get_invoice_summary(
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Get invoice summary."""
    try:
        summary = await service.get_invoice_summary()
        return success_response(summary, message="Invoice summary retrieved successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@payment_router.get("/invoices/outstanding", response_model=BaseResponse)
async def get_outstanding_invoices(
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Get all outstanding invoices."""
    try:
        invoices = await service.get_outstanding_invoices()
        return success_response(
            [InvoiceResponse.model_validate(inv).model_dump() for inv in invoices],
            message="Outstanding invoices retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@payment_router.get("/invoices/overdue", response_model=BaseResponse)
async def get_overdue_invoices(
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Get all overdue invoices."""
    try:
        invoices = await service.get_overdue_invoices()
        return success_response(
            [InvoiceResponse.model_validate(inv).model_dump() for inv in invoices],
            message="Overdue invoices retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@payment_router.get("/invoices/inquiry/{inquiry_id}", response_model=BaseResponse)
async def get_inquiry_invoices(
    inquiry_id: UUID,
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Get all invoices for an inquiry."""
    try:
        invoices = await service.get_invoices_by_inquiry(inquiry_id)
        return success_response(
            [InvoiceResponse.model_validate(inv).model_dump() for inv in invoices],
            message="Invoices retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@payment_router.get("/invoices/project/{project_id}", response_model=BaseResponse)
async def get_project_invoices(
    project_id: UUID,
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Get all invoices for a project."""
    try:
        invoices = await service.get_invoices_by_project(project_id)
        return success_response(
            [InvoiceResponse.model_validate(inv).model_dump() for inv in invoices],
            message="Invoices retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 4. INVOICE ROUTES - DENGAN PATH PARAMETER (DI BAWAH ROUTE STATIS)
# =============================================================================

@payment_router.post("/invoices", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    request: InvoiceCreate,
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Create a new invoice."""
    try:
        invoice = await service.create_invoice(request)
        await service.db.commit()
        return success_response(
            {"id": str(invoice.id), "invoice_number": invoice.invoice_number},
            message=f"Invoice {invoice.invoice_number} created successfully"
        )
    except (NotFoundError, ValidationError) as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@payment_router.get("/invoices/{invoice_id}", response_model=BaseResponse)
async def get_invoice(
    invoice_id: UUID,
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Get invoice by ID."""
    try:
        invoice = await service.get_invoice(invoice_id)
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found"
            )
        return success_response(
            InvoiceResponse.model_validate(invoice).model_dump(),
            message="Invoice retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@payment_router.patch("/invoices/{invoice_id}", response_model=BaseResponse)
async def update_invoice(
    invoice_id: UUID,
    request: InvoiceUpdate,
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Update invoice."""
    try:
        invoice = await service.update_invoice_status(
            invoice_id,
            request.status,
            request.notes
        )
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found"
            )
        await service.db.commit()
        return success_response(
            {"id": str(invoice.id), "status": invoice.status},
            message="Invoice updated successfully"
        )
    except (NotFoundError, ValidationError) as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@payment_router.post("/invoices/{invoice_id}/send", response_model=BaseResponse)
async def send_invoice(
    invoice_id: UUID,
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Mark invoice as sent."""
    try:
        invoice = await service.mark_invoice_sent(invoice_id)
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found"
            )
        await service.db.commit()
        return success_response(
            {"id": str(invoice.id), "status": "sent"},
            message="Invoice marked as sent"
        )
    except (NotFoundError, ValidationError) as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@payment_router.post("/invoices/{invoice_id}/mark-paid", response_model=BaseResponse)
async def mark_invoice_paid(
    invoice_id: UUID,
    request: InvoiceMarkPaid,
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Mark invoice as paid."""
    try:
        invoice = await service.mark_invoice_paid(
            invoice_id,
            request.payment_method,
            request.reference_number,
            request.notes
        )
        await service.db.commit()
        return success_response(
            {"id": str(invoice.id), "status": "paid"},
            message=f"Invoice {invoice.invoice_number} marked as paid"
        )
    except (NotFoundError, ValidationError, BusinessError) as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@payment_router.post("/invoices/{invoice_id}/reminder", response_model=BaseResponse)
async def send_invoice_reminder(
    invoice_id: UUID,
    request: InvoiceSendReminder = Body(default_factory=InvoiceSendReminder),
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Send reminder for overdue invoice."""
    try:
        reminder_request = InvoiceReminderRequest(
            note=request.note,
            sent_via=request.sent_via
        )
        reminder = await service.send_invoice_reminder(invoice_id, reminder_request)
        if not reminder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found"
            )
        await service.db.commit()
        
        invoice = await service.get_invoice(invoice_id)
        return success_response(
            {
                "id": str(reminder.id),
                "invoice_id": str(invoice_id),
                "reminder_count": invoice.reminder_count if invoice else 0,
                "sent_via": reminder.sent_via,
                "recipient": reminder.recipient,
                "status": reminder.status
            },
            message=f"Reminder sent (attempt {invoice.reminder_count if invoice else 0})"
        )
    except (NotFoundError, ValidationError) as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# =============================================================================
# 5. INVOICE ITEMS ROUTES
# =============================================================================

@payment_router.post("/invoices/{invoice_id}/items", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def add_invoice_item(
    invoice_id: UUID,
    request: InvoiceItemCreate,
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Add an item to invoice."""
    try:
        item = await service.add_invoice_item(invoice_id, request)
        await service.db.commit()
        return success_response(
            {"id": str(item.id)},
            message="Invoice item added successfully"
        )
    except (NotFoundError, ValidationError, BusinessError) as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@payment_router.delete("/invoices/items/{item_id}", response_model=BaseResponse)
async def remove_invoice_item(
    item_id: UUID,
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Remove an item from invoice."""
    try:
        result = await service.remove_invoice_item(item_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found"
            )
        await service.db.commit()
        return success_response(
            {"id": str(item_id)},
            message="Invoice item removed"
        )
    except (NotFoundError, ValidationError, BusinessError) as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# =============================================================================
# 6. FINANCIAL SUMMARY ROUTES
# =============================================================================

@payment_router.get("/inquiry/{inquiry_id}/financial-summary", response_model=BaseResponse)
async def get_inquiry_financial_summary(
    inquiry_id: UUID,
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Get comprehensive financial summary for an inquiry."""
    try:
        summary = await service.get_inquiry_financial_summary(inquiry_id)
        return success_response(summary, message="Financial summary retrieved successfully")
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@payment_router.get("/project/{project_id}/financial-summary", response_model=BaseResponse)
async def get_project_financial_summary(
    project_id: UUID,
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Get financial summary for a project."""
    try:
        summary = await service.get_project_financial_summary(project_id)
        return success_response(summary, message="Project financial summary retrieved successfully")
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# =============================================================================
# 7. RECONCILIATION ROUTES
# =============================================================================

@payment_router.post("/reconciliations", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_reconciliation(
    request: PaymentReconciliationCreate,
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Create payment reconciliation."""
    try:
        reconciliation = await service.create_reconciliation(request.payment_id, request)
        await service.db.commit()
        return success_response(
            {"id": str(reconciliation.id)},
            message="Reconciliation created successfully"
        )
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@payment_router.get("/reconciliations/payment/{payment_id}", response_model=BaseResponse)
async def get_reconciliation(
    payment_id: UUID,
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Get reconciliation for a payment."""
    try:
        reconciliation = await service.get_reconciliation(payment_id)
        if not reconciliation:
            return success_response(
                None,
                message="No reconciliation found for this payment"
            )
        return success_response(
            PaymentReconciliationResponse.model_validate(reconciliation).model_dump(),
            message="Reconciliation retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@payment_router.patch("/reconciliations/{reconciliation_id}", response_model=BaseResponse)
async def update_reconciliation(
    reconciliation_id: UUID,
    request: PaymentReconciliationUpdate,
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Update reconciliation status."""
    try:
        reconciliation = await service.update_reconciliation_status(
            reconciliation_id,
            request.status,
            request.notes
        )
        if not reconciliation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reconciliation not found"
            )
        await service.db.commit()
        return success_response(
            {"id": str(reconciliation.id), "status": reconciliation.status},
            message="Reconciliation updated successfully"
        )
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# =============================================================================
# 8. REMINDER ROUTES
# =============================================================================

@payment_router.post("/reminders", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    request: PaymentReminderCreate,
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Create a payment reminder."""
    try:
        # Convert to InvoiceReminderRequest
        reminder_request = InvoiceReminderRequest(
            note=request.message,
            sent_via=request.sent_via
        )
        reminder = await service.send_invoice_reminder(request.invoice_id, reminder_request)
        if not reminder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found"
            )
        await service.db.commit()
        return success_response(
            {"id": str(reminder.id)},
            message="Reminder created successfully"
        )
    except (NotFoundError, ValidationError, BusinessError) as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@payment_router.get("/invoices/{invoice_id}/reminders", response_model=BaseResponse)
async def get_invoice_reminders(
    invoice_id: UUID,
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Get all reminders for an invoice."""
    try:
        reminders = await service.get_invoice_reminders(invoice_id)
        return success_response(
            [PaymentReminderResponse.model_validate(r).model_dump() for r in reminders],
            message="Reminders retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@payment_router.post("/reminders/auto", response_model=BaseResponse)
async def send_auto_reminders(
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Send automatic reminders for upcoming due dates."""
    try:
        reminders = await service.send_auto_reminders()
        await service.db.commit()
        return success_response(
            {"sent": len(reminders)},
            message=f"Sent {len(reminders)} reminders"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 9. PDF ROUTES
# =============================================================================

@payment_router.post("/invoices/{invoice_id}/pdf", response_model=BaseResponse)
async def generate_invoice_pdf(
    invoice_id: UUID,
    generated_by: Optional[str] = Body("system", embed=True),
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Generate PDF for invoice."""
    try:
        pdf = await service.generate_invoice_pdf(invoice_id, generated_by)
        await service.db.commit()
        return success_response(
            {
                "id": str(pdf.id),
                "file_path": pdf.file_path,
                "file_name": pdf.file_name,
                "version": pdf.version
            },
            message="PDF generated successfully"
        )
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@payment_router.get("/invoices/{invoice_id}/pdfs", response_model=BaseResponse)
async def get_invoice_pdfs(
    invoice_id: UUID,
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Get all PDFs for an invoice."""
    try:
        pdfs = await service.get_invoice_pdfs(invoice_id)
        return success_response(
            [InvoicePDFResponse.model_validate(p).model_dump() for p in pdfs],
            message="PDFs retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))