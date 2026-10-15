"""Business rules for the inventory module.

Key guarantees:
- Stock is append-only. Transactions are never updated or deleted.
- Current stock is always computed from the transaction ledger.
- Every transaction carries the unit_cost at the time it happened.
- Purchase receipt creates PURCHASE transactions and updates material prices.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import AuditAction
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.modules.audit.service import AuditService
from app.modules.auth.models import User
from app.modules.inventory.constants import (
    INBOUND_TYPES,
    OUTBOUND_TYPES,
    PURCHASE_ORDER_STATUSES,
    TERMINAL_PO_STATUSES,
    PurchaseOrderStatus,
    ReferenceType,
    TransactionType,
)
from app.modules.inventory.models import (
    InventoryTransaction,
    Material,
    PurchaseOrder,
    PurchaseOrderItem,
    Supplier,
)
from app.modules.inventory.repository import (
    InventoryTransactionRepository,
    MaterialRepository,
    PurchaseOrderRepository,
    SupplierRepository,
)
from app.modules.inventory.schemas import (
    InventoryTransactionCreate,
    MaterialCreate,
    MaterialUpdate,
    PurchaseOrderCreate,
    PurchaseOrderItemCreate,
    PurchaseOrderItemUpdate,
    PurchaseOrderReceive,
    PurchaseOrderUpdate,
    SupplierCreate,
    SupplierUpdate,
)


# ════════════════════════════════════════════════════════════════
# SUPPLIERS
# ════════════════════════════════════════════════════════════════

class SupplierService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = SupplierRepository(db)
        self.audit = AuditService(db)

    async def create(self, payload: SupplierCreate, *, actor: User | None = None) -> Supplier:
        supplier = Supplier(
            code=await self.repo.next_code(),
            name=payload.name.strip(),
            contact_person=payload.contact_person,
            email=payload.email,
            phone=payload.phone,
            address=payload.address,
            tax_id=payload.tax_id,
            payment_terms=payload.payment_terms,
            notes=payload.notes,
            is_active=True,
        )
        await self.repo.add(supplier)
        await self.audit.log(
            action=AuditAction.CREATE,
            table_name="suppliers",
            record_id=supplier.id,
            user_id=actor.id if actor else None,
            new_data={"code": supplier.code, "name": supplier.name},
        )
        return supplier

    async def update(
        self, sid: UUID, payload: SupplierUpdate, *, actor: User
    ) -> Supplier:
        supplier = await self.repo.get(sid)
        if not supplier:
            raise NotFoundError("Supplier not found")

        # Partial update — respect model_fields_set so clearing works
        for field in payload.model_fields_set:
            value = getattr(payload, field)
            if isinstance(value, str):
                value = value.strip() or None
            setattr(supplier, field, value)

        await self.db.flush()
        await self.audit.log(
            action=AuditAction.UPDATE,
            table_name="suppliers",
            record_id=supplier.id,
            user_id=actor.id,
            new_data={"name": supplier.name},
        )
        return supplier


# ════════════════════════════════════════════════════════════════
# MATERIALS
# ════════════════════════════════════════════════════════════════

class MaterialService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = MaterialRepository(db)
        self.audit = AuditService(db)

    async def create(
        self, payload: MaterialCreate, *, actor: User | None = None
    ) -> Material:
        if await self.repo.by_code(payload.code):
            raise ConflictError(f"Material code already exists: {payload.code}")

        material = Material(
            code=payload.code.strip(),
            sku=payload.sku,
            name=payload.name.strip(),
            brand=payload.brand,
            category=payload.category,
            purchase_unit=payload.purchase_unit,
            stock_unit=payload.stock_unit,
            stock_units_per_purchase=payload.stock_units_per_purchase,
            current_purchase_price=payload.current_purchase_price,
            reorder_point=payload.reorder_point,
            min_stock=payload.min_stock,
            preferred_supplier_id=payload.preferred_supplier_id,
            notes=payload.notes,
            location=payload.location,
            is_active=True,
        )
        await self.repo.add(material)
        await self.audit.log(
            action=AuditAction.CREATE,
            table_name="materials",
            record_id=material.id,
            user_id=actor.id if actor else None,
            new_data={"code": material.code, "name": material.name},
        )
        return material

    async def update(
        self, mid: UUID, payload: MaterialUpdate, *, actor: User
    ) -> Material:
        material = await self.repo.get(mid)
        if not material:
            raise NotFoundError("Material not found")

        # Partial update — respect model_fields_set so users can clear
        # optional fields (e.g. remove a supplier or a location).
        for field in payload.model_fields_set:
            value = getattr(payload, field)
            if isinstance(value, str):
                value = value.strip() or None
            setattr(material, field, value)

        await self.db.flush()
        await self.audit.log(
            action=AuditAction.UPDATE,
            table_name="materials",
            record_id=material.id,
            user_id=actor.id,
            new_data={"code": material.code, "name": material.name},
        )
        return material

    async def update_price(
        self,
        mid: UUID,
        new_price: float,
        *,
        note: str | None,
        actor: User,
    ) -> Material:
        """Change the material's purchase price. Historical transactions keep their own cost."""
        material = await self.repo.get(mid)
        if not material:
            raise NotFoundError("Material not found")

        old = float(material.current_purchase_price)
        material.current_purchase_price = new_price
        await self.db.flush()

        await self.audit.log(
            action=AuditAction.PRICE_CHANGE,
            table_name="materials",
            record_id=material.id,
            user_id=actor.id,
            old_data={"current_purchase_price": old},
            new_data={"current_purchase_price": new_price, "note": note},
        )
        return material


