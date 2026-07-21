# modules/payment/__init__.py
"""
Payment Module

Module untuk mengelola:
- Payment management (CRUD, confirm, cancel)
- Invoice management (CRUD, send, mark paid)
- Invoice items management
- Payment reconciliation
- Payment reminders (auto & manual)
- Invoice PDF generation
- Financial summary (inquiry & project)
- Integration dengan Inquiry, Project, Price List, Settings

✅ Soft delete support
✅ Decimal operations fixed
✅ Integration with Settings for tax
✅ Integration with Price List for items
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

from .repository import (
    PaymentRepository,
    InvoiceRepository,
    InvoiceItemRepository,
)

from .services import PaymentService
from .router import payment_router

__all__ = [
    # ============ Models ============
    "InquiryPayment",
    "InquiryInvoice",
    "InvoiceItem",
    "PaymentReconciliation",
    "PaymentReminder",
    "InvoicePDF",
    
    # ============ Schemas - Payment ============
    "PaymentCreate",
    "PaymentUpdate",
    "PaymentResponse",
    "DepositCreate",
    
    # ============ Schemas - Invoice ============
    "InvoiceCreate",
    "InvoiceUpdate",
    "InvoiceResponse",
    "InvoiceItemCreate",
    "InvoiceItemResponse",
    "InvoiceMarkPaid",
    "InvoiceSendReminder",
    "InvoiceReminderRequest",
    
    # ============ Schemas - Financial Summary ============
    "InquiryFinancialSummaryResponse",
    "PaymentStatisticsResponse",
    "InvoiceSummaryResponse",
    "ProjectPaymentSummaryResponse",
    
    # ============ Schemas - Reconciliation ============
    "PaymentReconciliationCreate",
    "PaymentReconciliationUpdate",
    "PaymentReconciliationResponse",
    
    # ============ Schemas - Reminder ============
    "PaymentReminderCreate",
    "PaymentReminderResponse",
    
    # ============ Schemas - PDF ============
    "InvoicePDFResponse",
    
    # ============ Repositories ============
    "PaymentRepository",
    "InvoiceRepository",
    "InvoiceItemRepository",
    
    # ============ Service ============
    "PaymentService",
    
    # ============ Router ============
    "payment_router",
]
