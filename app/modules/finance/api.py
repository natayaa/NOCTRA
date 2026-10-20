"""REST endpoints for the finance module."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select

from app.core.constants import PermissionCode
from app.core.deps import DbSession
from app.core.exceptions import NotFoundError, ValidationError
from app.core.pagination import Page, PageParams, page_params, paginate
from app.modules.auth.dependencies import CurrentUser, require_permission
from app.modules.finance.constants import (
    ACCOUNT_TYPES,
    ACCOUNT_TYPE_LABELS,
    EXPENSE_CATEGORIES,
    EXPENSE_CATEGORY_LABELS,
    INVOICE_STATUSES,
    INVOICE_STATUS_LABELS,
    PAYMENT_METHODS,
    PAYMENT_METHOD_LABELS,
    TERMINAL_INVOICE_STATUSES,
    today_local,
)
from app.modules.finance.repository import (
    AccountRepository,
    ExpenseRepository,
    InvoiceRepository,
    PaymentRepository,
)
from app.modules.finance.schemas import (
    AccountOut,
    CashFlowSummary,
    ExpenseCreate,
    ExpenseOut,
    ExpenseUpdate,
    InvoiceCreate,
    InvoiceDetail,
    InvoiceFromProject,
    InvoiceItemOut,
    InvoiceListItem,
    InvoiceStatusChange,
    InvoiceUpdate,
    PaymentCreate,
    PaymentDetail,
    PaymentListItem,
    PaymentReverse,
    PayablesSummary,
    PnLReport,
    ReceivablesSummary,
)
from app.modules.finance.service import (
    ExpenseService,
    FinanceReportService,
    InvoiceService,
    PaymentService,
)

router = APIRouter(prefix="/finance", tags=["finance"])


async def _invoice_detail(
    db: DbSession, invoice, repo: InvoiceRepository
) -> InvoiceDetail:
    """Build InvoiceDetail with paid_amount, overdue flag, and customer name."""
    detail = InvoiceDetail.model_validate(invoice)
    detail.paid_amount = await repo.paid_amount(invoice.id)
    detail.balance_due = float(invoice.total) - detail.paid_amount
    detail.is_overdue = (
        invoice.due_date is not None
        and today_local() > invoice.due_date
        and invoice.status not in TERMINAL_INVOICE_STATUSES
    )

    from app.modules.customers.models import Customer
    customer = await db.get(Customer, invoice.customer_id)
    if customer:
        detail.customer_name = customer.name

    detail.items = [InvoiceItemOut.model_validate(i) for i in invoice.items]
    return detail


# ════════════════════════════════════════════════════════════════
# CATALOG
# ════════════════════════════════════════════════════════════════

@router.get("/catalog")
async def catalog() -> dict:
    return {
        "account_types": ACCOUNT_TYPES,
        "account_type_labels": ACCOUNT_TYPE_LABELS,
        "invoice_statuses": INVOICE_STATUSES,
        "invoice_status_labels": INVOICE_STATUS_LABELS,
        "payment_methods": PAYMENT_METHODS,
        "payment_method_labels": PAYMENT_METHOD_LABELS,
        "expense_categories": EXPENSE_CATEGORIES,
        "expense_category_labels": EXPENSE_CATEGORY_LABELS,
    }


# ════════════════════════════════════════════════════════════════
# ACCOUNTS
# ════════════════════════════════════════════════════════════════

@router.get("/accounts", response_model=list[AccountOut])
async def list_accounts(
    db: DbSession,
    account_type: str | None = Query(None),
    _=Depends(require_permission(PermissionCode.FINANCE_READ)),
) -> list[AccountOut]:
    stmt = AccountRepository(db).query(account_type=account_type)
    rows = (await db.execute(stmt)).scalars().all()
    return [AccountOut.model_validate(a) for a in rows]


# ════════════════════════════════════════════════════════════════
# INVOICES
# ════════════════════════════════════════════════════════════════

@router.get("/invoices", response_model=Page[InvoiceListItem])
async def list_invoices(
    db: DbSession,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, max_length=200),
    status_: str | None = Query(None, alias="status"),
    customer_id: UUID | None = Query(None),
    project_id: UUID | None = Query(None),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    only_unpaid: bool = Query(False),
    _=Depends(require_permission(PermissionCode.FINANCE_READ)),
) -> Page[InvoiceListItem]:
    if status_ is not None and status_ not in INVOICE_STATUSES:
        raise ValidationError(
            f"Invalid status {status_!r}. Choose from: {', '.join(INVOICE_STATUSES)}"
        )

    repo = InvoiceRepository(db)
    stmt = repo.query(
        q=q, status=status_, customer_id=customer_id, project_id=project_id,
        from_date=from_date, to_date=to_date, only_unpaid=only_unpaid,
    )
    rows, meta = await paginate(db, stmt, params)

    # Batch-fetch customers + paid amounts in 2 queries total (not N+1).
    customer_ids = {r.customer_id for r in rows if r.customer_id}
    customers: dict = {}
    if customer_ids:
        from app.modules.customers.models import Customer
        c_rows = await db.execute(select(Customer).where(Customer.id.in_(customer_ids)))
        customers = {c.id: c for c in c_rows.scalars().all()}

    paid_map = await repo.batch_paid_amount([r.id for r in rows])
    today = today_local()

    items: list[InvoiceListItem] = []
    for r in rows:
        item = InvoiceListItem.model_validate(r)
        item.paid_amount = paid_map.get(r.id, 0.0)
        item.balance_due = float(r.total) - item.paid_amount
        if r.customer_id in customers:
            item.customer_name = customers[r.customer_id].name
        item.is_overdue = (
            r.due_date is not None
            and today > r.due_date
            and r.status not in TERMINAL_INVOICE_STATUSES
        )
        items.append(item)

    return Page[InvoiceListItem](items=items, meta=meta)


@router.post("/invoices", response_model=InvoiceDetail, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    payload: InvoiceCreate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.INVOICE_WRITE)),
) -> InvoiceDetail:
    inv = await InvoiceService(db).create(payload, actor=actor)
    return await _invoice_detail(db, inv, InvoiceRepository(db))


@router.post("/invoices/from-project", response_model=InvoiceDetail, status_code=status.HTTP_201_CREATED)
async def create_invoice_from_project(
    payload: InvoiceFromProject,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.INVOICE_WRITE)),
) -> InvoiceDetail:
    inv = await InvoiceService(db).create_from_project(payload, actor=actor)
    return await _invoice_detail(db, inv, InvoiceRepository(db))


@router.get("/invoices/{invoice_id}", response_model=InvoiceDetail)
async def get_invoice(
    invoice_id: UUID,
    db: DbSession,
    _=Depends(require_permission(PermissionCode.FINANCE_READ)),
) -> InvoiceDetail:
    repo = InvoiceRepository(db)
    inv = await repo.get(invoice_id)
    if not inv:
        raise NotFoundError("Invoice not found")
    return await _invoice_detail(db, inv, repo)


@router.patch("/invoices/{invoice_id}", response_model=InvoiceDetail)
async def update_invoice(
    invoice_id: UUID,
    payload: InvoiceUpdate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.INVOICE_WRITE)),
) -> InvoiceDetail:
    inv = await InvoiceService(db).update(invoice_id, payload, actor=actor)
    return await _invoice_detail(db, inv, InvoiceRepository(db))


@router.post("/invoices/{invoice_id}/status", response_model=InvoiceDetail)
async def change_invoice_status(
    invoice_id: UUID,
    payload: InvoiceStatusChange,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.INVOICE_WRITE)),
) -> InvoiceDetail:
    inv = await InvoiceService(db).change_status(invoice_id, payload.status, actor=actor)
    return await _invoice_detail(db, inv, InvoiceRepository(db))


# ════════════════════════════════════════════════════════════════
# PAYMENTS
# ════════════════════════════════════════════════════════════════

@router.get("/payments", response_model=Page[PaymentListItem])
async def list_payments(
    db: DbSession,
    params: PageParams = Depends(page_params),
    direction: str | None = Query(None),
    customer_id: UUID | None = Query(None),
    supplier_id: UUID | None = Query(None),
    reference_type: str | None = Query(None),
    reference_id: UUID | None = Query(None),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    _=Depends(require_permission(PermissionCode.FINANCE_READ)),
) -> Page[PaymentListItem]:
    stmt = PaymentRepository(db).query(
        direction=direction, customer_id=customer_id, supplier_id=supplier_id,
        reference_type=reference_type, reference_id=reference_id,
        from_date=from_date, to_date=to_date,
    )
    rows, meta = await paginate(db, stmt, params)

    from app.modules.customers.models import Customer
    from app.modules.inventory.models import Supplier

    cids = {r.customer_id for r in rows if r.customer_id}
    sids = {r.supplier_id for r in rows if r.supplier_id}

    customers: dict = {}
    if cids:
        c_rows = await db.execute(select(Customer).where(Customer.id.in_(cids)))
        customers = {c.id: c for c in c_rows.scalars().all()}

    suppliers: dict = {}
    if sids:
        s_rows = await db.execute(select(Supplier).where(Supplier.id.in_(sids)))
        suppliers = {s.id: s for s in s_rows.scalars().all()}

    items: list[PaymentListItem] = []
    for r in rows:
        item = PaymentListItem.model_validate(r)
        if r.customer_id in customers:
            item.customer_name = customers[r.customer_id].name
        if r.supplier_id in suppliers:
            item.supplier_name = suppliers[r.supplier_id].name
        items.append(item)

    return Page[PaymentListItem](items=items, meta=meta)


@router.post("/payments", response_model=PaymentDetail, status_code=status.HTTP_201_CREATED)
async def record_payment(
    payload: PaymentCreate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.PAYMENT_WRITE)),
) -> PaymentDetail:
    payment = await PaymentService(db).record(payload, actor=actor)
    return PaymentDetail.model_validate(payment)


@router.get("/payments/{payment_id}", response_model=PaymentDetail)
async def get_payment(
    payment_id: UUID,
    db: DbSession,
    _=Depends(require_permission(PermissionCode.FINANCE_READ)),
) -> PaymentDetail:
    p = await PaymentRepository(db).get(payment_id)
    if not p:
        raise NotFoundError("Payment not found")
    return PaymentDetail.model_validate(p)


@router.post("/payments/{payment_id}/reverse", response_model=PaymentDetail)
async def reverse_payment(
    payment_id: UUID,
    payload: PaymentReverse,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.PAYMENT_WRITE)),
) -> PaymentDetail:
    reversal = await PaymentService(db).reverse(
        payment_id, actor=actor, reason=payload.reason,
    )
    return PaymentDetail.model_validate(reversal)


# ════════════════════════════════════════════════════════════════
# EXPENSES
# ════════════════════════════════════════════════════════════════

@router.get("/expenses", response_model=Page[ExpenseOut])
async def list_expenses(
    db: DbSession,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None),
    category: str | None = Query(None),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    _=Depends(require_permission(PermissionCode.FINANCE_READ)),
) -> Page[ExpenseOut]:
    stmt = ExpenseRepository(db).query(
        q=q, category=category, from_date=from_date, to_date=to_date,
    )
    rows, meta = await paginate(db, stmt, params)
    return Page[ExpenseOut](
        items=[ExpenseOut.model_validate(r) for r in rows], meta=meta
    )


@router.post("/expenses", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
async def create_expense(
    payload: ExpenseCreate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.EXPENSE_WRITE)),
) -> ExpenseOut:
    exp = await ExpenseService(db).create(payload, actor=actor)
    return ExpenseOut.model_validate(exp)


@router.patch("/expenses/{expense_id}", response_model=ExpenseOut)
async def update_expense(
    expense_id: UUID,
    payload: ExpenseUpdate,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.EXPENSE_WRITE)),
) -> ExpenseOut:
    exp = await ExpenseService(db).update(expense_id, payload, actor=actor)
    return ExpenseOut.model_validate(exp)


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: UUID,
    db: DbSession,
    actor: CurrentUser,
    _=Depends(require_permission(PermissionCode.EXPENSE_WRITE)),
) -> None:
    await ExpenseService(db).delete(expense_id, actor=actor)


# ════════════════════════════════════════════════════════════════
# REPORTS
# ════════════════════════════════════════════════════════════════

def _validate_range(from_date: date, to_date: date) -> None:
    if from_date > to_date:
        raise ValidationError("from_date must be <= to_date")


@router.get("/reports/pnl", response_model=PnLReport)
async def pnl_report(
    db: DbSession,
    from_date: date = Query(...),
    to_date: date = Query(...),
    _=Depends(require_permission(PermissionCode.FINANCE_REPORTS)),
) -> PnLReport:
    _validate_range(from_date, to_date)
    return await FinanceReportService(db).pnl(from_date=from_date, to_date=to_date)


@router.get("/reports/cash-flow", response_model=CashFlowSummary)
async def cash_flow_report(
    db: DbSession,
    from_date: date = Query(...),
    to_date: date = Query(...),
    _=Depends(require_permission(PermissionCode.FINANCE_REPORTS)),
) -> CashFlowSummary:
    _validate_range(from_date, to_date)
    return await FinanceReportService(db).cash_flow(from_date=from_date, to_date=to_date)


@router.get("/reports/receivables", response_model=ReceivablesSummary)
async def receivables_report(
    db: DbSession,
    _=Depends(require_permission(PermissionCode.FINANCE_REPORTS)),
) -> ReceivablesSummary:
    return await FinanceReportService(db).receivables()


@router.get("/reports/payables", response_model=PayablesSummary)
async def payables_report(
    db: DbSession,
    _=Depends(require_permission(PermissionCode.FINANCE_REPORTS)),
) -> PayablesSummary:
    return await FinanceReportService(db).payables()