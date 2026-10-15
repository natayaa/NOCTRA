"""Inventory models: suppliers, materials, transactions, purchase orders."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, UUIDMixin
from app.modules.inventory.constants import PurchaseOrderStatus


# ════════════════════════════════════════════════════════════════
# SUPPLIERS
# ════════════════════════════════════════════════════════════════

class Supplier(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "suppliers"
    __table_args__ = (
        Index("ix_suppliers_active_name", "is_active", "name"),
    )

    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    contact_person: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(32))
    address: Mapped[str | None] = mapped_column(Text)
    tax_id: Mapped[str | None] = mapped_column(String(64))
    payment_terms: Mapped[str | None] = mapped_column(String(64))
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Supplier {self.code} {self.name}>"


# ════════════════════════════════════════════════════════════════
# MATERIALS
# ════════════════════════════════════════════════════════════════

class Material(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "materials"
    __table_args__ = (
        Index("ix_materials_category_name", "category", "name"),
        Index("ix_materials_active_category", "is_active", "category"),
        Index("ix_materials_sku", "sku"),
    )

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    sku: Mapped[str | None] = mapped_column(String(64))

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    # ── Unit model ──────────────────────────────────────
    purchase_unit: Mapped[str] = mapped_column(String(16), nullable=False)
    stock_unit: Mapped[str] = mapped_column(String(16), nullable=False)
    stock_units_per_purchase: Mapped[float] = mapped_column(
        Numeric(14, 4), nullable=False,
    )

    # ── Pricing ────────────────────────────────────────
    current_purchase_price: Mapped[float] = mapped_column(
        Numeric(14, 2), default=0, nullable=False, server_default="0",
    )

    # ── Stock thresholds ───────────────────────────────
    reorder_point: Mapped[float] = mapped_column(
        Numeric(14, 4), default=0, nullable=False, server_default="0",
    )
    min_stock: Mapped[float] = mapped_column(
        Numeric(14, 4), default=0, nullable=False, server_default="0",
    )

    # ── Default supplier ───────────────────────────────
    preferred_supplier_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="SET NULL"),
    )

    # ── Metadata ───────────────────────────────────────
    notes: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    supplier: Mapped[Supplier | None] = relationship(
        foreign_keys=[preferred_supplier_id],
    )

    @property
    def cost_per_stock_unit(self) -> float:
        """Derived: IDR per ml / gr / piece. Used by the costing engine."""
        if not self.stock_units_per_purchase:
            return 0.0
        return float(self.current_purchase_price) / float(self.stock_units_per_purchase)

    def __repr__(self) -> str:
        return f"<Material {self.code} {self.name}>"


# ════════════════════════════════════════════════════════════════
# INVENTORY TRANSACTIONS (append-only ledger)
# ════════════════════════════════════════════════════════════════

class InventoryTransaction(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "inventory_transactions"
    __table_args__ = (
        Index("ix_inv_tx_material_created", "material_id", "created_at"),
        Index("ix_inv_tx_type_created", "transaction_type", "created_at"),
        Index("ix_inv_tx_reference", "reference_type", "reference_id"),
    )

    material_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("materials.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    transaction_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    quantity: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)

    unit_cost: Mapped[float | None] = mapped_column(Numeric(14, 4))

    reference_type: Mapped[str | None] = mapped_column(String(32))
    reference_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    reference_note: Mapped[str | None] = mapped_column(String(255))

    notes: Mapped[str | None] = mapped_column(Text)

    created_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    material: Mapped[Material] = relationship()

    def __repr__(self) -> str:
        sign = "+" if self.transaction_type in ("OPENING", "PURCHASE", "ADJUSTMENT_IN", "TRANSFER_IN") else "-"
        return f"<InventoryTx {self.transaction_type} {sign}{self.quantity} of {self.material_id}>"


# ════════════════════════════════════════════════════════════════
# PURCHASE ORDERS
# ════════════════════════════════════════════════════════════════

class PurchaseOrder(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "purchase_orders"
    __table_args__ = (
        Index("ix_purchase_orders_status_created", "status", "created_at"),
        Index("ix_purchase_orders_supplier", "supplier_id"),
    )

    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)

    supplier_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(16),
        default=PurchaseOrderStatus.DRAFT.value,
        nullable=False,
        index=True,
    )

    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_date: Mapped[date | None] = mapped_column(Date)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    total_amount: Mapped[float] = mapped_column(
        Numeric(14, 2), default=0, nullable=False, server_default="0",
    )

    notes: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    supplier: Mapped[Supplier] = relationship()
    items: Mapped[list["PurchaseOrderItem"]] = relationship(
        back_populates="purchase_order",
        cascade="all, delete-orphan",
        order_by="PurchaseOrderItem.created_at",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<PurchaseOrder {self.code} {self.status}>"


class PurchaseOrderItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "purchase_order_items"
    __table_args__ = (
        Index("ix_po_items_po", "purchase_order_id"),
        Index("ix_po_items_material", "material_id"),
    )

    purchase_order_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("purchase_orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    material_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("materials.id", ondelete="RESTRICT"),
        nullable=False,
    )

    quantity: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)

    quantity_received: Mapped[float] = mapped_column(
        Numeric(14, 4), default=0, nullable=False, server_default="0",
    )

    notes: Mapped[str | None] = mapped_column(Text)

    purchase_order: Mapped[PurchaseOrder] = relationship(back_populates="items")
    material: Mapped[Material] = relationship()

    @property
    def line_total(self) -> float:
        return float(self.quantity) * float(self.unit_price)