# modules/payment/__init__.py
"""
Payment Module

Module untuk mengelola:
- Pembayaran (deposit, payment, refund, installment)
- Invoice
- Financial summary
- Payment reminders
- Payment reconciliation
- Invoice PDF generation
"""

from .models import (
    InquiryPayment,
    InquiryInvoice,
    InvoiceItem,
    PaymentReconciliation,
    PaymentReminder,
    InvoicePDF,
)

from .schemas import (
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
    # Summary
    InquiryFinancialSummaryResponse,
    PaymentStatisticsResponse,
    InvoiceSummaryResponse,
    # Reconciliation
    PaymentReconciliationCreate,
    PaymentReconciliationResponse,
    # Invoice PDF
    InvoicePDFResponse,
    # Reminder
    PaymentReminderCreate,
    PaymentReminderResponse,
)

from .repository import (
    PaymentRepository,
    InvoiceRepository,
    InvoiceItemRepository,
)

from .services import PaymentService
from .router import payment_router

__all__ = [
    # Models
    "InquiryPayment",
    "InquiryInvoice",
    "InvoiceItem",
    "PaymentReconciliation",
    "PaymentReminder",
    "InvoicePDF",
    # Schemas - Payment
    "PaymentCreate",
    "PaymentUpdate",
    "PaymentResponse",
    "DepositCreate",
    # Schemas - Invoice
    "InvoiceCreate",
    "InvoiceUpdate",
    "InvoiceResponse",
    "InvoiceItemCreate",
    "InvoiceItemResponse",
    "InvoiceMarkPaid",
    "InvoiceSendReminder",
    "InvoiceReminderRequest",
    # Schemas - Summary
    "InquiryFinancialSummaryResponse",
    "PaymentStatisticsResponse",
    "InvoiceSummaryResponse",
    # Schemas - Reconciliation
    "PaymentReconciliationCreate",
    "PaymentReconciliationResponse",
    # Schemas - Invoice PDF
    "InvoicePDFResponse",
    # Schemas - Reminder
    "PaymentReminderCreate",
    "PaymentReminderResponse",
    # Repositories
    "PaymentRepository",
    "InvoiceRepository",
    "InvoiceItemRepository",
    # Service
    "PaymentService",
    # Router
    "payment_router",
]
