"""Read/write helpers for the inventory module."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, and_, case, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.modules.inventory.constants import (
    INBOUND_TYPES,
    PO_SORT_OPTIONS,
    TRANSACTION_SORT_OPTIONS,
)
from app.modules.inventory.models import (
    InventoryTransaction,
    Material,
    PurchaseOrder,
    PurchaseOrderItem,
    Supplier,
)


# ════════════════════════════════════════════════════════════════
# SUPPLIERS
# ════════════════════════════════════════════════════════════════

class SupplierRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, sid: UUID) -> Supplier | None:
        return await self.db.get(Supplier, sid)

    async def by_code(self, code: str) -> Supplier | None:
        stmt = select(Supplier).where(Supplier.code == code)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    def query(
        self,
        *,
        q: str | None = None,
        is_active: bool | None = None,
    ) -> Select:
        stmt = select(Supplier)
        conds = []
        if q:
            like = f"%{q.strip()}%"
            conds.append(
                or_(
                    Supplier.name.ilike(like),
                    Supplier.code.ilike(like),
                    Supplier.phone.ilike(like),
                    Supplier.email.ilike(like),
                )
            )
        if is_active is not None:
            conds.append(Supplier.is_active == is_active)
        if conds:
            stmt = stmt.where(and_(*conds))
        # Stable secondary sort prevents pagination drift on name ties.
        return stmt.order_by(Supplier.name.asc(), Supplier.id.asc())

    async def next_code(self) -> str:
        """
        Generate SUP-YYYY-NNNN under an advisory lock. Serialises concurrent
        creation so the unique constraint cannot collide.
        """
        year = datetime.now(UTC).year
        prefix = f"SUP-{year}-"

        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
            {"key": prefix},
        )

        stmt = (
            select(Supplier.code)
            .where(Supplier.code.like(f"{prefix}%"))
            .order_by(Supplier.code.desc())
            .limit(1)
        )
        last = (await self.db.execute(stmt)).scalar_one_or_none()
        n = 1 if last is None else int(last.rsplit("-", 1)[-1]) + 1
        return f"{prefix}{n:04d}"

    async def add(self, supplier: Supplier) -> Supplier:
        self.db.add(supplier)
        await self.db.flush()
        return supplier


# ════════════════════════════════════════════════════════════════
# MATERIALS
# ════════════════════════════════════════════════════════════════

class MaterialRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, mid: UUID) -> Material | None:
        return await self.db.get(Material, mid)

    async def by_code(self, code: str) -> Material | None:
        stmt = select(Material).where(Material.code == code)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    def query(
        self,
        *,
        q: str | None = None,
        category: str | None = None,
        is_active: bool | None = None,
        sort: str = "category_name",
    ) -> Select:
        stmt = select(Material)
        conds = []
        if q:
            like = f"%{q.strip()}%"
            conds.append(
                or_(
                    Material.name.ilike(like),
                    Material.code.ilike(like),
                    Material.brand.ilike(like),
                    Material.sku.ilike(like),
                )
            )
        if category:
            conds.append(Material.category == category)
        if is_active is not None:
            conds.append(Material.is_active == is_active)
        if conds:
            stmt = stmt.where(and_(*conds))

        # Stable secondary sort on id for all orders.
        if sort == "name_asc":
            stmt = stmt.order_by(Material.name.asc(), Material.id.asc())
        elif sort == "name_desc":
            stmt = stmt.order_by(Material.name.desc(), Material.id.asc())
        elif sort == "code_asc":
            stmt = stmt.order_by(Material.code.asc())
        elif sort == "created_desc":
            stmt = stmt.order_by(Material.created_at.desc(), Material.id.asc())
        else:  # category_name (default)
            stmt = stmt.order_by(
                Material.category.asc(), Material.name.asc(), Material.id.asc()
            )

        return stmt

    async def add(self, material: Material) -> Material:
        self.db.add(material)
        await self.db.flush()
        return material

    async def current_stock(self, material_id: UUID) -> float:
        """Return current stock in stock units for one material."""
        stmt = (
            select(
                func.coalesce(
                    func.sum(
                        case(
                            (InventoryTransaction.transaction_type.in_(INBOUND_TYPES),
                             InventoryTransaction.quantity),
                            else_=-InventoryTransaction.quantity,
                        )
                    ),
                    0,
                )
            )
            .where(InventoryTransaction.material_id == material_id)
        )
        result = (await self.db.execute(stmt)).scalar_one()
        return float(result or 0)

    async def current_stock_for_update(self, material_id: UUID) -> float:
        """
        Return current stock while holding a row-level lock on the material.
        Use inside a transaction to prevent concurrent consumption from
        racing past the stock check.
        """
        await self.db.execute(
            select(Material.id).where(Material.id == material_id).with_for_update()
        )
        return await self.current_stock(material_id)

    async def has_transactions(self, material_id: UUID) -> bool:
        """True if the material has at least one inventory transaction."""
        stmt = (
            select(func.count(InventoryTransaction.id))
            .where(InventoryTransaction.material_id == material_id)
            .limit(1)
        )
        return bool((await self.db.execute(stmt)).scalar_one())

    async def distinct_categories(self) -> list[str]:
        stmt = (
            select(Material.category)
            .where(Material.category.is_not(None))
            .distinct()
            .order_by(Material.category)
        )
        return [c for (c,) in (await self.db.execute(stmt)).all() if c]

    async def stats(self) -> dict[str, int]:
        """Aggregate counts for overview header."""
        total_stmt = select(func.count(Material.id))
        active_stmt = select(func.count(Material.id)).where(Material.is_active.is_(True))

        total = (await self.db.execute(total_stmt)).scalar_one()
        active = (await self.db.execute(active_stmt)).scalar_one()

        cat_stmt = (
            select(Material.category, func.count(Material.id))
            .where(Material.is_active.is_(True))
            .group_by(Material.category)
        )
        by_cat = {c: n for c, n in (await self.db.execute(cat_stmt)).all() if c}

        return {
            "total": total,
            "active": active,
            **{f"cat_{k}": v for k, v in by_cat.items()},
        }


# ════════════════════════════════════════════════════════════════
# INVENTORY TRANSACTIONS
# ════════════════════════════════════════════════════════════════

class InventoryTransactionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, tx_id: UUID) -> InventoryTransaction | None:
        return await self.db.get(InventoryTransaction, tx_id)

    def query(
        self,
        *,
        material_id: UUID | None = None,
        transaction_type: str | None = None,
        reference_type: str | None = None,
        reference_id: UUID | None = None,
        since: datetime | None = None,
        sort: str = "created_desc",
    ) -> Select:
        stmt = select(InventoryTransaction)
        conds = []
        if material_id:
            conds.append(InventoryTransaction.material_id == material_id)
        if transaction_type:
            conds.append(InventoryTransaction.transaction_type == transaction_type)
        if reference_type:
            conds.append(InventoryTransaction.reference_type == reference_type)
        if reference_id is not None:
            conds.append(InventoryTransaction.reference_id == reference_id)
        if since:
            conds.append(InventoryTransaction.created_at >= since)
        if conds:
            stmt = stmt.where(and_(*conds))

        # Stable secondary sort on id prevents pagination drift when many
        # transactions share a timestamp (bulk consumption / PO receive).
        if sort == "created_asc":
            stmt = stmt.order_by(
                InventoryTransaction.created_at.asc(), InventoryTransaction.id.asc()
            )
        else:
            stmt = stmt.order_by(
                InventoryTransaction.created_at.desc(), InventoryTransaction.id.desc()
            )
        return stmt

    async def add(self, tx: InventoryTransaction) -> InventoryTransaction:
        self.db.add(tx)
        await self.db.flush()
        return tx

    async def stock_for_materials(self, ids: list[UUID]) -> dict[UUID, float]:
        """Batch stock query for the overview page."""
        if not ids:
            return {}
        stmt = (
            select(
                InventoryTransaction.material_id,
                func.coalesce(
                    func.sum(
                        case(
                            (InventoryTransaction.transaction_type.in_(INBOUND_TYPES),
                             InventoryTransaction.quantity),
                            else_=-InventoryTransaction.quantity,
                        )
                    ),
                    0,
                ).label("stock"),
            )
            .where(InventoryTransaction.material_id.in_(ids))
            .group_by(InventoryTransaction.material_id)
        )
        rows = (await self.db.execute(stmt)).all()
        return {row.material_id: float(row.stock) for row in rows}

    async def stats(self, *, material_id: UUID | None = None) -> dict[str, int]:
        """Counts per transaction type, optionally scoped to a material."""
        stmt = (
            select(
                InventoryTransaction.transaction_type,
                func.count(InventoryTransaction.id),
            )
            .group_by(InventoryTransaction.transaction_type)
        )
        if material_id:
            stmt = stmt.where(InventoryTransaction.material_id == material_id)
        rows = (await self.db.execute(stmt)).all()
        return {"total": sum(n for _, n in rows), **{t: n for t, n in rows}}


# ════════════════════════════════════════════════════════════════
# PURCHASE ORDERS
# ════════════════════════════════════════════════════════════════

class PurchaseOrderRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, po_id: UUID) -> PurchaseOrder | None:
        return await self.db.get(PurchaseOrder, po_id)

    async def get_for_update(self, po_id: UUID) -> PurchaseOrder | None:
        """Load the PO with a row-level lock for the duration of the tx."""
        stmt = (
            select(PurchaseOrder)
            .where(PurchaseOrder.id == po_id)
            .with_for_update()
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def by_code(self, code: str) -> PurchaseOrder | None:
        stmt = select(PurchaseOrder).where(PurchaseOrder.code == code)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    def query(
        self,
        *,
        status: str | None = None,
        supplier_id: UUID | None = None,
        q: str | None = None,
        sort: str = "created_desc",
    ) -> Select:
        # `noload` prevents the selectin loader for items from firing —
        # list view does not need them.
        stmt = select(PurchaseOrder).options(noload(PurchaseOrder.items))
        conds = []
        if status:
            conds.append(PurchaseOrder.status == status)
        if supplier_id:
            conds.append(PurchaseOrder.supplier_id == supplier_id)
        if q:
            like = f"%{q.strip()}%"
            conds.append(
                or_(
                    PurchaseOrder.code.ilike(like),
                    PurchaseOrder.notes.ilike(like),
                )
            )
        if conds:
            stmt = stmt.where(and_(*conds))

        if sort == "created_asc":
            stmt = stmt.order_by(PurchaseOrder.created_at.asc(), PurchaseOrder.id.asc())
        elif sort == "order_desc":
            stmt = stmt.order_by(PurchaseOrder.order_date.desc(), PurchaseOrder.id.asc())
        elif sort == "expected_asc":
            stmt = stmt.order_by(
                PurchaseOrder.expected_date.asc().nulls_last(),
                PurchaseOrder.id.asc(),
            )
        else:
            stmt = stmt.order_by(
                PurchaseOrder.created_at.desc(), PurchaseOrder.id.asc()
            )
        return stmt

    async def next_code(self) -> str:
        """
        Generate PO-YYYY-NNNNN under an advisory lock. Serialises concurrent
        creation so the unique constraint cannot collide.
        """
        year = datetime.now(UTC).year
        prefix = f"PO-{year}-"

        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
            {"key": prefix},
        )

        stmt = (
            select(PurchaseOrder.code)
            .where(PurchaseOrder.code.like(f"{prefix}%"))
            .order_by(PurchaseOrder.code.desc())
            .limit(1)
        )
        last = (await self.db.execute(stmt)).scalar_one_or_none()
        n = 1 if last is None else int(last.rsplit("-", 1)[-1]) + 1
        return f"{prefix}{n:05d}"

    async def add(self, po: PurchaseOrder) -> PurchaseOrder:
        self.db.add(po)
        await self.db.flush()
        return po

    async def get_item(self, item_id: UUID) -> PurchaseOrderItem | None:
        return await self.db.get(PurchaseOrderItem, item_id)

    async def add_item(self, item: PurchaseOrderItem) -> PurchaseOrderItem:
        self.db.add(item)
        await self.db.flush()
        return item

    async def delete_item(self, item: PurchaseOrderItem) -> None:
        await self.db.delete(item)
        await self.db.flush()

    async def recalc_total(self, po_id: UUID) -> None:
        """Update the PO's total_amount from its line items."""
        stmt = select(
            func.coalesce(
                func.sum(PurchaseOrderItem.quantity * PurchaseOrderItem.unit_price),
                0,
            )
        ).where(PurchaseOrderItem.purchase_order_id == po_id)
        total = (await self.db.execute(stmt)).scalar_one()
        po = await self.get(po_id)
        if po:
            po.total_amount = float(total)
            await self.db.flush()