# ════════════════════════════════════════════════════════════════
# INVENTORY TRANSACTIONS
# ════════════════════════════════════════════════════════════════

class InventoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.tx_repo = InventoryTransactionRepository(db)
        self.material_repo = MaterialRepository(db)
        self.audit = AuditService(db)

    async def record(
        self,
        payload: InventoryTransactionCreate,
        *,
        actor: User | None = None,
    ) -> InventoryTransaction:
        """Record a stock movement. Validates and audits the transaction."""
        material = await self.material_repo.get(payload.material_id)
        if not material:
            raise NotFoundError("Material not found")

        if payload.transaction_type not in INBOUND_TYPES | OUTBOUND_TYPES:
            raise ValidationError(f"Unknown transaction type: {payload.transaction_type}")

        # Detect negative stock but do NOT mutate the payload (Pydantic
        # objects may be shared with callers).
        notes = payload.notes
        if payload.transaction_type in OUTBOUND_TYPES:
            current = await self.material_repo.current_stock(payload.material_id)
            if payload.quantity > current:
                suffix = (
                    f"[negative stock: {current:.4g} available, "
                    f"{payload.quantity:.4g} requested]"
                )
                notes = f"{notes} {suffix}".strip() if notes else suffix

        # Default unit_cost: from the material's current price
        unit_cost = payload.unit_cost
        if unit_cost is None:
            unit_cost = material.cost_per_stock_unit

        tx = InventoryTransaction(
            material_id=payload.material_id,
            transaction_type=payload.transaction_type,
            quantity=payload.quantity,
            unit_cost=unit_cost,
            reference_type=payload.reference_type,
            reference_id=payload.reference_id,
            reference_note=payload.reference_note,
            notes=notes,
            created_by_id=actor.id if actor else None,
        )
        await self.tx_repo.add(tx)

        is_inbound = payload.transaction_type in INBOUND_TYPES
        await self.audit.log(
            action=AuditAction.STOCK_IN if is_inbound else AuditAction.STOCK_OUT,
            table_name="inventory_transactions",
            record_id=tx.id,
            user_id=actor.id if actor else None,
            new_data={
                "material_id": str(payload.material_id),
                "type": payload.transaction_type,
                "quantity": float(payload.quantity),
                "unit_cost": float(unit_cost) if unit_cost else None,
            },
        )
        return tx

    async def record_consumption(
        self,
        material_id: UUID,
        quantity: float,
        *,
        reference_type: str | None = None,
        reference_id: UUID | None = None,
        reference_note: str | None = None,
        notes: str | None = None,
        actor: User | None = None,
    ) -> InventoryTransaction:
        """
        Convenience wrapper for external modules (e.g. projects) that need
        to consume stock. Wraps `record()` with sane defaults.
        """
        return await self.record(
            InventoryTransactionCreate(
                material_id=material_id,
                transaction_type=TransactionType.CONSUMPTION.value,
                quantity=quantity,
                reference_type=reference_type,
                reference_id=reference_id,
                reference_note=reference_note,
                notes=notes,
            ),
            actor=actor,
        )

    async def ensure_available(
        self,
        material_id: UUID,
        quantity: float,
        *,
        allow_negative: bool = False,
    ) -> None:
        """
        Raise ValidationError if the material does not have enough stock.
        Holds a row-level lock on the material so concurrent transactions
        cannot race past the check.
        """
        material = await self.material_repo.get(material_id)
        if not material:
            raise NotFoundError("Material not found")

        current = await self.material_repo.current_stock_for_update(material_id)
        if not allow_negative and quantity > current:
            raise ValidationError(
                f"Insufficient stock for {material.code}: "
                f"need {quantity:.4g} {material.stock_unit}, "
                f"have {current:.4g}"
            )

    async def stock_overview(self) -> list[dict]:
        """Return all active materials with current stock and value."""
        materials = list(
            (await self.db.execute(
                self.material_repo.query(is_active=True)
            )).scalars().all()
        )
        if not materials:
            return []

        ids = [m.id for m in materials]
        stock_map = await self.tx_repo.stock_for_materials(ids)

        result = []
        for m in materials:
            stock = stock_map.get(m.id, 0.0)
            unit_cost = m.cost_per_stock_unit
            result.append({
                "material": m,
                "current_stock": stock,
                "cost_per_stock_unit": unit_cost,
                "stock_value": stock * unit_cost,
                "below_reorder": stock <= float(m.reorder_point),
                "below_min": stock <= float(m.min_stock),
            })
        return result


