"""Admin web routes for purchase orders."""

from __future__ import annotations

from datetime import date
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
from app.modules.inventory.constants import (
    PURCHASE_ORDER_STATUSES,
    PURCHASE_ORDER_STATUS_LABELS,
)
from app.modules.inventory.repository import (
    MaterialRepository,
    PurchaseOrderRepository,
    SupplierRepository,
)
from app.modules.inventory.schemas import (
    PurchaseOrderCreate,
    PurchaseOrderItemCreate,
    PurchaseOrderReceive,
    PurchaseOrderUpdate,
)
from app.modules.inventory.service import PurchaseOrderService
from app.web.admin._perms import read, write
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/purchase-orders", tags=["admin-purchase-orders"])

_FORM_ERRORS = (AppError, PydanticValidationError, ValueError, KeyError)


def _error_url(po_id: UUID, exc: Exception) -> str:
    """Redirect back to the PO with a properly encoded error message.

    `&`/`#` in a validation message would otherwise truncate the query
    string or inject extra parameters.
    """
    message = getattr(exc, "message", None) or str(exc) or "Invalid input"
    return (
        f"/admin/purchase-orders/{po_id}?error={quote(message.strip(), safe='')}"
    )


@router.get("", response_class=HTMLResponse)
async def list_view(
    request: Request,
    db: DbSession,
    params: PageParams = Depends(page_params),
    status_: str | None = Query(None, alias="status"),
    q: str | None = Query(None, max_length=200),
    _=read(PermissionCode.INVENTORY_READ),
    current=Depends(get_current_user),
) -> HTMLResponse:
    stmt = PurchaseOrderRepository(db).query(status=status_, q=q)
    rows, meta = await paginate(db, stmt, params)

    suppliers = list(
        (await db.execute(SupplierRepository(db).query())).scalars().all()
    )
    supplier_map = {s.id: s for s in suppliers}

    return templates.render(
        request,
        "admin/purchase_orders/list.html",
        {
            "title": "Purchase Orders",
            "purchase_orders": rows,
            "page_meta": meta,
            "suppliers_by_id": supplier_map,
            "status_filter": status_ or "",
            "q": q or "",
            "statuses": PURCHASE_ORDER_STATUSES,
            "status_labels": PURCHASE_ORDER_STATUS_LABELS,
        },
    )


@router.get("/new", response_class=HTMLResponse)
async def new_view(
    request: Request,
    db: DbSession,
    _=write(PermissionCode.INVENTORY_PURCHASE),
    current=Depends(get_current_user),
) -> HTMLResponse:
    suppliers = list(
        (await db.execute(SupplierRepository(db).query(is_active=True)))
        .scalars()
        .all()
    )
    return templates.render(
        request,
        "admin/purchase_orders/form.html",
        {
            "title": "New Purchase Order",
            "mode": "create",
            "po": None,
            "suppliers": suppliers,
        },
    )


