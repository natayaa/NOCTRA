# models/inventory/inventory_items.py
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import String, Numeric, ForeignKey, Text, Enum, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, UUIDMixin, TimestampMixin


class InventoryItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_inventory_items"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    cost_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    selling_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    current_stock: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, default=0)
    min_stock_threshold: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    material_usages = relationship("InventoryMaterialUsage", back_populates="item")
    stock_movements = relationship("InventoryStockMovement", back_populates="item")

    __table_args__ = (
        CheckConstraint("current_stock >= 0", name="ck_inventory_current_stock_non_negative"),
        CheckConstraint("min_stock_threshold >= 0", name="ck_inventory_min_stock_non_negative"),
    )


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
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    job = relationship("ProjectWorkshopTask", back_populates="material_usages")
    project = relationship("Project", back_populates="material_usages")
    item = relationship("InventoryItem", back_populates="material_usages")


class InventoryStockMovement(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_inventory_stock_movements"

    item_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_inventory_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    reference_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_id: Mapped[UUID | None] = mapped_column(nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    item = relationship("InventoryItem", back_populates="stock_movements")


class ProjectWorkshopTask(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_inventory_workshop_jobs"

    project_id: Mapped[UUID | None] = mapped_column(ForeignKey("tb_projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    unit_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    estimated_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    actual_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    project = relationship("Project", back_populates="workshop_job")
    material_usages = relationship(
        "InventoryMaterialUsage",
        back_populates="job",
        cascade="all, delete-orphan",
    )