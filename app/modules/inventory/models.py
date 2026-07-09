# modules/inventory/models.py
from __future__ import annotations

from decimal import Decimal
from datetime import datetime, date
from uuid import UUID

from sqlalchemy import (
    String, Numeric, ForeignKey, Text, Integer, Boolean,
    DateTime, func, CheckConstraint, Date, JSON, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.base import Base, UUIDMixin, TimestampMixin
from core.constants import InventoryStatus, StockMovementType


class InventoryItem(Base, UUIDMixin, TimestampMixin):
    """Model untuk item inventory."""
    __tablename__ = "tb_inventory_items"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True)
    sub_category: Mapped[str | None] = mapped_column(
        String(100), nullable=True)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    base_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    conversion_factor: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), nullable=False, default=1)

    # Pricing
    cost_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0)
    selling_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True)
    last_purchase_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0)

    # Stock
    current_stock: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), nullable=False, default=0)
    min_stock_threshold: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), nullable=False, default=0)
    max_stock_threshold: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), nullable=False, default=999999)
    reserved_stock: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), nullable=False, default=0)
    available_stock: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), nullable=False, default=0)

    # Metadata
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=InventoryStatus.ACTIVE, index=True)
    sku: Mapped[str | None] = mapped_column(
        String(50), nullable=True, unique=True, index=True)
    barcode: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    supplier_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tb_suppliers.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    weight: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 3), nullable=True)
    dimensions: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    supplier = relationship("Supplier", back_populates="inventory_items")
    material_usages = relationship(
        "InventoryMaterialUsage", back_populates="item", cascade="all, delete-orphan"
    )
    stock_movements = relationship(
        "InventoryStockMovement", back_populates="item", cascade="all, delete-orphan"
    )
    purchase_order_items = relationship(
        "PurchaseOrderItem", back_populates="item", cascade="all, delete-orphan"
    )
    alerts = relationship(
        "StockAlert", back_populates="item", cascade="all, delete-orphan", lazy="selectin"
    )
    opnames = relationship(
        "StockOpname", back_populates="item", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        CheckConstraint("current_stock >= 0",
                        name="ck_inventory_current_stock_non_negative"),
        CheckConstraint("min_stock_threshold >= 0",
                        name="ck_inventory_min_stock_non_negative"),
        CheckConstraint("max_stock_threshold > 0",
                        name="ck_inventory_max_stock_positive"),
        CheckConstraint("reserved_stock >= 0",
                        name="ck_inventory_reserved_stock_non_negative"),
        CheckConstraint("available_stock >= 0",
                        name="ck_inventory_available_stock_non_negative"),
        Index("idx_inventory_items_status", "status"),
        Index("idx_inventory_items_category_status", "category", "status"),
        Index("idx_inventory_items_name_search", "name"),
    )

    def __repr__(self):
        return f"<InventoryItem {self.id} - {self.name} ({self.current_stock} {self.unit})>"

    @property
    def is_low_stock(self) -> bool:
        return self.current_stock <= self.min_stock_threshold

    @property
    def is_out_of_stock(self) -> bool:
        return self.current_stock <= 0

    @property
    def stock_value(self) -> Decimal:
        return self.current_stock * self.cost_price


class InventoryMaterialUsage(Base, UUIDMixin, TimestampMixin):
    """Model untuk penggunaan material."""
    __tablename__ = "tb_inventory_job_material_usage"

    job_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tb_inventory_workshop_jobs.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tb_projects.id", ondelete="CASCADE"),
        nullable=True, index=True
    )
    item_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_inventory_items.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0)
    total_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_waste: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False)
    waste_percentage: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True)
    used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    confirmed_by: Mapped[str | None] = mapped_column(
        String(100), nullable=True)

    # Relationships
    job = relationship("ProjectWorkshopTask", back_populates="material_usages")
    project = relationship("Project", back_populates="material_usages",
                           foreign_keys="[InventoryMaterialUsage.project_id]")
    item = relationship("InventoryItem", back_populates="material_usages")

    __table_args__ = (
        CheckConstraint(
            "quantity > 0", name="ck_material_usage_quantity_positive"),
        CheckConstraint("unit_cost >= 0",
                        name="ck_material_usage_unit_cost_non_negative"),
        CheckConstraint("waste_percentage IS NULL OR waste_percentage >= 0",
                        name="ck_material_usage_waste_percentage_range"),
        Index("idx_material_usage_project", "project_id"),
        Index("idx_material_usage_job", "job_id"),
        Index("idx_material_usage_item", "item_id"),
    )

    def __repr__(self):
        return f"<InventoryMaterialUsage {self.id} - {self.quantity} x {self.item.name}>"


