"""Admin web routes for suppliers."""

from __future__ import annotations

from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError as PydanticValidationError

from app.core.constants import PermissionCode
from app.core.deps import DbSession
from app.core.exceptions import AppError, NotFoundError
from app.core.pagination import PageParams, paginate, page_params
from app.modules.auth.dependencies import get_current_user
from app.modules.inventory.repository import SupplierRepository
from app.modules.inventory.schemas import SupplierCreate, SupplierUpdate
from app.modules.inventory.service import SupplierService
from app.web.admin._perms import read, write
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/suppliers", tags=["admin-suppliers"])

_FORM_ERRORS = (AppError, PydanticValidationError, ValueError, KeyError)


def _form_error(exc: Exception) -> str:
    return (getattr(exc, "message", None) or str(exc) or "Invalid input").strip()


def _build_create(form) -> SupplierCreate:
    return SupplierCreate(
        name=(form.get("name") or "").strip(),
        contact_person=(form.get("contact_person") or "").strip() or None,
        email=(form.get("email") or "").strip() or None,
        phone=(form.get("phone") or "").strip() or None,
        address=(form.get("address") or "").strip() or None,
        tax_id=(form.get("tax_id") or "").strip() or None,
        payment_terms=(form.get("payment_terms") or "").strip() or None,
        notes=(form.get("notes") or "").strip() or None,
    )


def _build_update(form) -> SupplierUpdate:
    return SupplierUpdate(
        name=(form.get("name") or "").strip() or None,
        contact_person=(form.get("contact_person") or "").strip() or None,
        email=(form.get("email") or "").strip() or None,
        phone=(form.get("phone") or "").strip() or None,
        address=(form.get("address") or "").strip() or None,
        tax_id=(form.get("tax_id") or "").strip() or None,
        payment_terms=(form.get("payment_terms") or "").strip() or None,
        notes=(form.get("notes") or "").strip() or None,
        is_active=("is_active" in form and form.get("is_active") == "true"),
    )


# ════════════════════════════════════════════════════════════════
# LIST
# ════════════════════════════════════════════════════════════════

@router.get("", response_class=HTMLResponse)
async def list_view(
    request: Request,
    db: DbSession,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, max_length=200),
    _=read(PermissionCode.SUPPLIER_READ),
    current=Depends(get_current_user),
) -> HTMLResponse:
    stmt = SupplierRepository(db).query(q=q)
    rows, meta = await paginate(db, stmt, params)
    return templates.render(
        request,
        "admin/suppliers/list.html",
        {
            "title": "Suppliers",
            "suppliers": rows,
            "page_meta": meta,
            "q": q or "",
        },
    )


# ════════════════════════════════════════════════════════════════
# NEW / CREATE
# ════════════════════════════════════════════════════════════════

@router.get("/new", response_class=HTMLResponse)
async def new_view(
    request: Request,
    _=write(PermissionCode.SUPPLIER_WRITE),
    current=Depends(get_current_user),
) -> HTMLResponse:
    return templates.render(
        request,
        "admin/suppliers/form.html",
        {"title": "New Supplier", "mode": "create", "supplier": None},
    )


@router.post("")
async def create_submit(
    request: Request,
    db: DbSession,
    _=write(PermissionCode.SUPPLIER_WRITE),
    current=Depends(get_current_user),
):
    form = await request.form()

    try:
        payload = _build_create(form)
        supplier = await SupplierService(db).create(payload, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return templates.render(
            request,
            "admin/suppliers/form.html",
            {
                "title": "New Supplier",
                "mode": "create",
                "supplier": None,
                "error": _form_error(exc),
                "form_values": dict(form),
            },
            status_code=getattr(exc, "status_code", 400),
        )

    return RedirectResponse(url=f"/admin/suppliers/{supplier.id}", status_code=303)


# ════════════════════════════════════════════════════════════════
# DETAIL
# ════════════════════════════════════════════════════════════════

@router.get("/{supplier_id}", response_class=HTMLResponse)
async def detail_view(
    supplier_id: UUID,
    request: Request,
    db: DbSession,
    _=read(PermissionCode.SUPPLIER_READ),
    current=Depends(get_current_user),
) -> HTMLResponse:
    supplier = await SupplierRepository(db).get(supplier_id)
    if not supplier:
        raise NotFoundError("Supplier not found")
    return templates.render(
        request,
        "admin/suppliers/detail.html",
        {"title": supplier.name, "supplier": supplier},
    )


# ════════════════════════════════════════════════════════════════
# EDIT
# ════════════════════════════════════════════════════════════════

@router.get("/{supplier_id}/edit", response_class=HTMLResponse)
async def edit_view(
    supplier_id: UUID,
    request: Request,
    db: DbSession,
    _=write(PermissionCode.SUPPLIER_WRITE),
    current=Depends(get_current_user),
) -> HTMLResponse:
    supplier = await SupplierRepository(db).get(supplier_id)
    if not supplier:
        raise NotFoundError("Supplier not found")
    return templates.render(
        request,
        "admin/suppliers/form.html",
        {"title": f"Edit {supplier.name}", "mode": "edit", "supplier": supplier},
    )


@router.post("/{supplier_id}")
async def update_submit(
    supplier_id: UUID,
    request: Request,
    db: DbSession,
    _=write(PermissionCode.SUPPLIER_WRITE),
    current=Depends(get_current_user),
):
    form = await request.form()

    try:
        payload = _build_update(form)
        await SupplierService(db).update(supplier_id, payload, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        supplier = await SupplierRepository(db).get(supplier_id)
        return templates.render(
            request,
            "admin/suppliers/form.html",
            {
                "title": f"Edit {supplier.name}" if supplier else "Edit Supplier",
                "mode": "edit",
                "supplier": supplier,
                "error": _form_error(exc),
                "form_values": dict(form),
            },
            status_code=getattr(exc, "status_code", 400),
        )

    return RedirectResponse(url=f"/admin/suppliers/{supplier_id}", status_code=303)