@router.post("")
async def create_submit(
    request: Request,
    db: DbSession,
    _=write(PermissionCode.INVENTORY_PURCHASE),
    current=Depends(get_current_user),
):
    form = await request.form()
    try:
        payload = PurchaseOrderCreate(
            supplier_id=UUID(form["supplier_id"]),
            order_date=date.fromisoformat(form["order_date"]),
            expected_date=(
                date.fromisoformat(form["expected_date"])
                if form.get("expected_date") else None
            ),
            notes=(form.get("notes") or "").strip() or None,
        )
        po = await PurchaseOrderService(db).create(payload, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        suppliers = list(
            (await db.execute(SupplierRepository(db).query(is_active=True)))
            .scalars()
            .all()
        )
        return templates.render(
            request,
            "admin/purchase_orders/form.html",
            {
                "title": "New Purchase Order",
                "mode": "create",
                "po": None,
                "suppliers": suppliers,
                "error": getattr(exc, "message", str(exc)),
                "form_values": dict(form),
            },
            status_code=getattr(exc, "status_code", 400),
        )
    return RedirectResponse(url=f"/admin/purchase-orders/{po.id}", status_code=303)


@router.get("/{po_id}", response_class=HTMLResponse)
async def detail_view(
    po_id: UUID,
    request: Request,
    db: DbSession,
    _=read(PermissionCode.INVENTORY_READ),
    current=Depends(get_current_user),
) -> HTMLResponse:
    po = await PurchaseOrderRepository(db).get(po_id)
    if not po:
        raise NotFoundError("Purchase order not found")
    supplier = await SupplierRepository(db).get(po.supplier_id)
    materials = list(
        (await db.execute(MaterialRepository(db).query(is_active=True)))
        .scalars()
        .all()
    )
    material_map = {m.id: m for m in materials}
    return templates.render(
        request,
        "admin/purchase_orders/detail.html",
        {
            "title": po.code,
            "po": po,
            "supplier": supplier,
            "items": po.items,
            "materials": materials,
            "materials_by_id": material_map,
            "status_labels": PURCHASE_ORDER_STATUS_LABELS,
        },
    )


@router.post("/{po_id}/items")
async def add_item_submit(
    po_id: UUID,
    request: Request,
    db: DbSession,
    _=write(PermissionCode.INVENTORY_PURCHASE),
    current=Depends(get_current_user),
):
    form = await request.form()
    try:
        payload = PurchaseOrderItemCreate(
            material_id=UUID(form["material_id"]),
            quantity=float(form.get("quantity") or 0),
            unit_price=float(form.get("unit_price") or 0),
            notes=(form.get("notes") or "").strip() or None,
        )
        await PurchaseOrderService(db).add_item(po_id, payload, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return RedirectResponse(url=_error_url(po_id, exc), status_code=303)
    return RedirectResponse(url=f"/admin/purchase-orders/{po_id}", status_code=303)


@router.post("/{po_id}/items/{item_id}/delete")
async def delete_item_submit(
    po_id: UUID,
    item_id: UUID,
    request: Request,
    db: DbSession,
    _=write(PermissionCode.INVENTORY_PURCHASE),
    current=Depends(get_current_user),
):
    try:
        await PurchaseOrderService(db).delete_item(po_id, item_id, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return RedirectResponse(url=_error_url(po_id, exc), status_code=303)
    return RedirectResponse(url=f"/admin/purchase-orders/{po_id}", status_code=303)


@router.post("/{po_id}/send")
async def send_submit(
    po_id: UUID,
    request: Request,
    db: DbSession,
    _=write(PermissionCode.INVENTORY_PURCHASE),
    current=Depends(get_current_user),
):
    try:
        await PurchaseOrderService(db).send(po_id, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return RedirectResponse(url=_error_url(po_id, exc), status_code=303)
    return RedirectResponse(url=f"/admin/purchase-orders/{po_id}", status_code=303)


@router.post("/{po_id}/receive")
async def receive_submit(
    po_id: UUID,
    request: Request,
    db: DbSession,
    _=write(PermissionCode.INVENTORY_PURCHASE),
    current=Depends(get_current_user),
):
    try:
        await PurchaseOrderService(db).receive(
            po_id, PurchaseOrderReceive(), actor=current
        )
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return RedirectResponse(url=_error_url(po_id, exc), status_code=303)
    return RedirectResponse(url=f"/admin/purchase-orders/{po_id}", status_code=303)


@router.post("/{po_id}/cancel")
async def cancel_submit(
    po_id: UUID,
    request: Request,
    db: DbSession,
    _=write(PermissionCode.INVENTORY_PURCHASE),
    current=Depends(get_current_user),
):
    try:
        await PurchaseOrderService(db).cancel(po_id, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return RedirectResponse(url=_error_url(po_id, exc), status_code=303)
    return RedirectResponse(url=f"/admin/purchase-orders/{po_id}", status_code=303)