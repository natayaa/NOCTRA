"""Admin web routes for materials."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from pydantic import ValidationError as PydanticValidationError

from app.core.deps import DbSession
from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.pagination import PageParams, paginate, page_params
from app.modules.auth.dependencies import get_current_user
from app.modules.inventory.constants import (
    MANUAL_TRANSACTION_TYPES,
    MATERIAL_CATEGORIES,
    MATERIAL_CATEGORY_LABELS,
    MATERIAL_CATEGORY_TONE,
    MATERIAL_SORT_OPTIONS,
    TRANSACTION_TYPE_LABELS,
    TRANSACTION_TYPE_TONE,
    TRANSACTION_TYPES,
    UNITS,
    ReferenceType,
    TransactionType,
)
from app.modules.inventory.repository import (
    InventoryTransactionRepository,
    MaterialRepository,
    SupplierRepository,
)
from app.modules.inventory.schemas import (
    InventoryTransactionCreate,
    MaterialCreate,
    MaterialUpdate,
    MaterialUpdatePrice,
)
from app.modules.inventory.service import InventoryService, MaterialService
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/materials", tags=["admin-materials"])

_FORM_ERRORS = (AppError, PydanticValidationError, ValueError, KeyError)


# ════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════

def _catalog_context() -> dict:
    return {
        "categories": MATERIAL_CATEGORIES,
        "category_labels": MATERIAL_CATEGORY_LABELS,
        "category_tone": MATERIAL_CATEGORY_TONE,
        "units": UNITS,
        "material_sort_options": MATERIAL_SORT_OPTIONS,
        "transaction_types": TRANSACTION_TYPES,
        "transaction_type_labels": TRANSACTION_TYPE_LABELS,
        "transaction_type_tone": TRANSACTION_TYPE_TONE,
        "manual_transaction_types": MANUAL_TRANSACTION_TYPES,
    }


def _form_error(exc: Exception) -> str:
    msg = getattr(exc, "message", None) or str(exc)
    return (msg or "Invalid input").strip()


def _redirect_with_error(material_id: UUID, exc: Exception) -> RedirectResponse:
    return RedirectResponse(
        url=f"/admin/materials/{material_id}?error={quote(_form_error(exc), safe='')}",
        status_code=303,
    )


def _safe_float(raw) -> float | None:
    """Safely parse float; return None if empty or invalid (Pydantic will handle)."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _safe_int(raw, default: int = 0) -> int:
    if raw is None:
        return default
    s = str(raw).strip()
    if not s:
        return default
    try:
        return int(s)
    except (ValueError, TypeError):
        return default


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


async def _load_suppliers(db):
    return list(
        (await db.execute(SupplierRepository(db).query(is_active=True))).scalars().all()
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
    category: str | None = Query(None),
    is_active: bool | None = Query(True),
    sort: str = Query("category_name"),
    current=Depends(get_current_user),
) -> HTMLResponse:
    repo = MaterialRepository(db)
    stmt = repo.query(
        q=q, category=category, is_active=is_active,
        sort=sort if sort in MATERIAL_SORT_OPTIONS else "category_name",
    )
    rows, meta = await paginate(db, stmt, params)

    # Batch-load stock for visible materials
    material_ids = [m.id for m in rows]
    stock_map: dict = {}
    if material_ids:
        stock_map = await InventoryTransactionRepository(db).stock_for_materials(material_ids)

    # Stats (across all active)
    stats = await repo.stats()
    all_categories = MATERIAL_CATEGORIES

    def _qs(**overrides) -> str:
        from urllib.parse import urlencode
        base = {
            "q": q or "",
            "category": category or "",
            "is_active": "" if is_active is None else ("true" if is_active else "false"),
            "sort": sort,
        }
        base.update({k: ("" if v is None else v) for k, v in overrides.items()})
        return "?" + urlencode({k: v for k, v in base.items() if v})

    return templates.render(
        request,
        "admin/materials/list.html",
        {
            "title": "Materials",
            "materials": rows,
            "page_meta": meta,
            "stats": stats,
            "stock_map": stock_map,
            "q": q or "",
            "category_filter": category or "",
            "is_active_filter": is_active,
            "sort": sort,
            "all_categories": all_categories,
            "qs": _qs,
            **_catalog_context(),
        },
    )


# ════════════════════════════════════════════════════════════════
# EXPORT CSV
# ════════════════════════════════════════════════════════════════

