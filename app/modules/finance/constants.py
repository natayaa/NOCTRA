"""Finance module vocabulary."""

from __future__ import annotations

from enum import StrEnum


# ════════════════════════════════════════════════════════════════
# CHART OF ACCOUNTS
# ════════════════════════════════════════════════════════════════

class AccountType(StrEnum):
    ASSET = "ASSET"           # bank, cash, receivables
    LIABILITY = "LIABILITY"   # payables, loans
    EQUITY = "EQUITY"         # owner's equity
    REVENUE = "REVENUE"       # sales income
    EXPENSE = "EXPENSE"       # costs, operating expenses


ACCOUNT_TYPES: list[str] = [t.value for t in AccountType]

ACCOUNT_TYPE_LABELS: dict[str, str] = {
    AccountType.ASSET.value:     "Asset",
    AccountType.LIABILITY.value: "Liability",
    AccountType.EQUITY.value:    "Equity",
    AccountType.REVENUE.value:   "Revenue",
    AccountType.EXPENSE.value:   "Expense",
}


# ════════════════════════════════════════════════════════════════
# INVOICES
# ════════════════════════════════════════════════════════════════

class InvoiceStatus(StrEnum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


INVOICE_STATUSES: list[str] = [s.value for s in InvoiceStatus]

INVOICE_STATUS_LABELS: dict[str, str] = {
    InvoiceStatus.DRAFT.value:          "Draft",
    InvoiceStatus.SENT.value:           "Sent",
    InvoiceStatus.PARTIALLY_PAID.value: "Partially paid",
    InvoiceStatus.PAID.value:           "Paid",
    InvoiceStatus.OVERDUE.value:        "Overdue",
    InvoiceStatus.CANCELLED.value:      "Cancelled",
}

TERMINAL_INVOICE_STATUSES: frozenset[str] = frozenset({
    InvoiceStatus.PAID.value,
    InvoiceStatus.CANCELLED.value,
})


# ════════════════════════════════════════════════════════════════
# PAYMENTS
# ════════════════════════════════════════════════════════════════

class PaymentDirection(StrEnum):
    IN = "IN"     # received from customer
    OUT = "OUT"   # paid to supplier or expense


class PaymentMethod(StrEnum):
    CASH = "CASH"
    BANK_TRANSFER = "BANK_TRANSFER"
    QRIS = "QRIS"
    EWALLET = "EWALLET"
    CREDIT_CARD = "CREDIT_CARD"
    OTHER = "OTHER"


PAYMENT_DIRECTIONS: list[str] = [d.value for d in PaymentDirection]
PAYMENT_METHODS: list[str] = [m.value for m in PaymentMethod]

PAYMENT_METHOD_LABELS: dict[str, str] = {
    PaymentMethod.CASH.value:          "Cash",
    PaymentMethod.BANK_TRANSFER.value: "Bank transfer",
    PaymentMethod.QRIS.value:          "QRIS",
    PaymentMethod.EWALLET.value:       "E-wallet",
    PaymentMethod.CREDIT_CARD.value:   "Credit card",
    PaymentMethod.OTHER.value:         "Other",
}


class PaymentReferenceType(StrEnum):
    INVOICE = "INVOICE"
    PURCHASE_ORDER = "PURCHASE_ORDER"
    EXPENSE = "EXPENSE"
    PROJECT = "PROJECT"           # for ad-hoc payments against a project
    OTHER = "OTHER"


PAYMENT_REFERENCE_TYPES: list[str] = [r.value for r in PaymentReferenceType]


# ════════════════════════════════════════════════════════════════
# EXPENSES
# ════════════════════════════════════════════════════════════════

class ExpenseCategory(StrEnum):
    RENT = "RENT"
    UTILITIES = "UTILITIES"          # electricity, water, internet
    SALARIES = "SALARIES"            # staff wages
    MARKETING = "MARKETING"
    SUPPLIES = "SUPPLIES"            # consumables bought directly (not via PO)
    TRANSPORT = "TRANSPORT"
    MAINTENANCE = "MAINTENANCE"
    PROFESSIONAL = "PROFESSIONAL"    # accountants, legal
    TAX = "TAX"
    OTHER = "OTHER"


EXPENSE_CATEGORIES: list[str] = [c.value for c in ExpenseCategory]

EXPENSE_CATEGORY_LABELS: dict[str, str] = {
    ExpenseCategory.RENT.value:         "Rent",
    ExpenseCategory.UTILITIES.value:    "Utilities",
    ExpenseCategory.SALARIES.value:     "Salaries",
    ExpenseCategory.MARKETING.value:    "Marketing",
    ExpenseCategory.SUPPLIES.value:     "Supplies",
    ExpenseCategory.TRANSPORT.value:    "Transport",
    ExpenseCategory.MAINTENANCE.value:  "Maintenance",
    ExpenseCategory.PROFESSIONAL.value: "Professional services",
    ExpenseCategory.TAX.value:          "Tax",
    ExpenseCategory.OTHER.value:        "Other",
}