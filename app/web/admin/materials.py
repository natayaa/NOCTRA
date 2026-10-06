"""Admin web routes for materials."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.deps import DbSession
from app.core.exceptions import AppError, NotFoundError
from app.core.pagination import PageParams, paginate, page_params
from app.modules.auth.dependencies import get_current_user
from app.modules.inventory.constants import (
    MATERIAL_CATEGORIES,
    MATERIAL_CATEGORY_LABELS,
    UNITS
)
from app.modules.inventory.repository import (
    InventoryTransactionRepository,
    MaterialRepository,
    SupplierRepository,
)
from app.modules.inventory.schemas import (
    MaterialCreate,
    MaterialUpdate,
    MaterialUpdatePrice,
)
from app.modules.inventory.service import MaterialService
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/materials", tags=["admin-materials"])


def _catalog_context() -> dict:
    return {
        "categories": MATERIAL_CATEGORIES,
        "category_labels": MATERIAL_CATEGORY_LABELS,
        "units": UNITS,
    }


@router.get("", response_class=HTMLResponse)
async def list_view(
    request: Request,
    db: DbSession,
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, max_length=200),
    category: str | None = Query(None),
    current=Depends(get_current_user),
) -> HTMLResponse:
    stmt = MaterialRepository(db).query(q=q, category=category, is_active=True)
    rows, meta = await paginate(db, stmt, params)
    return templates.render(
        request,
        "admin/materials/list.html",
        {
            "title": "Materials",
            "materials": rows,
            "page_meta": meta,
            "q": q or "",
            "category_filter": category or "",
            **_catalog_context(),
        },
    )


@router.get("/new", response_class=HTMLResponse)
async def new_view(request: Request, db: DbSession, current=Depends(get_current_user)) -> HTMLResponse:
    suppliers = list(
        (await db.execute(SupplierRepository(db).query(is_active=True))).scalars().all()
    )
    return templates.render(
        request,
        "admin/materials/form.html",
        {
            "title": "New Material",
            "mode": "create",
            "material": None,
            "suppliers": suppliers,
            **_catalog_context(),
        },
    )


@router.post("")
async def create_submit(request: Request, db: DbSession, current=Depends(get_current_user)):
    form = await request.form()
    payload = MaterialCreate(
        code=(form.get("code") or "").strip(),
        sku=(form.get("sku") or "").strip() or None,
        name=(form.get("name") or "").strip(),
        brand=(form.get("brand") or "").strip() or None,
        category=(form.get("category") or "").strip(),
        purchase_unit=(form.get("purchase_unit") or "").strip(),
        stock_unit=(form.get("stock_unit") or "").strip(),
        stock_units_per_purchase=float(form.get("stock_units_per_purchase") or 0),
        current_purchase_price=float(form.get("current_purchase_price") or 0),
        reorder_point=float(form.get("reorder_point") or 0),
        min_stock=float(form.get("min_stock") or 0),
        preferred_supplier_id=(UUID(form["preferred_supplier_id"]) if form.get("preferred_supplier_id") else None),
        location=(form.get("location") or "").strip() or None,
        notes=(form.get("notes") or "").strip() or None,
    )
    try:
        material = await MaterialService(db).create(payload, actor=current)
    except AppError as exc:
        await db.rollback()
        suppliers = list(
            (await db.execute(SupplierRepository(db).query(is_active=True))).scalars().all()
        )
        return templates.render(
            request,
            "admin/materials/form.html",
            {
                "title": "New Material",
                "mode": "create",
                "material": None,
                "suppliers": suppliers,
                "error": exc.message,
                "form_values": dict(form),
                **_catalog_context(),
            },
            status_code=exc.status_code,
        )
    await db.commit()
    return RedirectResponse(url=f"/admin/materials/{material.id}", status_code=303)


@router.get("/{material_id}", response_class=HTMLResponse)
async def detail_view(
    material_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
) -> HTMLResponse:
    repo = MaterialRepository(db)
    material = await repo.get(material_id)
    if not material:
        raise NotFoundError("Material not found")

    stock = await repo.current_stock(material_id)
    tx_stmt = InventoryTransactionRepository(db).query(material_id=material_id)
    tx_rows, tx_meta = await paginate(db, tx_stmt, PageParams(page=1, size=25))

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
            **_catalog_context(),
        },
    )


@router.get("/{material_id}/edit", response_class=HTMLResponse)
async def edit_view(
    material_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
) -> HTMLResponse:
    material = await MaterialRepository(db).get(material_id)
    if not material:
        raise NotFoundError("Material not found")
    suppliers = list(
        (await db.execute(SupplierRepository(db).query(is_active=True))).scalars().all()
    )
    return templates.render(
        request,
        "admin/materials/form.html",
        {
            "title": f"Edit {material.name}",
            "mode": "edit",
            "material": material,
            "suppliers": suppliers,
            **_catalog_context(),
        },
    )


@router.post("/{material_id}")
async def update_submit(
    material_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
):
    form = await request.form()
    payload = MaterialUpdate(
        sku=(form.get("sku") or "").strip() or None,
        name=(form.get("name") or "").strip() or None,
        brand=(form.get("brand") or "").strip() or None,
        category=(form.get("category") or "").strip() or None,
        purchase_unit=(form.get("purchase_unit") or "").strip() or None,
        stock_unit=(form.get("stock_unit") or "").strip() or None,
        stock_units_per_purchase=(float(form["stock_units_per_purchase"]) if form.get("stock_units_per_purchase") else None),
        reorder_point=(float(form["reorder_point"]) if form.get("reorder_point") else None),
        min_stock=(float(form["min_stock"]) if form.get("min_stock") else None),
        preferred_supplier_id=(UUID(form["preferred_supplier_id"]) if form.get("preferred_supplier_id") else None),
        location=(form.get("location") or "").strip() or None,
        notes=(form.get("notes") or "").strip() or None,
        is_active=form.get("is_active") == "true",
    )
    await MaterialService(db).update(material_id, payload, actor=current)
    await db.commit()
    return RedirectResponse(url=f"/admin/materials/{material_id}", status_code=303)


@router.post("/{material_id}/price")
async def price_submit(
    material_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
):
    form = await request.form()
    new_price = float(form.get("new_purchase_price") or 0)
    note = (form.get("note") or "").strip() or None
    await MaterialService(db).update_price(material_id, new_price, note=note, actor=current)
    await db.commit()
    return RedirectResponse(url=f"/admin/materials/{material_id}", status_code=303)


@router.post("/{material_id}/transaction")
async def transaction_submit(
    material_id: UUID, request: Request, db: DbSession, current=Depends(get_current_user)
):
    """Quick-record a stock movement from the material detail page."""
    from app.modules.inventory.schemas import InventoryTransactionCreate
    from app.modules.inventory.service import InventoryService

    form = await request.form()
    payload = InventoryTransactionCreate(
        material_id=material_id,
        transaction_type=(form.get("transaction_type") or "").strip(),
        quantity=float(form.get("quantity") or 0),
        unit_cost=(float(form["unit_cost"]) if form.get("unit_cost") else None),
        reference_note=(form.get("reference_note") or "").strip() or None,
        notes=(form.get("notes") or "").strip() or None,
    )
    await InventoryService(db).record(payload, actor=current)
    await db.commit()
    return RedirectResponse(url=f"/admin/materials/{material_id}", status_code=303)