@router.get("/export.csv")
async def export_csv(
    db: DbSession,
    q: str | None = Query(None),
    category: str | None = Query(None),
    is_active: bool | None = Query(True),
    current=Depends(get_current_user),
):
    stmt = MaterialRepository(db).query(q=q, category=category, is_active=is_active)
    rows = (await db.execute(stmt)).scalars().all()

    material_ids = [m.id for m in rows]
    stock_map: dict = {}
    if material_ids:
        stock_map = await InventoryTransactionRepository(db).stock_for_materials(material_ids)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "code", "name", "brand", "category", "sku",
        "purchase_unit", "stock_unit", "stock_units_per_purchase",
        "current_purchase_price", "cost_per_stock_unit",
        "current_stock", "stock_value",
        "reorder_point", "min_stock", "location", "is_active",
    ])
    for m in rows:
        stock = stock_map.get(m.id, 0.0)
        cost_per_unit = m.cost_per_stock_unit
        writer.writerow([
            m.code, m.name, m.brand or "", m.category, m.sku or "",
            m.purchase_unit, m.stock_unit, float(m.stock_units_per_purchase),
            float(m.current_purchase_price), f"{cost_per_unit:.4f}",
            f"{stock:.4f}", f"{stock * cost_per_unit:.2f}",
            float(m.reorder_point), float(m.min_stock),
            m.location or "", "yes" if m.is_active else "no",
        ])

    buf.seek(0)
    filename = f"materials-{datetime.utcnow().strftime('%Y%m%d-%H%M')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ════════════════════════════════════════════════════════════════
# CREATE
# ════════════════════════════════════════════════════════════════

@router.get("/new", response_class=HTMLResponse)
async def new_view(
    request: Request, db: DbSession, current=Depends(get_current_user)
) -> HTMLResponse:
    return templates.render(
        request,
        "admin/materials/form.html",
        {
            "title": "New Material",
            "mode": "create",
            "material": None,
            "suppliers": await _load_suppliers(db),
            **_catalog_context(),
        },
    )


@router.post("")
async def create_submit(
    request: Request, db: DbSession, current=Depends(get_current_user)
):
    form = await request.form()

    async def _render_error(msg: str, status_code: int = 400):
        return templates.render(
            request,
            "admin/materials/form.html",
            {
                "title": "New Material",
                "mode": "create",
                "material": None,
                "suppliers": await _load_suppliers(db),
                "error": msg,
                "form_values": dict(form),
                **_catalog_context(),
            },
            status_code=status_code,
        )

    try:
        payload = MaterialCreate(
            code=(form.get("code") or "").strip(),
            sku=(form.get("sku") or "").strip() or None,
            name=(form.get("name") or "").strip(),
            brand=(form.get("brand") or "").strip() or None,
            category=(form.get("category") or "").strip(),
            purchase_unit=(form.get("purchase_unit") or "").strip(),
            stock_unit=(form.get("stock_unit") or "").strip(),
            stock_units_per_purchase=_safe_float(form.get("stock_units_per_purchase")) or 0,
            current_purchase_price=_safe_float(form.get("current_purchase_price")) or 0,
            reorder_point=_safe_float(form.get("reorder_point")) or 0,
            min_stock=_safe_float(form.get("min_stock")) or 0,
            preferred_supplier_id=_safe_uuid(form.get("preferred_supplier_id")),
            location=(form.get("location") or "").strip() or None,
            notes=(form.get("notes") or "").strip() or None,
        )
        material = await MaterialService(db).create(payload, actor=current)
    except _FORM_ERRORS as exc:
        await db.rollback()
        return await _render_error(_form_error(exc), getattr(exc, "status_code", 400))

    await db.commit()
    return RedirectResponse(url=f"/admin/materials/{material.id}", status_code=303)


# ════════════════════════════════════════════════════════════════
# DETAIL
# ════════════════════════════════════════════════════════════════

@router.get("/{material_id}", response_class=HTMLResponse)
async def detail_view(
    material_id: UUID,
    request: Request,
    db: DbSession,
    params: PageParams = Depends(page_params),
    error: str | None = Query(None),
    tx_type: str | None = Query(None),
    current=Depends(get_current_user),
) -> HTMLResponse:
    repo = MaterialRepository(db)
    material = await repo.get(material_id)
    if not material:
        raise NotFoundError("Material not found")

    stock = await repo.current_stock(material_id)

    tx_stmt = InventoryTransactionRepository(db).query(
        material_id=material_id,
        transaction_type=tx_type,
    )
    tx_rows, tx_meta = await paginate(db, tx_stmt, params)

    supplier = None
    if material.preferred_supplier_id:
        supplier = await SupplierRepository(db).get(material.preferred_supplier_id)

    return templates.render(
        request,
        "admin/materials/detail.html",
        {
            "title": material.name,
            "material": material,
            "supplier": supplier,
            "current_stock": stock,
            "cost_per_stock_unit": material.cost_per_stock_unit,
            "stock_value": stock * material.cost_per_stock_unit,
            "transactions": tx_rows,
            "page_meta": tx_meta,
            "error": error,
            "tx_type_filter": tx_type or "",
            **_catalog_context(),
        },
    )


# ════════════════════════════════════════════════════════════════
# EDIT
# ════════════════════════════════════════════════════════════════