class InventoryStockMovement(Base, UUIDMixin, TimestampMixin):
    """Model untuk pergerakan stock."""
    __tablename__ = "tb_inventory_stock_movements"

    item_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_inventory_items.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    previous_stock: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), nullable=False)
    new_stock: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    reference_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_id: Mapped[UUID | None] = mapped_column(
        nullable=True, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    performed_by: Mapped[str | None] = mapped_column(
        String(100), nullable=True)

    # Relationships
    item = relationship("InventoryItem", back_populates="stock_movements")

    __table_args__ = (
        CheckConstraint("quantity != 0",
                        name="ck_stock_movement_quantity_not_zero"),
        Index("idx_stock_movements_reference",
              "reference_type", "reference_id"),
        Index("idx_stock_movements_created_at", "created_at"),
        Index("idx_stock_movements_item_type", "item_id", "type"),
    )

    def __repr__(self):
        return f"<InventoryStockMovement {self.id} - {self.type} - {self.quantity}>"


class ProjectWorkshopTask(Base, UUIDMixin, TimestampMixin):
    """Model untuk workshop task project."""
    __tablename__ = "tb_inventory_workshop_jobs"

    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tb_projects.id", ondelete="CASCADE"),
        nullable=True, index=True
    )
    unit_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending", index=True)
    estimated_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0)
    actual_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0)
    start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    technician_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_hours: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True)
    actual_hours: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    # Relationships
    project = relationship("Project", back_populates="workshop_job",
                           foreign_keys="[ProjectWorkshopTask.project_id]")
    material_usages = relationship(
        "InventoryMaterialUsage",
        back_populates="job",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_workshop_job_project", "project_id"),
        Index("idx_workshop_job_status", "status"),
    )

    def __repr__(self):
        return f"<ProjectWorkshopTask {self.id} - {self.unit_name or 'Unnamed'}>"


class Supplier(Base, UUIDMixin, TimestampMixin):
    """Model untuk supplier."""
    __tablename__ = "tb_suppliers"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    contact_person: Mapped[str | None] = mapped_column(
        String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payment_terms: Mapped[str | None] = mapped_column(
        String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    inventory_items = relationship("InventoryItem", back_populates="supplier")
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")

    __table_args__ = (
        CheckConstraint("rating IS NULL OR rating BETWEEN 1 AND 5",
                        name="ck_supplier_rating_range"),
        Index("idx_supplier_name", "name"),
        Index("idx_supplier_active", "is_active"),
    )

    def __repr__(self):
        return f"<Supplier {self.id} - {self.name}>"


class PurchaseOrder(Base, UUIDMixin, TimestampMixin):
    """Model untuk purchase order."""
    __tablename__ = "tb_purchase_orders"

    supplier_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_suppliers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    po_number: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True)
    order_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now())
    expected_delivery: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    actual_delivery: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="draft", index=True)
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    # Relationships
    supplier = relationship("Supplier", back_populates="purchase_orders")
    items = relationship(
        "PurchaseOrderItem",
        back_populates="purchase_order",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_po_supplier", "supplier_id"),
        Index("idx_po_status", "status"),
        Index("idx_po_number", "po_number"),
    )

    def __repr__(self):
        return f"<PurchaseOrder {self.id} - {self.po_number}>"