# ════════════════════════════════════════════════════════════════
# PURCHASE ORDERS
# ════════════════════════════════════════════════════════════════

class PurchaseOrderService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = PurchaseOrderRepository(db)
        self.material_repo = MaterialRepository(db)
        self.tx_repo = InventoryTransactionRepository(db)
        self.audit = AuditService(db)

    async def create(
        self, payload: PurchaseOrderCreate, *, actor: User
    ) -> PurchaseOrder:
        supplier = await SupplierRepository(self.db).get(payload.supplier_id)
        if not supplier:
            raise NotFoundError("Supplier not found")

        po = PurchaseOrder(
            code=await self.repo.next_code(),
            supplier_id=payload.supplier_id,
            status=PurchaseOrderStatus.DRAFT.value,
            order_date=payload.order_date,
            expected_date=payload.expected_date,
            notes=payload.notes,
            created_by_id=actor.id,
        )
        await self.repo.add(po)
        await self.audit.log(
            action=AuditAction.CREATE,
            table_name="purchase_orders",
            record_id=po.id,
            user_id=actor.id,
            new_data={"code": po.code, "supplier_id": str(payload.supplier_id)},
        )
        await self.db.refresh(po, ["items"])
        return po

    async def update(
        self, po_id: UUID, payload: PurchaseOrderUpdate, *, actor: User
    ) -> PurchaseOrder:
        po = await self._get_or_404(po_id)
        if po.status in TERMINAL_PO_STATUSES:
            raise ConflictError(f"Cannot edit {po.status} purchase order")

        # Partial update — respect model_fields_set so users can clear notes
        for field in payload.model_fields_set:
            value = getattr(payload, field)
            if isinstance(value, str):
                value = value.strip() or None
            setattr(po, field, value)

        await self.db.flush()
        return po

    async def add_item(
        self,
        po_id: UUID,
        payload: PurchaseOrderItemCreate,
        *,
        actor: User,
    ) -> PurchaseOrderItem:
        po = await self._get_or_404(po_id)
        if po.status not in (PurchaseOrderStatus.DRAFT.value, PurchaseOrderStatus.SENT.value):
            raise ConflictError(f"Cannot add items to a {po.status} PO")

        material = await self.material_repo.get(payload.material_id)
        if not material:
            raise NotFoundError("Material not found")

        item = PurchaseOrderItem(
            purchase_order_id=po.id,
            material_id=payload.material_id,
            quantity=payload.quantity,
            unit_price=payload.unit_price,
            notes=payload.notes,
        )
        await self.repo.add_item(item)
        await self.repo.recalc_total(po.id)
        return item

    async def update_item(
        self,
        po_id: UUID,
        item_id: UUID,
        payload: PurchaseOrderItemUpdate,
        *,
        actor: User,
    ) -> PurchaseOrderItem:
        po = await self._get_or_404(po_id)
        if po.status not in (PurchaseOrderStatus.DRAFT.value, PurchaseOrderStatus.SENT.value):
            raise ConflictError(f"Cannot edit items of a {po.status} PO")

        item = await self.repo.get_item(item_id)
        if not item or item.purchase_order_id != po.id:
            raise NotFoundError("Purchase order item not found")

        for field in payload.model_fields_set:
            value = getattr(payload, field)
            if isinstance(value, str):
                value = value.strip() or None
            setattr(item, field, value)

        await self.db.flush()
        await self.repo.recalc_total(po.id)
        return item

    async def delete_item(
        self, po_id: UUID, item_id: UUID, *, actor: User
    ) -> None:
        po = await self._get_or_404(po_id)
        if po.status != PurchaseOrderStatus.DRAFT.value:
            raise ConflictError("Only DRAFT purchase orders can have items removed")

        item = await self.repo.get_item(item_id)
        if not item or item.purchase_order_id != po.id:
            raise NotFoundError("Purchase order item not found")

        await self.repo.delete_item(item)
        await self.repo.recalc_total(po.id)

    async def send(self, po_id: UUID, *, actor: User) -> PurchaseOrder:
        po = await self._get_or_404(po_id)
        if po.status != PurchaseOrderStatus.DRAFT.value:
            raise ConflictError(f"Cannot send a {po.status} PO")
        if not po.items:
            raise ConflictError("Cannot send an empty purchase order")

        po.status = PurchaseOrderStatus.SENT.value
        await self.db.flush()
        await self.audit.log(
            action=AuditAction.STATUS_CHANGE,
            table_name="purchase_orders",
            record_id=po.id,
            user_id=actor.id,
            old_data={"status": PurchaseOrderStatus.DRAFT.value},
            new_data={"status": PurchaseOrderStatus.SENT.value},
        )
        return po

    async def receive(
        self,
        po_id: UUID,
        payload: PurchaseOrderReceive,
        *,
        actor: User,
    ) -> PurchaseOrder:
        """
        Receive stock. Creates a PURCHASE transaction for each line item,
        updates the material's current purchase price to the received price,
        and marks the PO as RECEIVED.
        """
        po = await self._get_or_404(po_id)
        if po.status not in (PurchaseOrderStatus.SENT.value, PurchaseOrderStatus.DRAFT.value):
            raise ConflictError(f"Cannot receive a {po.status} PO")

        overrides = {ri.item_id: ri.quantity_received for ri in payload.received_items}

        # Pre-validate overrides
        for ri in payload.received_items:
            item = next((i for i in po.items if i.id == ri.item_id), None)
            if not item:
                raise ValidationError(f"Item {ri.item_id} does not belong to this PO")
            if ri.quantity_received > float(item.quantity):
                raise ValidationError(
                    f"Received quantity ({ri.quantity_received}) cannot exceed "
                    f"ordered quantity ({float(item.quantity)}) for {item.material_id}"
                )

        now = datetime.now(UTC)
        for item in po.items:
            # Already received → skip (idempotent)
            if float(item.quantity_received) > 0:
                continue

            qty = overrides.get(item.id, float(item.quantity))
            if qty <= 0:
                continue

            material = await self.material_repo.get(item.material_id)
            if not material:
                raise NotFoundError(f"Material for PO item {item.id} disappeared")

            # Quantity to add to stock is in *stock units*
            stock_qty = qty * float(material.stock_units_per_purchase)
            cost_per_stock_unit = (
                float(item.unit_price) / float(material.stock_units_per_purchase)
            )

            tx = InventoryTransaction(
                material_id=item.material_id,
                transaction_type=TransactionType.PURCHASE.value,
                quantity=stock_qty,
                unit_cost=cost_per_stock_unit,
                reference_type=ReferenceType.PURCHASE_ORDER.value,
                reference_id=po.id,
                reference_note=po.code,
                created_by_id=actor.id,
            )
            await self.tx_repo.add(tx)

            # Update the material's current price to the latest received price
            material.current_purchase_price = float(item.unit_price)
            item.quantity_received = qty

        po.status = PurchaseOrderStatus.RECEIVED.value
        po.received_at = now
        await self.db.flush()

        await self.audit.log(
            action=AuditAction.STOCK_IN,
            table_name="purchase_orders",
            record_id=po.id,
            user_id=actor.id,
            new_data={
                "status": po.status,
                "item_count": len(po.items),
                "received_at": now.isoformat(),
            },
        )
        return po

    async def close(self, po_id: UUID, *, actor: User) -> PurchaseOrder:
        po = await self._get_or_404(po_id)
        if po.status != PurchaseOrderStatus.RECEIVED.value:
            raise ConflictError("Only RECEIVED purchase orders can be closed")
        po.status = PurchaseOrderStatus.CLOSED.value
        await self.db.flush()
        return po

    async def cancel(self, po_id: UUID, *, actor: User) -> PurchaseOrder:
        po = await self._get_or_404(po_id)
        if po.status in TERMINAL_PO_STATUSES:
            raise ConflictError(f"Cannot cancel a {po.status} PO")
        if po.status == PurchaseOrderStatus.RECEIVED.value:
            raise ConflictError("Received purchase orders cannot be cancelled; use returns")
        po.status = PurchaseOrderStatus.CANCELLED.value
        await self.db.flush()
        await self.audit.log(
            action=AuditAction.STATUS_CHANGE,
            table_name="purchase_orders",
            record_id=po.id,
            user_id=actor.id,
            new_data={"status": po.status},
        )
        return po

    async def _get_or_404(self, po_id: UUID) -> PurchaseOrder:
        po = await self.repo.get(po_id)
        if not po:
            raise NotFoundError("Purchase order not found")
        return po