@router.get("/{material_id}/edit", response_class=HTMLResponse)
async def edit_view(
    material_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
) -> HTMLResponse:
    material = await MaterialRepository(db).get(material_id)
    if not material:
        raise NotFoundError("Material not found")
    return templates.render(
        request,
        "admin/materials/form.html",
        {
            "title": f"Edit {material.name}",
            "mode": "edit",
            "material": material,
            "suppliers": await _load_suppliers(db),
            **_catalog_context(),
        },
    )


@router.post("/{material_id}")
async def update_submit(
    material_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
):
    form = await request.form()

    async def _render_error(msg: str, status_code: int = 400):
        material = await MaterialRepository(db).get(material_id)
        return templates.render(
            request,
            "admin/materials/form.html",
            {
                "title": f"Edit {material.name}" if material else "Edit Material",
                "mode": "edit",
                "material": material,
                "suppliers": await _load_suppliers(db),
                "error": msg,
                "form_values": dict(form),
                **_catalog_context(),
            },
            status_code=status_code,
        )

    try:
        payload = MaterialUpdate(
            sku=(form.get("sku") or "").strip() or None,
            name=(form.get("name") or "").strip() or None,
            brand=(form.get("brand") or "").strip() or None,
            category=(form.get("category") or "").strip() or None,
            purchase_unit=(form.get("purchase_unit") or "").strip() or None,
            stock_unit=(form.get("stock_unit") or "").strip() or None,
            stock_units_per_purchase=_safe_float(form.get("stock_units_per_purchase")),
            reorder_point=_safe_float(form.get("reorder_point")),
            min_stock=_safe_float(form.get("min_stock")),
            preferred_supplier_id=_safe_uuid(form.get("preferred_supplier_id")),
            location=(form.get("location") or "").strip() or None,
            notes=(form.get("notes") or "").strip() or None,
            is_active=form.get("is_active") == "true",
        )
        await MaterialService(db).update(material_id, payload, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return await _render_error(_form_error(exc), getattr(exc, "status_code", 400))

    return RedirectResponse(url=f"/admin/materials/{material_id}", status_code=303)


# ════════════════════════════════════════════════════════════════
# PRICE CHANGE
# ════════════════════════════════════════════════════════════════

@router.post("/{material_id}/price")
async def price_submit(
    material_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
):
    form = await request.form()

    new_price = _safe_float(form.get("new_purchase_price"))
    if new_price is None or new_price < 0:
        return _redirect_with_error(
            material_id, ValueError("New price must be a non-negative number")
        )

    note = (form.get("note") or "").strip() or None

    try:
        await MaterialService(db).update_price(
            material_id, new_price, note=note, actor=current
        )
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return _redirect_with_error(material_id, exc)

    return RedirectResponse(url=f"/admin/materials/{material_id}", status_code=303)


# ════════════════════════════════════════════════════════════════
# QUICK TRANSACTION
# ════════════════════════════════════════════════════════════════

@router.post("/{material_id}/transaction")
async def transaction_submit(
    material_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
):
    """Quick-record a stock movement from the material detail page."""
    form = await request.form()

    quantity = _safe_float(form.get("quantity"))
    if quantity is None or quantity <= 0:
        return _redirect_with_error(
            material_id, ValueError("Quantity must be a positive number")
        )

    try:
        payload = InventoryTransactionCreate(
            material_id=material_id,
            transaction_type=(form.get("transaction_type") or "").strip(),
            quantity=quantity,
            unit_cost=_safe_float(form.get("unit_cost")),
            reference_type=ReferenceType.MANUAL.value,
            reference_note=(form.get("reference_note") or "").strip() or None,
            notes=(form.get("notes") or "").strip() or None,
        )
        await InventoryService(db).record(payload, actor=current)
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return _redirect_with_error(material_id, exc)

    return RedirectResponse(url=f"/admin/materials/{material_id}", status_code=303)


# ════════════════════════════════════════════════════════════════
# ACTIVATE / DEACTIVATE
# ════════════════════════════════════════════════════════════════

@router.post("/{material_id}/deactivate")
async def deactivate_submit(
    material_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
):
    try:
        await MaterialService(db).update(
            material_id, MaterialUpdate(is_active=False), actor=current
        )
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return _redirect_with_error(material_id, exc)
    return RedirectResponse(url=f"/admin/materials/{material_id}", status_code=303)


@router.post("/{material_id}/reactivate")
async def reactivate_submit(
    material_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
):
    try:
        await MaterialService(db).update(
            material_id, MaterialUpdate(is_active=True), actor=current
        )
        await db.commit()
    except _FORM_ERRORS as exc:
        await db.rollback()
        return _redirect_with_error(material_id, exc)
    return RedirectResponse(url=f"/admin/materials/{material_id}", status_code=303)