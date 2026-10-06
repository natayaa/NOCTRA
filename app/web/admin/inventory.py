"""Admin web routes for inventory overview + global ledger."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse

from app.core.deps import DbSession
from app.core.pagination import PageParams, paginate, page_params
from app.modules.auth.dependencies import get_current_user
from app.modules.inventory.constants import (
    MATERIAL_CATEGORIES,
    MATERIAL_CATEGORY_LABELS,
    TRANSACTION_TYPE_LABELS,
    TRANSACTION_TYPES,
)
from app.modules.inventory.repository import (
    InventoryTransactionRepository,
    MaterialRepository,
)
from app.modules.inventory.service import InventoryService
from app.web.templates_env import templates

router = APIRouter(prefix="/admin/inventory", tags=["admin-inventory"])


@router.get("", response_class=HTMLResponse)
async def overview(
    request: Request, db: DbSession, current=Depends(get_current_user)
) -> HTMLResponse:
    rows = await InventoryService(db).stock_overview()
    total_value = sum(r["stock_value"] for r in rows)
    low_stock = [r for r in rows if r["below_reorder"]]

    return templates.render(
        request,
        "admin/inventory/overview.html",
        {
            "title": "Inventory",
            "items": rows,
            "total_value": total_value,
            "low_stock_count": len(low_stock),
            "category_labels": MATERIAL_CATEGORY_LABELS,
        },
    )


@router.get("/transactions", response_class=HTMLResponse)
async def ledger(
    request: Request,
    db: DbSession,
    params: PageParams = Depends(page_params),
    material_id: UUID | None = Query(None),
    transaction_type: str | None = Query(None),
    current=Depends(get_current_user),
) -> HTMLResponse:
    stmt = InventoryTransactionRepository(db).query(
        material_id=material_id, transaction_type=transaction_type
    )
    rows, meta = await paginate(db, stmt, params)

    # Load materials for display
    materials = list(
        (await db.execute(MaterialRepository(db).query(is_active=None))).scalars().all()
    )
    mat_map = {m.id: m for m in materials}

    return templates.render(
        request,
        "admin/inventory/transactions.html",
        {
            "title": "Inventory Ledger",
            "transactions": rows,
            "page_meta": meta,
            "materials_by_id": mat_map,
            "all_materials": materials,
            "transaction_types": TRANSACTION_TYPES,
            "transaction_type_labels": TRANSACTION_TYPE_LABELS,
            "material_filter": material_id,
            "type_filter": transaction_type or "",
        },
    )