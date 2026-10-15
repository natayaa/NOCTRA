"""Admin web routes for inventory overview + global ledger."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse

from app.core.deps import DbSession
from app.core.exceptions import AppError
from app.core.pagination import PageParams, paginate, page_params
from app.modules.auth.dependencies import get_current_user
from app.modules.inventory.constants import (
    MATERIAL_CATEGORIES,
    MATERIAL_CATEGORY_LABELS,
    MATERIAL_CATEGORY_TONE,
    MATERIAL_SORT_OPTIONS,
    TRANSACTION_SORT_OPTIONS,
    TRANSACTION_TYPE_LABELS,
    TRANSACTION_TYPE_TONE,
    TRANSACTION_TYPES,
    signed_quantity,
)
from app.modules.inventory.repository import (
    InventoryTransactionRepository,
    MaterialRepository,
)
from app.modules.inventory.service import InventoryService
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/inventory", tags=["admin-inventory"])

_FORM_ERRORS = (AppError, ValueError, KeyError)


# ════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════

def _catalog() -> dict:
    return {
        "material_categories": MATERIAL_CATEGORIES,
        "category_labels": MATERIAL_CATEGORY_LABELS,
        "category_tone": MATERIAL_CATEGORY_TONE,
        "material_sort_options": MATERIAL_SORT_OPTIONS,
        "transaction_types": TRANSACTION_TYPES,
        "transaction_type_labels": TRANSACTION_TYPE_LABELS,
        "transaction_type_tone": TRANSACTION_TYPE_TONE,
        "transaction_sort_options": TRANSACTION_SORT_OPTIONS,
        "signed_quantity": signed_quantity,
    }


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


# ════════════════════════════════════════════════════════════════
# OVERVIEW
# ════════════════════════════════════════════════════════════════

@router.get("", response_class=HTMLResponse)
async def overview(
    request: Request,
    db: DbSession,
    q: str | None = Query(None, max_length=200),
    category: str | None = Query(None),
    low_stock: bool = Query(False),
    sort: str = Query("category_name"),
    current=Depends(get_current_user),
) -> HTMLResponse:
    # Load full overview and filter in memory (inventory is small; the
    # overview already loads all active materials in one query).
    rows = await InventoryService(db).stock_overview()

    # Apply filters
    if q:
        needle = q.strip().lower()
        rows = [
            r for r in rows
            if needle in (r["material"].name or "").lower()
            or needle in (r["material"].code or "").lower()
            or needle in (r["material"].brand or "").lower()
        ]
    if category:
        rows = [r for r in rows if r["material"].category == category]
    if low_stock:
        rows = [r for r in rows if r["below_reorder"]]

    # Apply sort
    if sort == "name_asc":
        rows.sort(key=lambda r: (r["material"].name or "").lower())
    elif sort == "name_desc":
        rows.sort(key=lambda r: (r["material"].name or "").lower(), reverse=True)
    elif sort == "code_asc":
        rows.sort(key=lambda r: (r["material"].code or "").lower())
    elif sort == "created_desc":
        rows.sort(key=lambda r: r["material"].created_at or datetime.min, reverse=True)
    else:  # category_name
        rows.sort(key=lambda r: (
            (r["material"].category or "").lower(),
            (r["material"].name or "").lower(),
        ))

    total_value = sum(r["stock_value"] for r in rows)

    # Count low stock across ALL materials (not just filtered)
    all_rows = await InventoryService(db).stock_overview()
    low_stock_count = sum(1 for r in all_rows if r["below_reorder"])
    below_min_count = sum(1 for r in all_rows if r["below_min"])

    # Stats per category (only count filtered/visible)
    by_category: dict[str, dict] = {}
    for r in rows:
        cat = r["material"].category
        bucket = by_category.setdefault(cat, {"count": 0, "value": 0.0})
        bucket["count"] += 1
        bucket["value"] += r["stock_value"]

    def _qs(**overrides) -> str:
        from urllib.parse import urlencode
        base = {
            "q": q or "", "category": category or "",
            "low_stock": "true" if low_stock else "", "sort": sort,
        }
        base.update({k: ("" if v is None else v) for k, v in overrides.items()})
        return "?" + urlencode({k: v for k, v in base.items() if v})

    return templates.render(
        request,
        "admin/inventory/overview.html",
        {
            "title": "Inventory",
            "items": rows,
            "total_value": total_value,
            "low_stock_count": low_stock_count,
            "below_min_count": below_min_count,
            "by_category": by_category,
            "q": q or "",
            "category_filter": category or "",
            "low_stock_filter": low_stock,
            "sort": sort,
            "qs": _qs,
            "all_categories": MATERIAL_CATEGORIES,
            **_catalog(),
        },
    )


# ════════════════════════════════════════════════════════════════
# OVERVIEW CSV EXPORT
# ════════════════════════════════════════════════════════════════

@router.get("/export.csv")
async def export_stock_csv(
    db: DbSession,
    q: str | None = Query(None),
    category: str | None = Query(None),
    low_stock: bool = Query(False),
    current=Depends(get_current_user),
):
    rows = await InventoryService(db).stock_overview()

    if q:
        needle = q.strip().lower()
        rows = [
            r for r in rows
            if needle in (r["material"].name or "").lower()
            or needle in (r["material"].code or "").lower()
            or needle in (r["material"].brand or "").lower()
        ]
    if category:
        rows = [r for r in rows if r["material"].category == category]
    if low_stock:
        rows = [r for r in rows if r["below_reorder"]]

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "code", "name", "brand", "category",
        "current_stock", "stock_unit",
        "cost_per_stock_unit", "stock_value",
        "reorder_point", "min_stock",
        "location", "below_reorder", "below_min",
    ])
    for r in rows:
        m = r["material"]
        writer.writerow([
            m.code, m.name, m.brand or "", m.category,
            f"{r['current_stock']:.4f}", m.stock_unit,
            f"{r['cost_per_stock_unit']:.2f}", f"{r['stock_value']:.2f}",
            f"{float(m.reorder_point):.4f}", f"{float(m.min_stock):.4f}",
            m.location or "",
            "yes" if r["below_reorder"] else "no",
            "yes" if r["below_min"] else "no",
        ])

    buf.seek(0)
    filename = f"inventory-{datetime.utcnow().strftime('%Y%m%d-%H%M')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ════════════════════════════════════════════════════════════════
# LEDGER
# ════════════════════════════════════════════════════════════════

@router.get("/transactions", response_class=HTMLResponse)
async def ledger(
    request: Request,
    db: DbSession,
    params: PageParams = Depends(page_params),
    material_id: UUID | None = Query(None),
    transaction_type: str | None = Query(None),
    reference_type: str | None = Query(None),
    sort: str = Query("created_desc"),
    current=Depends(get_current_user),
) -> HTMLResponse:
    tx_repo = InventoryTransactionRepository(db)
    stmt = tx_repo.query(
        material_id=material_id,
        transaction_type=transaction_type,
        reference_type=reference_type,
        sort=sort if sort in TRANSACTION_SORT_OPTIONS else "created_desc",
    )
    rows, meta = await paginate(db, stmt, params)

    # Only load materials referenced in this page (not all)
    material_ids = {t.material_id for t in rows}
    mat_map: dict = {}
    if material_ids:
        from sqlalchemy import select
        from app.modules.inventory.models import Material
        m_rows = await db.execute(select(Material).where(Material.id.in_(material_ids)))
        mat_map = {m.id: m for m in m_rows.scalars().all()}

    # For filter dropdown, only load a lightweight list
    all_materials = list(
        (await db.execute(
            MaterialRepository(db).query(is_active=None, sort="category_name")
        )).scalars().all()
    )

    def _qs(**overrides) -> str:
        from urllib.parse import urlencode
        base = {
            "material_id": str(material_id) if material_id else "",
            "transaction_type": transaction_type or "",
            "reference_type": reference_type or "",
            "sort": sort,
        }
        base.update({k: ("" if v is None else v) for k, v in overrides.items()})
        return "?" + urlencode({k: v for k, v in base.items() if v})

    return templates.render(
        request,
        "admin/inventory/transactions.html",
        {
            "title": "Inventory Ledger",
            "transactions": rows,
            "page_meta": meta,
            "materials_by_id": mat_map,
            "all_materials": all_materials,
            "material_filter": material_id,
            "type_filter": transaction_type or "",
            "ref_filter": reference_type or "",
            "sort": sort,
            "qs": _qs,
            **_catalog(),
        },
    )


# ════════════════════════════════════════════════════════════════
# LEDGER CSV EXPORT
# ════════════════════════════════════════════════════════════════

@router.get("/transactions/export.csv")
async def export_ledger_csv(
    db: DbSession,
    material_id: UUID | None = Query(None),
    transaction_type: str | None = Query(None),
    reference_type: str | None = Query(None),
    current=Depends(get_current_user),
):
    from sqlalchemy import select
    from app.modules.inventory.models import Material

    stmt = InventoryTransactionRepository(db).query(
        material_id=material_id,
        transaction_type=transaction_type,
        reference_type=reference_type,
        sort="created_desc",
    )
    rows = (await db.execute(stmt)).scalars().all()

    mat_ids = {t.material_id for t in rows}
    mat_map: dict = {}
    if mat_ids:
        m_rows = await db.execute(select(Material).where(Material.id.in_(mat_ids)))
        mat_map = {m.id: m for m in m_rows.scalars().all()}

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "created_at", "material_code", "material_name",
        "transaction_type", "quantity", "stock_unit",
        "signed_quantity", "unit_cost",
        "reference_type", "reference_note", "notes",
    ])
    for t in rows:
        m = mat_map.get(t.material_id)
        writer.writerow([
            t.created_at.isoformat() if t.created_at else "",
            m.code if m else "",
            m.name if m else "",
            t.transaction_type,
            f"{float(t.quantity):.4f}",
            m.stock_unit if m else "",
            f"{signed_quantity(t.transaction_type, float(t.quantity)):.4f}",
            f"{float(t.unit_cost):.2f}" if t.unit_cost is not None else "",
            t.reference_type or "",
            t.reference_note or "",
            t.notes or "",
        ])

    buf.seek(0)
    filename = f"inventory-ledger-{datetime.utcnow().strftime('%Y%m%d-%H%M')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )