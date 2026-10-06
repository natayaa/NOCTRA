"""Admin web routes for expenses."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.deps import DbSession
from app.core.exceptions import AppError, NotFoundError
from app.core.pagination import PageParams, paginate, page_params
from app.modules.auth.dependencies import get_current_user
from app.modules.finance.constants import (
    EXPENSE_CATEGORIES,
    EXPENSE_CATEGORY_LABELS,
)
from app.modules.finance.repository import (
    AccountRepository,
    ExpenseRepository,
)
from app.modules.finance.schemas import ExpenseCreate, ExpenseUpdate
from app.modules.finance.service import ExpenseService
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/expenses", tags=["admin-expenses"])


@router.get("", response_class=HTMLResponse)
async def list_view(
    request: Request,
    db: DbSession,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None),
    category: str | None = Query(None),
    current=Depends(get_current_user),
) -> HTMLResponse:
    stmt = ExpenseRepository(db).query(q=q, category=category)
    rows, meta = await paginate(db, stmt, params)
    return templates.render(
        request,
        "admin/expenses/list.html",
        {
            "title": "Expenses",
            "expenses": rows,
            "page_meta": meta,
            "q": q or "",
            "category_filter": category or "",
            "categories": EXPENSE_CATEGORIES,
            "category_labels": EXPENSE_CATEGORY_LABELS,
        },
    )


@router.get("/new", response_class=HTMLResponse)
async def new_view(request: Request, db: DbSession, current=Depends(get_current_user)) -> HTMLResponse:
    accounts = (await db.execute(AccountRepository(db).query(account_type="EXPENSE"))).scalars().all()
    return templates.render(
        request,
        "admin/expenses/form.html",
        {
            "title": "New Expense",
            "mode": "create",
            "expense": None,
            "accounts": accounts,
            "categories": EXPENSE_CATEGORIES,
            "category_labels": EXPENSE_CATEGORY_LABELS,
            "today": datetime.now(UTC).date(),
        },
    )


@router.post("")
async def create_submit(request: Request, db: DbSession, current=Depends(get_current_user)):
    form = await request.form()
    payload = ExpenseCreate(
        category=(form.get("category") or "").strip(),
        description=(form.get("description") or "").strip(),
        amount=float(form.get("amount") or 0),
        expense_date=date.fromisoformat(form["expense_date"]),
        account_id=(UUID(form["account_id"]) if form.get("account_id") else None),
        reference_number=(form.get("reference_number") or "").strip() or None,
        notes=(form.get("notes") or "").strip() or None,
    )
    try:
        await ExpenseService(db).create(payload, actor=current)
        await db.commit()
    except AppError as exc:
        await db.rollback()
        accounts = (await db.execute(AccountRepository(db).query(account_type="EXPENSE"))).scalars().all()
        return templates.render(
            request,
            "admin/expenses/form.html",
            {
                "title": "New Expense",
                "mode": "create",
                "expense": None,
                "accounts": accounts,
                "categories": EXPENSE_CATEGORIES,
                "category_labels": EXPENSE_CATEGORY_LABELS,
                "today": datetime.now(UTC).date(),
                "error": exc.message,
                "form_values": dict(form),
            },
            status_code=exc.status_code,
        )
    return RedirectResponse(url="/admin/expenses", status_code=303)


@router.get("/{expense_id}/edit", response_class=HTMLResponse)
async def edit_view(
    expense_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
) -> HTMLResponse:
    exp = await ExpenseRepository(db).get(expense_id)
    if not exp:
        raise NotFoundError("Expense not found")
    accounts = (await db.execute(AccountRepository(db).query(account_type="EXPENSE"))).scalars().all()
    return templates.render(
        request,
        "admin/expenses/form.html",
        {
            "title": f"Edit {exp.code}",
            "mode": "edit",
            "expense": exp,
            "accounts": accounts,
            "categories": EXPENSE_CATEGORIES,
            "category_labels": EXPENSE_CATEGORY_LABELS,
            "today": datetime.now(UTC).date(),
        },
    )


@router.post("/{expense_id}")
async def update_submit(
    expense_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
):
    form = await request.form()
    payload = ExpenseUpdate(
        category=(form.get("category") or "").strip() or None,
        description=(form.get("description") or "").strip() or None,
        amount=(float(form["amount"]) if form.get("amount") else None),
        expense_date=(date.fromisoformat(form["expense_date"]) if form.get("expense_date") else None),
        account_id=(UUID(form["account_id"]) if form.get("account_id") else None),
        reference_number=(form.get("reference_number") or "").strip() or None,
        notes=(form.get("notes") or "").strip() or None,
    )
    try:
        await ExpenseService(db).update(expense_id, payload, actor=current)
        await db.commit()
    except AppError as exc:
        await db.rollback()
        return RedirectResponse(url=f"/admin/expenses/{expense_id}/edit?error={exc.message}", status_code=303)
    return RedirectResponse(url="/admin/expenses", status_code=303)


@router.post("/{expense_id}/delete")
async def delete_submit(
    expense_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
):
    await ExpenseService(db).delete(expense_id, actor=current)
    await db.commit()
    return RedirectResponse(url="/admin/expenses", status_code=303)