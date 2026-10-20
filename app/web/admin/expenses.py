"""Admin web routes for expenses."""

from __future__ import annotations

from datetime import date
from urllib.parse import quote, urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError as PydanticValidationError

from app.core.constants import PermissionCode
from app.core.deps import DbSession
from app.core.exceptions import AppError, NotFoundError
from app.core.pagination import PageParams, paginate, page_params
from app.modules.auth.dependencies import get_current_user
from app.modules.finance.constants import (
    EXPENSE_CATEGORIES,
    EXPENSE_CATEGORY_LABELS,
    today_local,
)
from app.modules.finance.repository import (
    AccountRepository,
    ExpenseRepository,
)
from app.modules.finance.schemas import ExpenseCreate, ExpenseUpdate
from app.modules.finance.service import ExpenseService
from app.web.admin._perms import read, write
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/expenses", tags=["admin-expenses"])

_FORM_ERRORS = (AppError, PydanticValidationError, ValueError, KeyError)


def _form_error(exc: Exception) -> str:
    return (getattr(exc, "message", None) or str(exc) or "Invalid input").strip()


def _safe_float(raw) -> float | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _safe_uuid(raw) -> UUID | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        return UUID(s)
    except (ValueError, TypeError):
        return None


def _safe_date(raw) -> date | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


async def _load_accounts(db):
    return (
        await db.execute(AccountRepository(db).query(account_type="EXPENSE"))
    ).scalars().all()


# ════════════════════════════════════════════════════════════════
# LIST
# ════════════════════════════════════════════════════════════════

@router.get("", response_class=HTMLResponse)
async def list_view(
    request: Request,
    db: DbSession,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, max_length=200),
    category: str | None = Query(None),
    _=read(PermissionCode.FINANCE_READ),
    current=Depends(get_current_user),
) -> HTMLResponse:
    stmt = ExpenseRepository(db).query(q=q, category=category)
    rows, meta = await paginate(db, stmt, params)

    def qs(page: int | None = None, **overrides) -> str:
        base = {
            "q": q or "",
            "category": category or "",
        }
        if page is not None:
            base["page"] = str(page)
        base.update({k: ("" if v is None else str(v)) for k, v in overrides.items()})
        return "?" + urlencode({k: v for k, v in base.items() if v})

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
            "qs": qs,
        },
    )


# ════════════════════════════════════════════════════════════════
# NEW / CREATE
# ════════════════════════════════════════════════════════════════

@router.get("/new", response_class=HTMLResponse)
async def new_view(
    request: Request,
    db: DbSession,
    _=write(PermissionCode.EXPENSE_WRITE),
    current=Depends(get_current_user),
) -> HTMLResponse:
    return templates.render(
        request,
        "admin/expenses/form.html",
        {
            "title": "New Expense",
            "mode": "create",
            "expense": None,
            "accounts": await _load_accounts(db),
            "categories": EXPENSE_CATEGORIES,
            "category_labels": EXPENSE_CATEGORY_LABELS,
            "today": today_local(),
        },
    )


@router.post("")
async def create_submit(
    request: Request,
    db: DbSession,
    _=write(PermissionCode.EXPENSE_WRITE),
    current=Depends(get_current_user),
):
    form = await request.form()

    async def _render_error(msg: str, status_code: int = 400):
        return templates.render(
            request,
            "admin/expenses/form.html",
            {
                "title": "New Expense",
                "mode": "create",
                "expense": None,
                "accounts": await _load_accounts(db),
                "categories": EXPENSE_CATEGORIES,
                "category_labels": EXPENSE_CATEGORY_LABELS,
                "today": today_local(),
                "error": msg,
                "form_values": dict(form),
            },
            status_code=status_code,
        )

    try:
        payload = ExpenseCreate(
            category=(form.get("category") or "").strip(),
            description=(form.get("description") or "").strip(),
            amount=_safe_float(form.get("amount")) or 0,
            expense_date=date.fromisoformat(form["expense_date"]),
            account_id=_safe_uuid(form.get("account_id")),
            reference_number=(form.get("reference_number") or "").strip() or None,
            notes=(form.get("notes") or "").strip() or None,
        )
        await ExpenseService(db).create(payload, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return await _render_error(
            _form_error(exc), getattr(exc, "status_code", 400)
        )

    return RedirectResponse(url="/admin/expenses", status_code=303)


# ════════════════════════════════════════════════════════════════
# EDIT / UPDATE
# ════════════════════════════════════════════════════════════════

@router.get("/{expense_id}/edit", response_class=HTMLResponse)
async def edit_view(
    expense_id: UUID,
    request: Request,
    db: DbSession,
    error: str | None = Query(None),
    _=write(PermissionCode.EXPENSE_WRITE),
    current=Depends(get_current_user),
) -> HTMLResponse:
    exp = await ExpenseRepository(db).get(expense_id)
    if not exp:
        raise NotFoundError("Expense not found")
    return templates.render(
        request,
        "admin/expenses/form.html",
        {
            "title": f"Edit {exp.code}",
            "mode": "edit",
            "expense": exp,
            "accounts": await _load_accounts(db),
            "categories": EXPENSE_CATEGORIES,
            "category_labels": EXPENSE_CATEGORY_LABELS,
            "today": today_local(),
            "error": error,
        },
    )


@router.post("/{expense_id}")
async def update_submit(
    expense_id: UUID,
    request: Request,
    db: DbSession,
    _=write(PermissionCode.EXPENSE_WRITE),
    current=Depends(get_current_user),
):
    form = await request.form()

    try:
        payload = ExpenseUpdate(
            category=(form.get("category") or "").strip() or None,
            description=(form.get("description") or "").strip() or None,
            amount=_safe_float(form.get("amount")),
            expense_date=_safe_date(form.get("expense_date")),
            account_id=_safe_uuid(form.get("account_id")),
            reference_number=(form.get("reference_number") or "").strip() or None,
            notes=(form.get("notes") or "").strip() or None,
        )
        await ExpenseService(db).update(expense_id, payload, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        msg = quote(_form_error(exc), safe="")
        return RedirectResponse(
            url=f"/admin/expenses/{expense_id}/edit?error={msg}",
            status_code=303,
        )

    return RedirectResponse(url="/admin/expenses", status_code=303)


# ════════════════════════════════════════════════════════════════
# DELETE
# ════════════════════════════════════════════════════════════════

@router.post("/{expense_id}/delete")
async def delete_submit(
    expense_id: UUID,
    request: Request,
    db: DbSession,
    _=write(PermissionCode.EXPENSE_WRITE),
    current=Depends(get_current_user),
):
    try:
        await ExpenseService(db).delete(expense_id, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        msg = quote(_form_error(exc), safe="")
        return RedirectResponse(
            url=f"/admin/expenses?error={msg}", status_code=303
        )
    return RedirectResponse(url="/admin/expenses", status_code=303)