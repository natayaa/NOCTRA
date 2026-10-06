"""Admin web routes for suppliers."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.deps import DbSession
from app.core.exceptions import AppError, NotFoundError
from app.core.pagination import PageParams, paginate, page_params
from app.modules.auth.dependencies import get_current_user
from app.modules.inventory.repository import SupplierRepository
from app.modules.inventory.schemas import SupplierCreate, SupplierUpdate
from app.modules.inventory.service import SupplierService
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/suppliers", tags=["admin-suppliers"])


@router.get("", response_class=HTMLResponse)
async def list_view(
    request: Request,
    db: DbSession,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, max_length=200),
    current=Depends(get_current_user),
) -> HTMLResponse:
    stmt = SupplierRepository(db).query(q=q)
    rows, meta = await paginate(db, stmt, params)
    return templates.render(
        request,
        "admin/suppliers/list.html",
        {"title": "Suppliers", "suppliers": rows, "page_meta": meta, "q": q or ""},
    )


@router.get("/new", response_class=HTMLResponse)
async def new_view(request: Request, current=Depends(get_current_user)) -> HTMLResponse:
    return templates.render(
        request,
        "admin/suppliers/form.html",
        {"title": "New Supplier", "mode": "create", "supplier": None},
    )


@router.post("")
async def create_submit(request: Request, db: DbSession, current=Depends(get_current_user)):
    form = await request.form()
    payload = SupplierCreate(
        name=(form.get("name") or "").strip(),
        contact_person=(form.get("contact_person") or "").strip() or None,
        email=(form.get("email") or "").strip() or None,
        phone=(form.get("phone") or "").strip() or None,
        address=(form.get("address") or "").strip() or None,
        tax_id=(form.get("tax_id") or "").strip() or None,
        payment_terms=(form.get("payment_terms") or "").strip() or None,
        notes=(form.get("notes") or "").strip() or None,
    )
    try:
        supplier = await SupplierService(db).create(payload, actor=current)
    except AppError as exc:
        await db.rollback()
        return templates.render(
            request,
            "admin/suppliers/form.html",
            {
                "title": "New Supplier",
                "mode": "create",
                "supplier": None,
                "error": exc.message,
                "form_values": dict(form),
            },
            status_code=exc.status_code,
        )
    await db.commit()
    return RedirectResponse(url=f"/admin/suppliers/{supplier.id}", status_code=303)


@router.get("/{supplier_id}", response_class=HTMLResponse)
async def detail_view(
    supplier_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
) -> HTMLResponse:
    supplier = await SupplierRepository(db).get(supplier_id)
    if not supplier:
        raise NotFoundError("Supplier not found")
    return templates.render(
        request,
        "admin/suppliers/detail.html",
        {"title": supplier.name, "supplier": supplier},
    )


@router.get("/{supplier_id}/edit", response_class=HTMLResponse)
async def edit_view(
    supplier_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
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
    supplier_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
):
    form = await request.form()
    payload = SupplierUpdate(
        name=(form.get("name") or "").strip() or None,
        contact_person=(form.get("contact_person") or "").strip() or None,
        email=(form.get("email") or "").strip() or None,
        phone=(form.get("phone") or "").strip() or None,
        address=(form.get("address") or "").strip() or None,
        tax_id=(form.get("tax_id") or "").strip() or None,
        payment_terms=(form.get("payment_terms") or "").strip() or None,
        notes=(form.get("notes") or "").strip() or None,
        is_active=form.get("is_active") == "true",
    )
    await SupplierService(db).update(supplier_id, payload, actor=current)
    await db.commit()
    return RedirectResponse(url=f"/admin/suppliers/{supplier_id}", status_code=303)