class PurchaseOrderItem(Base, UUIDMixin, TimestampMixin):
    """Model untuk item purchase order."""
    __tablename__ = "tb_purchase_order_items"

    purchase_order_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_purchase_orders.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    item_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_inventory_items.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False)
    received_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    purchase_order = relationship("PurchaseOrder", back_populates="items")
    item = relationship("InventoryItem", back_populates="purchase_order_items")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_po_item_quantity_positive"),
        CheckConstraint("unit_price >= 0",
                        name="ck_po_item_unit_price_non_negative"),
        CheckConstraint("received_quantity >= 0",
                        name="ck_po_item_received_quantity_non_negative"),
        CheckConstraint("received_quantity <= quantity",
                        name="ck_po_item_received_not_exceed_quantity"),
        Index("idx_po_item_po", "purchase_order_id"),
        Index("idx_po_item_item", "item_id"),
    )

    def __repr__(self):
        return f"<PurchaseOrderItem {self.id} - {self.item.name}>"

    @property
    def is_fully_received(self) -> bool:
        return self.received_quantity >= self.quantity

    @property
    def remaining_quantity(self) -> Decimal:
        return self.quantity - self.received_quantity


class StockAlert(Base, UUIDMixin, TimestampMixin):
    """Stock alert."""
    __tablename__ = "tb_stock_alerts"

    item_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_inventory_items.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    # low_stock, out_of_stock, expiring, overstock
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    current_stock: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), nullable=False)
    threshold: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    status: Mapped[str] = mapped_column(
        # active, resolved, ignored
        String(50), nullable=False, default="active")
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default="warning")  # warning, critical
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    item = relationship("InventoryItem", back_populates="alerts")

    __table_args__ = (
        CheckConstraint(
            "alert_type IN ('low_stock', 'out_of_stock', 'expiring', 'overstock')", name="ck_alert_type"),
        CheckConstraint("severity IN ('warning', 'critical')",
                        name="ck_alert_severity"),
        CheckConstraint(
            "status IN ('active', 'resolved', 'ignored')", name="ck_alert_status"),
        Index("idx_stock_alerts_item_status", "item_id", "status"),
        Index("idx_stock_alerts_created_at", "created_at"),
        Index("idx_stock_alerts_severity", "severity"),
    )

    def __repr__(self):
        return f"<StockAlert {self.id} - {self.item_id} - {self.alert_type}>"


class StockOpname(Base, UUIDMixin, TimestampMixin):
    """Stock opname."""
    __tablename__ = "tb_stock_opnames"

    item_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_inventory_items.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    system_stock: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), nullable=False)
    physical_stock: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), nullable=False)
    difference: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    adjustment_reason: Mapped[str] = mapped_column(String(255), nullable=False)
    performed_by: Mapped[str] = mapped_column(String(100), nullable=False)
    performed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now())
    approved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    item = relationship("InventoryItem", back_populates="opnames")

    __table_args__ = (
        Index("idx_stock_opnames_item", "item_id"),
        Index("idx_stock_opnames_performed_at", "performed_at"),
        Index("idx_stock_opnames_approved", "approved_by"),
    )

    def __repr__(self):
        return f"<StockOpname {self.id} - {self.item_id}>"


class InventoryValuation(Base, UUIDMixin, TimestampMixin):
    """Inventory valuation."""
    __tablename__ = "tb_inventory_valuations"

    item_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_inventory_items.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    valuation_date: Mapped[date] = mapped_column(Date, nullable=False)
    method: Mapped[str] = mapped_column(
        String(20), nullable=False)  # fifo, lifo, average
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_value: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False)

    # Relationships
    item = relationship("InventoryItem", back_populates="valuations")

    __table_args__ = (
        Index("idx_valuation_item_date", "item_id", "valuation_date"),
        Index("idx_valuation_method", "method"),
    )

    def __repr__(self):
        return f"<InventoryValuation {self.id} - {self.item_id} - {self.valuation_date}>"


# Tambahkan relationship ke InventoryItem
InventoryItem.valuations = relationship(
    "InventoryValuation", back_populates="item", cascade="all, delete-orphan", lazy="selectin"
)
