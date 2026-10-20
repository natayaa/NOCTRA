"""Costing models: employees, projects, project items."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, UUIDMixin
from app.modules.projects.constants import ProjectStatus


# ════════════════════════════════════════════════════════════════
# EMPLOYEES
# ════════════════════════════════════════════════════════════════

class Employee(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "employees"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    position: Mapped[str | None] = mapped_column(String(100))
    hourly_rate: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, server_default="0",
    )
    monthly_salary: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    joined_at: Mapped[date | None] = mapped_column(Date)
    phone: Mapped[str | None] = mapped_column(String(32))
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Employee {self.code} {self.name}>"


# ════════════════════════════════════════════════════════════════
# PROJECTS
# ════════════════════════════════════════════════════════════════

class Project(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "projects"
    __table_args__ = (
        Index("ix_projects_status_created", "status", "created_at"),
        Index("ix_projects_customer_created", "customer_id", "created_at"),
        Index("ix_projects_vehicle", "vehicle_id"),
    )

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)

    inquiry_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("inquiries.id", ondelete="SET NULL"),
        index=True,
    )
    customer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    vehicle_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="SET NULL"),
    )
    assigned_lead_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    status: Mapped[str] = mapped_column(
        String(24),
        default=ProjectStatus.DRAFT.value,
        server_default=ProjectStatus.DRAFT.value,
        nullable=False,
        index=True,
    )
    priority: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False,
    )

    quoted_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    approved_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))

    estimated_hpp: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=0, nullable=False, server_default="0",
    )
    actual_hpp: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=0, nullable=False, server_default="0",
    )
    estimated_materials: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=0, server_default="0", nullable=False,
    )
    estimated_parts: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=0, server_default="0", nullable=False,
    )
    estimated_labor: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=0, server_default="0", nullable=False,
    )
    estimated_outsource: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=0, server_default="0", nullable=False,
    )
    estimated_overhead: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=0, server_default="0", nullable=False,
    )
    estimated_misc: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=0, server_default="0", nullable=False,
    )

    actual_materials: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=0, server_default="0", nullable=False,
    )
    actual_parts: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=0, server_default="0", nullable=False,
    )
    actual_labor: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=0, server_default="0", nullable=False,
    )
    actual_outsource: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=0, server_default="0", nullable=False,
    )
    actual_overhead: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=0, server_default="0", nullable=False,
    )
    actual_misc: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=0, server_default="0", nullable=False,
    )

    start_date: Mapped[date | None] = mapped_column(Date)
    target_end_date: Mapped[date | None] = mapped_column(Date)
    actual_end_date: Mapped[date | None] = mapped_column(Date)

    internal_notes: Mapped[str | None] = mapped_column(Text)
    closing_note: Mapped[str | None] = mapped_column(Text)

    created_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    items: Mapped[list["ProjectItem"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectItem.created_at",
        lazy="selectin",
    )

    # ── Derived properties ─────────────────────────────
    @property
    def hpp_variance(self) -> float:
        """Positive = spent less than estimated. Negative = overrun."""
        return float(self.estimated_hpp) - float(self.actual_hpp)

    @property
    def actual_gross_profit(self) -> float:
        if self.approved_price is None:
            return 0.0
        return float(self.approved_price) - float(self.actual_hpp)

    @property
    def actual_gross_margin_pct(self) -> float:
        if not self.approved_price:
            return 0.0
        return (self.actual_gross_profit / float(self.approved_price)) * 100

    @property
    def estimated_gross_profit(self) -> float:
        if self.approved_price is None:
            return 0.0
        return float(self.approved_price) - float(self.estimated_hpp)

    # ── Float-safe views (for templates & arithmetic) ──
    # These were previously (incorrectly) on ProjectItem — moved here
    # where the underlying columns actually live.

    @property
    def est_hpp(self) -> float:
        return float(self.estimated_hpp or 0)

    @property
    def act_hpp(self) -> float:
        return float(self.actual_hpp or 0)

    @property
    def quoted_price_f(self) -> float:
        return float(self.quoted_price or 0)

    @property
    def approved_price_f(self) -> float:
        return float(self.approved_price or 0)

    @property
    def estimated_materials_f(self) -> float:
        return float(self.estimated_materials or 0)

    @property
    def actual_materials_f(self) -> float:
        return float(self.actual_materials or 0)

    @property
    def estimated_labor_f(self) -> float:
        return float(self.estimated_labor or 0)

    @property
    def actual_labor_f(self) -> float:
        return float(self.actual_labor or 0)

    @property
    def estimated_overhead_f(self) -> float:
        return float(self.estimated_overhead or 0)

    @property
    def actual_overhead_f(self) -> float:
        return float(self.actual_overhead or 0)

    def __repr__(self) -> str:
        return f"<Project {self.code} {self.status}>"


# ════════════════════════════════════════════════════════════════
# PROJECT ITEMS
# ════════════════════════════════════════════════════════════════

class ProjectItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "project_items"
    __table_args__ = (
        Index("ix_project_items_project", "project_id"),
        Index("ix_project_items_category", "category"),
        Index("ix_project_items_material", "material_id"),
        Index("ix_project_items_employee", "employee_id"),
    )

    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    category: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)

    material_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("materials.id", ondelete="RESTRICT"),
    )
    employee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="RESTRICT"),
    )

    unit: Mapped[str | None] = mapped_column(String(16))

    estimated_quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    estimated_unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    estimated_cost: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=0, nullable=False, server_default="0",
    )

    actual_quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    actual_unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    actual_cost: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=0, nullable=False, server_default="0",
    )

    status: Mapped[str] = mapped_column(
        String(16), default="PLANNED", server_default="PLANNED", nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text)

    # Business date for finance COGS periodization. Backfilled from
    # created_at for legacy rows; not updated on item edits.
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    project: Mapped[Project] = relationship(back_populates="items")

    def __repr__(self) -> str:
        return f"<ProjectItem {self.category} {self.description[:30]}>"