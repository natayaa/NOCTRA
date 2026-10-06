"""Read/write helpers for the inventory module."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.inventory.constants import (
    INBOUND_TYPES,
    OUTBOUND_TYPES,
)
from app.modules.inventory.models import (
    InventoryTransaction,
    Material,
    PurchaseOrder,
    PurchaseOrderItem,
    Supplier,
)


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
        stmt = select(Supplier).order_by(Supplier.name)
        conds = []
        if q:
            like = f"%{q.strip()}%"
            conds.append(or_(Supplier.name.ilike(like), Supplier.code.ilike(like)))
        if is_active is not None:
            conds.append(Supplier.is_active == is_active)
        if conds:
            stmt = stmt.where(and_(*conds))
        return stmt

    async def next_code(self) -> str:
        year = datetime.now(UTC).year
        prefix = f"SUP-{year}-"
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
    ) -> Select:
        stmt = select(Material).order_by(Material.category, Material.name)
        conds = []
        if q:
            like = f"%{q.strip()}%"
            conds.append(
                or_(
                    Material.name.ilike(like),
                    Material.code.ilike(like),
                    Material.brand.ilike(like),
                )
            )
        if category:
            conds.append(Material.category == category)
        if is_active is not None:
            conds.append(Material.is_active == is_active)
        if conds:
            stmt = stmt.where(and_(*conds))
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
    ) -> Select:
        stmt = select(InventoryTransaction).order_by(
            InventoryTransaction.created_at.desc()
        )
        conds = []
        if material_id:
            conds.append(InventoryTransaction.material_id == material_id)
        if transaction_type:
            conds.append(InventoryTransaction.transaction_type == transaction_type)
        if reference_type:
            conds.append(InventoryTransaction.reference_type == reference_type)
        if reference_id:
            conds.append(InventoryTransaction.reference_id == reference_id)
        if since:
            conds.append(InventoryTransaction.created_at >= since)
        if conds:
            stmt = stmt.where(and_(*conds))
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


class PurchaseOrderRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, po_id: UUID) -> PurchaseOrder | None:
        return await self.db.get(PurchaseOrder, po_id)

    async def by_code(self, code: str) -> PurchaseOrder | None:
        stmt = select(PurchaseOrder).where(PurchaseOrder.code == code)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    def query(
        self,
        *,
        status: str | None = None,
        supplier_id: UUID | None = None,
    ) -> Select:
        stmt = select(PurchaseOrder).order_by(PurchaseOrder.created_at.desc())
        conds = []
        if status:
            conds.append(PurchaseOrder.status == status)
        if supplier_id:
            conds.append(PurchaseOrder.supplier_id == supplier_id)
        if conds:
            stmt = stmt.where(and_(*conds))
        return stmt

    async def next_code(self) -> str:
        year = datetime.now(UTC).year
        prefix = f"PO-{year}-"
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
            func.coalesce(func.sum(PurchaseOrderItem.quantity * PurchaseOrderItem.unit_price), 0)
        ).where(PurchaseOrderItem.purchase_order_id == po_id)
        total = (await self.db.execute(stmt)).scalar_one()
        po = await self.get(po_id)
        if po:
            po.total_amount = float(total)
            await self.db.flush()