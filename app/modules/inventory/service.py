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

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import AuditAction
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.modules.audit.service import AuditService
from app.modules.auth.models import User
from app.modules.inventory.constants import (
    INBOUND_TYPES,
    OUTBOUND_TYPES,
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
            name=payload.name,          # already stripped by schema
            contact_person=payload.contact_person,
            email=str(payload.email) if payload.email else None,
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

        for field in payload.model_fields_set:
            value = getattr(payload, field)
            if isinstance(value, str):
                value = value.strip() or None
            if field == "email" and value is not None:
                value = str(value)
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

_IMMUTABLE_AFTER_TX = frozenset({
    "stock_units_per_purchase",
    "stock_unit",
    "purchase_unit",
})


class MaterialService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = MaterialRepository(db)
        self.audit = AuditService(db)

    async def create(
        self, payload: MaterialCreate, *, actor: User | None = None
    ) -> Material:
        # Schema already strips; strip here too in case this service is
        # invoked directly (tests, seeds, internal callers).
        code = payload.code.strip()
        name = payload.name.strip()

        if await self.repo.by_code(code):
            raise ConflictError(f"Material code already exists: {code}")

        if payload.preferred_supplier_id is not None:
            if not await SupplierRepository(self.db).get(payload.preferred_supplier_id):
                raise NotFoundError("Preferred supplier not found")

        material = Material(
            code=code,
            sku=payload.sku,
            name=name,
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
        try:
            await self.repo.add(material)
        except IntegrityError as exc:
            # Lost the race — another request created the same code between
            # `by_code` and this flush. Surface as 409, not 500.
            await self.db.rollback()
            raise ConflictError(
                f"Material code already exists: {code}"
            ) from exc

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

        # Validate FK BEFORE mutating — DBSessionMiddleware commits the
        # session on AppError, so a mid-loop IntegrityError would leave
        # partial changes committed. (Well, on IntegrityError we rollback;
        # but validating up-front is cleaner and produces a proper 404.)
        if "preferred_supplier_id" in payload.model_fields_set:
            sid = payload.preferred_supplier_id
            if sid is not None:
                if not await SupplierRepository(self.db).get(sid):
                    raise NotFoundError("Preferred supplier not found")

        immutable_touched = _IMMUTABLE_AFTER_TX.intersection(payload.model_fields_set)
        if immutable_touched:
            if await self.repo.has_transactions(mid):
                raise ConflictError(
                    f"Cannot change {', '.join(sorted(immutable_touched))} on a "
                    f"material that already has transactions. Create a new "
                    f"material with the corrected units instead."
                )

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
# INVENTORY TRANSACTIONS (unchanged)
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
        strict_stock: bool = False,
        occurred_at: datetime | None = None,
    ) -> InventoryTransaction:
        material = await self.material_repo.get(payload.material_id)
        if not material:
            raise NotFoundError("Material not found")

        if payload.transaction_type not in INBOUND_TYPES | OUTBOUND_TYPES:
            raise ValidationError(f"Unknown transaction type: {payload.transaction_type}")

        is_outbound = payload.transaction_type in OUTBOUND_TYPES
        notes = payload.notes

        if is_outbound:
            if strict_stock:
                current = await self.material_repo.current_stock_for_update(
                    payload.material_id
                )
                if payload.quantity > current:
                    raise ValidationError(
                        f"Insufficient stock for {material.code}: "
                        f"need {payload.quantity:.4g} {material.stock_unit}, "
                        f"have {current:.4g}"
                    )
            else:
                current = await self.material_repo.current_stock(
                    payload.material_id
                )
                if payload.quantity > current:
                    suffix = (
                        f"[negative stock: {current:.4g} available, "
                        f"{payload.quantity:.4g} requested]"
                    )
                    notes = f"{notes} {suffix}".strip() if notes else suffix

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
            occurred_at=occurred_at or datetime.now(UTC),
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
        allow_negative: bool = True,
    ) -> InventoryTransaction:
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
            strict_stock=not allow_negative,
        )

    async def ensure_available(
        self,
        material_id: UUID,
        quantity: float,
        *,
        allow_negative: bool = False,
    ) -> None:
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
        # Lock the PO so `update` doesn't interleave with `receive`/item
        # mutations, and so the terminal-status guard is race-free.
        po = await self.repo.get_for_update(po_id)
        if not po:
            raise NotFoundError("Purchase order not found")
        await self.db.refresh(po, ["items"])

        if po.status in TERMINAL_PO_STATUSES:
            raise ConflictError(f"Cannot edit {po.status} purchase order")

        changed = {}
        for field in payload.model_fields_set:
            value = getattr(payload, field)
            if isinstance(value, str):
                value = value.strip() or None
            setattr(po, field, value)
            changed[field] = value

        await self.db.flush()
        await self.audit.log(
            action=AuditAction.UPDATE,
            table_name="purchase_orders",
            record_id=po.id,
            user_id=actor.id,
            new_data={"code": po.code, "fields": list(changed)},
        )
        return po

    async def add_item(
        self,
        po_id: UUID,
        payload: PurchaseOrderItemCreate,
        *,
        actor: User,
    ) -> PurchaseOrderItem:
        # Lock PO so we serialize with receive(). Without this, an add_item
        # racing with receive() could land a line on a PO that's about to
        # become RECEIVED, leaving that line orphaned at quantity_received=0.
        po = await self.repo.get_for_update(po_id)
        if not po:
            raise NotFoundError("Purchase order not found")
        await self.db.refresh(po, ["items"])

        if po.status not in (
            PurchaseOrderStatus.DRAFT.value,
            PurchaseOrderStatus.SENT.value,
        ):
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

        await self.audit.log(
            action=AuditAction.UPDATE,
            table_name="purchase_orders",
            record_id=po.id,
            user_id=actor.id,
            new_data={
                "action": "add_item",
                "item_id": str(item.id),
                "material_id": str(payload.material_id),
                "quantity": float(payload.quantity),
                "unit_price": float(payload.unit_price),
            },
        )
        return item

    async def update_item(
        self,
        po_id: UUID,
        item_id: UUID,
        payload: PurchaseOrderItemUpdate,
        *,
        actor: User,
    ) -> PurchaseOrderItem:
        po = await self.repo.get_for_update(po_id)
        if not po:
            raise NotFoundError("Purchase order not found")
        await self.db.refresh(po, ["items"])

        if po.status not in (
            PurchaseOrderStatus.DRAFT.value,
            PurchaseOrderStatus.SENT.value,
        ):
            raise ConflictError(f"Cannot edit items of a {po.status} PO")

        item = await self.repo.get_item(item_id)
        if not item or item.purchase_order_id != po.id:
            raise NotFoundError("Purchase order item not found")

        before = {
            "quantity": float(item.quantity),
            "unit_price": float(item.unit_price),
        }
        for field in payload.model_fields_set:
            value = getattr(payload, field)
            if isinstance(value, str):
                value = value.strip() or None
            setattr(item, field, value)

        await self.db.flush()
        await self.repo.recalc_total(po.id)

        await self.audit.log(
            action=AuditAction.UPDATE,
            table_name="purchase_orders",
            record_id=po.id,
            user_id=actor.id,
            old_data={"action": "update_item", "item_id": str(item.id), **before},
            new_data={
                "action": "update_item",
                "item_id": str(item.id),
                "quantity": float(item.quantity),
                "unit_price": float(item.unit_price),
            },
        )
        return item

    async def delete_item(
        self, po_id: UUID, item_id: UUID, *, actor: User
    ) -> None:
        po = await self.repo.get_for_update(po_id)
        if not po:
            raise NotFoundError("Purchase order not found")
        await self.db.refresh(po, ["items"])

        if po.status != PurchaseOrderStatus.DRAFT.value:
            raise ConflictError("Only DRAFT purchase orders can have items removed")

        item = await self.repo.get_item(item_id)
        if not item or item.purchase_order_id != po.id:
            raise NotFoundError("Purchase order item not found")

        snapshot = {
            "item_id": str(item.id),
            "material_id": str(item.material_id),
            "quantity": float(item.quantity),
            "unit_price": float(item.unit_price),
        }
        await self.repo.delete_item(item)
        await self.repo.recalc_total(po.id)

        await self.audit.log(
            action=AuditAction.UPDATE,
            table_name="purchase_orders",
            record_id=po.id,
            user_id=actor.id,
            old_data={"action": "delete_item", **snapshot},
        )

    async def send(self, po_id: UUID, *, actor: User) -> PurchaseOrder:
        po = await self.repo.get_for_update(po_id)
        if not po:
            raise NotFoundError("Purchase order not found")
        await self.db.refresh(po, ["items"])

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
        """Receive stock against a SENT purchase order.

        **Semantics of `received_items`:**

        - **Empty list** → receive ALL remaining quantity for every item
          that still has room (`ordered - already_received`). This is the
          "receive everything" default and matches the pre-fix behaviour.
        - **Non-empty list** → receive ONLY the listed items at the given
          quantities. Items not mentioned are left untouched (0 this call).
          This is the "partial receipt" mode and previously caused silent
          over-receipt — a mixed payload like `[{A, 5}]` on a 3-item PO
          used to auto-receive B and C at full quantity.

        `quantity_received` accumulates across calls, so multiple receives
        are safe. The PO transitions to RECEIVED automatically once every
        item's `quantity_received >= quantity`.

        Concurrency: obtains a row-level lock on the PO so two simultaneous
        `receive` calls cannot double-apply stock.
        """
        po = await self.repo.get_for_update(po_id)
        if not po:
            raise NotFoundError("Purchase order not found")
        await self.db.refresh(po, ["items"])

        if po.status != PurchaseOrderStatus.SENT.value:
            raise ConflictError(
                f"Cannot receive a {po.status} PO. "
                f"Send it first via POST /purchase-orders/{po_id}/send."
            )

        # Map schema-validated items to PO items. Schema already rejected
        # duplicate `item_id`s, so we can rely on this being one-per-item.
        items_by_id = {i.id: i for i in po.items}
        for ri in payload.received_items:
            if ri.item_id not in items_by_id:
                raise ValidationError(
                    f"Item {ri.item_id} does not belong to this PO"
                )

        # Build the effective receive map for this call.
        is_partial_call = bool(payload.received_items)
        receive_map: dict[UUID, float] = {}
        for item in po.items:
            if is_partial_call:
                qty = next(
                    (
                        ri.quantity_received
                        for ri in payload.received_items
                        if ri.item_id == item.id
                    ),
                    0.0,
                )
            else:
                qty = float(item.quantity) - float(item.quantity_received)
            receive_map[item.id] = qty

        # Validate against remaining (float tolerance for decimal→float).
        for item_id, qty in receive_map.items():
            item = items_by_id[item_id]
            remaining = float(item.quantity) - float(item.quantity_received)
            if qty > remaining + 1e-6:
                raise ValidationError(
                    f"Received quantity ({qty}) exceeds remaining "
                    f"({remaining}) for item {item_id}"
                )
            if qty < 0:
                raise ValidationError(f"Negative quantity for item {item_id}")

        total_now = sum(receive_map.values())
        if total_now <= 0:
            raise ValidationError(
                "Nothing to receive — supply positive quantities or omit "
                "received_items to receive all remaining."
            )

        now = datetime.now(UTC)
        for item in po.items:
            qty = receive_map[item.id]
            if qty <= 0:
                continue

            material = await self.material_repo.get(item.material_id)
            if not material:
                raise NotFoundError(
                    f"Material for PO item {item.id} disappeared"
                )

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
                occurred_at=now,
                created_by_id=actor.id,
            )
            await self.tx_repo.add(tx)

            material.current_purchase_price = float(item.unit_price)
            item.quantity_received = float(item.quantity_received) + qty

        # Transition to RECEIVED only when every line is fully received.
        # Partial receipts leave the PO in SENT so a follow-up `receive`
        # can complete the delivery.
        all_received = all(
            float(item.quantity_received) >= float(item.quantity) - 1e-6
            for item in po.items
        )
        if all_received:
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
                "received_now": {
                    str(k): v for k, v in receive_map.items() if v > 0
                },
                "is_partial": not all_received,
                "received_at": now.isoformat() if all_received else None,
            },
        )
        return po

    async def close(self, po_id: UUID, *, actor: User) -> PurchaseOrder:
        po = await self.repo.get_for_update(po_id)
        if not po:
            raise NotFoundError("Purchase order not found")
        await self.db.refresh(po, ["items"])

        if po.status != PurchaseOrderStatus.RECEIVED.value:
            raise ConflictError("Only RECEIVED purchase orders can be closed")
        po.status = PurchaseOrderStatus.CLOSED.value
        await self.db.flush()
        await self.audit.log(
            action=AuditAction.STATUS_CHANGE,
            table_name="purchase_orders",
            record_id=po.id,
            user_id=actor.id,
            old_data={"status": PurchaseOrderStatus.RECEIVED.value},
            new_data={"status": PurchaseOrderStatus.CLOSED.value},
        )
        return po

    async def cancel(self, po_id: UUID, *, actor: User) -> PurchaseOrder:
        po = await self.repo.get_for_update(po_id)
        if not po:
            raise NotFoundError("Purchase order not found")
        await self.db.refresh(po, ["items"])

        if po.status in TERMINAL_PO_STATUSES:
            raise ConflictError(f"Cannot cancel a {po.status} PO")
        if po.status == PurchaseOrderStatus.RECEIVED.value:
            raise ConflictError(
                "Received purchase orders cannot be cancelled; use returns"
            )
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