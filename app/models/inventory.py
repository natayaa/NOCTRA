# models/inventory/inventory_items.py
from __future__ import annotations

from decimal import Decimal
from uuid import UUID
from datetime import date

from sqlalchemy import String, Numeric, ForeignKey, Text, Enum, CheckConstraint, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, UUIDMixin, TimestampMixin
from schemas.constants import InventoryStatus, StockMovementType


class InventoryItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_inventory_items"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    sub_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    conversion_factor: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), 
        nullable=False, 
        default=Decimal('1.000000')
    )
    # Pricing
    cost_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    selling_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    last_purchase_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    
    # Stock
    current_stock: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, default=0)
    min_stock_threshold: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, default=0)
    max_stock_threshold: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, default=999999)
    
    # Metadata
    status: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        default=InventoryStatus.ACTIVE,
        index=True
    )
    sku: Mapped[str | None] = mapped_column(String(50), nullable=True, unique=True, index=True)
    barcode: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    supplier_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tb_suppliers.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    weight: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    dimensions: Mapped[str | None] = mapped_column(String(100), nullable=True)  # LxWxH
    
    # Relationships
    supplier = relationship("Supplier", back_populates="inventory_items")
    material_usages = relationship("InventoryMaterialUsage", back_populates="item")
    stock_movements = relationship("InventoryStockMovement", back_populates="item")
    purchase_order_items = relationship("PurchaseOrderItem", back_populates="item")

    __table_args__ = (
        CheckConstraint("current_stock >= 0", name="ck_inventory_current_stock_non_negative"),
        CheckConstraint("min_stock_threshold >= 0", name="ck_inventory_min_stock_non_negative"),
        CheckConstraint("max_stock_threshold > 0", name="ck_inventory_max_stock_positive"),
    )

    def __repr__(self):
        return f"<InventoryItem {self.id} - {self.name} ({self.current_stock} {self.unit})>"


class InventoryMaterialUsage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_inventory_job_material_usage"

    job_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tb_inventory_workshop_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tb_projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    item_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_inventory_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_waste: Mapped[bool] = mapped_column(nullable=False, default=False)
    waste_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    # Relationships
    job = relationship("ProjectWorkshopTask", back_populates="material_usages")
    project = relationship("Project", back_populates="material_usages")
    item = relationship("InventoryItem", back_populates="material_usages")

    def __repr__(self):
        return f"<InventoryMaterialUsage {self.id} - {self.quantity} x {self.item.name}>"


class InventoryStockMovement(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_inventory_stock_movements"

    item_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_inventory_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(
        String(30), 
        nullable=False,
        index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    previous_stock: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    new_stock: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    reference_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    performed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    item = relationship("InventoryItem", back_populates="stock_movements")

    def __repr__(self):
        return f"<InventoryStockMovement {self.id} - {self.type} - {self.quantity}>"


class ProjectWorkshopTask(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_inventory_workshop_jobs"

    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tb_projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    unit_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), 
        nullable=False, 
        default="pending",
        index=True
    )
    estimated_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    actual_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    
    # Additional fields
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    technician_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="workshop_job")
    material_usages = relationship(
        "InventoryMaterialUsage",
        back_populates="job",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<ProjectWorkshopTask {self.id} - {self.unit_name or 'Unnamed'}>"


# Tambahan model untuk Supplier
class Supplier(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_suppliers"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    contact_person: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payment_terms: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    inventory_items = relationship("InventoryItem", back_populates="supplier")
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")


# Tambahan model untuk Purchase Order
class PurchaseOrder(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_purchase_orders"

    supplier_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_suppliers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    po_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    order_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    expected_delivery: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relationships
    supplier = relationship("Supplier", back_populates="purchase_orders")
    items = relationship("PurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan")


class PurchaseOrderItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_purchase_order_items"

    purchase_order_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_purchase_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    item_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_inventory_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    received_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    purchase_order = relationship("PurchaseOrder", back_populates="items")
    item = relationship("InventoryItem", back_populates="purchase_order_items")