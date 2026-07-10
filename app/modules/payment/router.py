# modules/payment/router.py

from decimal import Decimal
from uuid import UUID
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import PaymentStatus, PaymentType
from core.database import get_db
from core.base import BaseResponse
from core.dependencies import success_response, get_service
from core.exceptions import NotFoundError, ValidationError, BusinessError
from modules.payment.schemas import (
    PaymentCreate,
    PaymentUpdate,
    PaymentResponse,
    DepositCreate,
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceResponse,
    InvoiceItemCreate,
    InvoiceMarkPaid,
    InvoiceSendReminder,
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
async def get_pending_payments(
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Get all pending payments."""
    payments = await service.get_pending_payments()
    return success_response(
        [PaymentResponse.model_validate(p).model_dump() for p in payments],
        message="Pending payments retrieved successfully"
    )


@payment_router.get("/statistics", response_model=BaseResponse)
async def get_payment_statistics(
    start_date: Optional[datetime] = Query(None, description="Tanggal mulai"),
    end_date: Optional[datetime] = Query(None, description="Tanggal akhir"),
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Get payment statistics."""
    stats = await service.get_payment_statistics(start_date, end_date)
    return success_response(stats, message="Payment statistics retrieved successfully")


# =============================================================================
# 2. INVOICE ROUTES - STATIS DULUAN (SEBELUM /invoices/{invoice_id})
# =============================================================================

@payment_router.get("/invoices/generate-number", response_model=BaseResponse)
async def generate_invoice_number(
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Generate a unique invoice number."""
    number = await service.generate_invoice_number()
    return success_response(
        {"invoice_number": number},
        message="Invoice number generated"
    )


@payment_router.get("/invoices/summary", response_model=BaseResponse)
async def get_invoice_summary(
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Get invoice summary."""
    summary = await service.get_invoice_summary()
    return success_response(summary, message="Invoice summary retrieved successfully")


@payment_router.get("/invoices/outstanding", response_model=BaseResponse)
async def get_outstanding_invoices(
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Get all outstanding invoices."""
    invoices = await service.get_outstanding_invoices()
    return success_response(
        [InvoiceResponse.model_validate(inv).model_dump() for inv in invoices],
        message="Outstanding invoices retrieved successfully"
    )


@payment_router.get("/invoices/overdue", response_model=BaseResponse)
async def get_overdue_invoices(
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Get all overdue invoices."""
    invoices = await service.get_overdue_invoices()
    return success_response(
        [InvoiceResponse.model_validate(inv).model_dump() for inv in invoices],
        message="Overdue invoices retrieved successfully"
    )


@payment_router.get("/invoices/inquiry/{inquiry_id}", response_model=BaseResponse)
async def get_inquiry_invoices(
    inquiry_id: UUID,
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Get all invoices for an inquiry."""
    invoices = await service.get_invoices_by_inquiry(inquiry_id)
    return success_response(
        [InvoiceResponse.model_validate(inv).model_dump() for inv in invoices],
        message="Invoices retrieved successfully"
    )


@payment_router.get("/invoices/project/{project_id}", response_model=BaseResponse)
async def get_project_invoices(
    project_id: UUID,
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Get all invoices for a project."""
    invoices = await service.get_invoices_by_project(project_id)
    return success_response(
        [InvoiceResponse.model_validate(inv).model_dump() for inv in invoices],
        message="Invoices retrieved successfully"
    )


# =============================================================================
# 3. PAYMENT ROUTES - DENGAN PATH PARAMETER
# =============================================================================

@payment_router.post("/", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    request: PaymentCreate,
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Create a new payment."""
    try:
        payment = await service.create_payment(request)
        return success_response(
            {"id": str(payment.id)},
            message="Payment created successfully"
        )
    except (NotFoundError, ValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@payment_router.post("/deposit", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_deposit(
    request: DepositCreate,
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Create a deposit payment."""
    try:
        payment = await service.create_deposit(request)
        return success_response(
            {"id": str(payment.id)},
            message="Deposit created successfully"
        )
    except (NotFoundError, ValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@payment_router.get("/inquiry/{inquiry_id}", response_model=BaseResponse)
async def get_inquiry_payments(
    inquiry_id: UUID,
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Get all payments for an inquiry."""
    payments = await service.get_inquiry_payments(inquiry_id)
    return success_response(
        [PaymentResponse.model_validate(p).model_dump() for p in payments],
        message="Payments retrieved successfully"
    )


@payment_router.get("/project/{project_id}", response_model=BaseResponse)
async def get_project_payments(
    project_id: UUID,
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Get all payments for a project."""
    payments = await service.get_project_payments(project_id)
    return success_response(
        [PaymentResponse.model_validate(p).model_dump() for p in payments],
        message="Payments retrieved successfully"
    )


@payment_router.get("/{payment_id}", response_model=BaseResponse)
async def get_payment(
    payment_id: UUID,
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Get payment by ID."""
    payment = await service.get_payment(payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    return success_response(
        PaymentResponse.model_validate(payment).model_dump(),
        message="Payment retrieved successfully"
    )


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
                status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        return success_response(
            {"id": str(payment.id), "status": payment.status},
            message="Payment updated successfully"
        )
    except (NotFoundError, ValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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
                status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        return success_response(
            {"id": str(payment.id), "status": payment.status},
            message="Payment confirmed successfully"
        )
    except (NotFoundError, ValidationError, BusinessError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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
                status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        return success_response(
            {"id": str(payment.id), "status": "cancelled"},
            message="Payment cancelled"
        )
    except (NotFoundError, ValidationError, BusinessError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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
        return success_response(
            {"id": str(invoice.id), "invoice_number": invoice.invoice_number},
            message=f"Invoice {invoice.invoice_number} created successfully"
        )
    except (NotFoundError, ValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@payment_router.get("/invoices/{invoice_id}", response_model=BaseResponse)
async def get_invoice(
    invoice_id: UUID,
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Get invoice by ID."""
    invoice = await service.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    return success_response(
        InvoiceResponse.model_validate(invoice).model_dump(),
        message="Invoice retrieved successfully"
    )


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
                status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
        return success_response(
            {"id": str(invoice.id), "status": invoice.status},
            message="Invoice updated successfully"
        )
    except (NotFoundError, ValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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
                status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
        return success_response(
            {"id": str(invoice.id), "status": "sent"},
            message="Invoice marked as sent"
        )
    except (NotFoundError, ValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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
        return success_response(
            {"id": str(invoice.id), "status": "paid"},
            message=f"Invoice {invoice.invoice_number} marked as paid"
        )
    except (NotFoundError, ValidationError, BusinessError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@payment_router.post("/invoices/{invoice_id}/reminder", response_model=BaseResponse)
async def send_invoice_reminder(
    invoice_id: UUID,
    request: InvoiceSendReminder = Body(default_factory=dict),
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Send reminder for overdue invoice."""
    try:
        invoice = await service.send_reminder(invoice_id)
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
        return success_response(
            {"id": str(invoice.id), "reminder_count": invoice.reminder_count},
            message=f"Reminder sent (attempt {invoice.reminder_count})"
        )
    except (NotFoundError, ValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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
        return success_response(
            {"id": str(item.id)},
            message="Invoice item added successfully"
        )
    except (NotFoundError, ValidationError, BusinessError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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
                status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        return success_response(
            {"id": str(item_id)},
            message="Invoice item removed"
        )
    except (NotFoundError, ValidationError, BusinessError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

# modules/payment/router.py - Tambahkan di akhir

# =============================================================================
# 7. PROJECT FINANCIAL SUMMARY
# =============================================================================


@payment_router.get("/project/{project_id}/financial-summary", response_model=BaseResponse)
async def get_project_financial_summary(
    project_id: UUID,
    service: PaymentService = Depends(get_service(PaymentService))
):
    """Get financial summary for a project."""
    try:
        # Ambil project
        from .repository import ProjectRepository
        project_repo = ProjectRepository(service.db)
        project = await project_repo.get_with_details(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Ambil payments untuk project
        payments = await service.payment_repo.get_by_project(project_id)

        # Hitung total
        total_paid = Decimal('0')
        total_deposit = Decimal('0')
        for p in payments:
            if p.status == PaymentStatus.COMPLETED:
                if p.payment_type == PaymentType.DEPOSIT:
                    total_deposit += p.amount
                else:
                    total_paid += p.amount

        actual_cost = project.actual_cost or Decimal('0')
        remaining = max(actual_cost - total_paid - total_deposit, Decimal('0'))

        return success_response({
            "project_id": str(project.id),
            "project_name": project.name,
            "estimated_cost": float(project.estimated_cost or 0),
            "actual_cost": float(actual_cost),
            "total_deposit": float(total_deposit),
            "total_paid": float(total_paid),
            "remaining": float(remaining),
            "is_paid_off": remaining <= Decimal('0'),
            "payment_count": len(payments),
        }, message="Project financial summary retrieved successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
