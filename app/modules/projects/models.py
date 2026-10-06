"""Costing models: employees, projects, project items."""

from __future__ import annotations

from datetime import date, datetime
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

    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    position: Mapped[str | None] = mapped_column(String(100))
    hourly_rate: Mapped[float] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, server_default="0",
    )
    monthly_salary: Mapped[float | None] = mapped_column(Numeric(14, 2))
    joined_at: Mapped[date | None] = mapped_column(Date)
    phone: Mapped[str | None] = mapped_column(String(32))
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

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

    # ── Identity ────────────────────────────────────────
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)

    # ── Relationships ───────────────────────────────────
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

    # ── Workflow ────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(24),
        default=ProjectStatus.DRAFT.value,
        nullable=False,
        index=True,
    )
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ── Pricing ────────────────────────────────────────
    # Quoted price is what we offer the customer; approved_price is
    # what they actually agreed to. Gross profit = approved - actual_hpp.
    quoted_price: Mapped[float | None] = mapped_column(Numeric(14, 2))
    approved_price: Mapped[float | None] = mapped_column(Numeric(14, 2))

    # ── Denormalized costing totals (kept in sync by the service) ──
    estimated_hpp: Mapped[float] = mapped_column(
        Numeric(14, 2), default=0, nullable=False, server_default="0",
    )
    actual_hpp: Mapped[float] = mapped_column(
        Numeric(14, 2), default=0, nullable=False, server_default="0",
    )
    # Per-category breakdown (both estimated and actual)
    estimated_materials: Mapped[float] = mapped_column(Numeric(14, 2), default=0, server_default="0", nullable=False)
    estimated_parts: Mapped[float] = mapped_column(Numeric(14, 2), default=0, server_default="0", nullable=False)
    estimated_labor: Mapped[float] = mapped_column(Numeric(14, 2), default=0, server_default="0", nullable=False)
    estimated_outsource: Mapped[float] = mapped_column(Numeric(14, 2), default=0, server_default="0", nullable=False)
    estimated_overhead: Mapped[float] = mapped_column(Numeric(14, 2), default=0, server_default="0", nullable=False)
    estimated_misc: Mapped[float] = mapped_column(Numeric(14, 2), default=0, server_default="0", nullable=False)

    actual_materials: Mapped[float] = mapped_column(Numeric(14, 2), default=0, server_default="0", nullable=False)
    actual_parts: Mapped[float] = mapped_column(Numeric(14, 2), default=0, server_default="0", nullable=False)
    actual_labor: Mapped[float] = mapped_column(Numeric(14, 2), default=0, server_default="0", nullable=False)
    actual_outsource: Mapped[float] = mapped_column(Numeric(14, 2), default=0, server_default="0", nullable=False)
    actual_overhead: Mapped[float] = mapped_column(Numeric(14, 2), default=0, server_default="0", nullable=False)
    actual_misc: Mapped[float] = mapped_column(Numeric(14, 2), default=0, server_default="0", nullable=False)

    # ── Timeline ────────────────────────────────────────
    start_date: Mapped[date | None] = mapped_column(Date)
    target_end_date: Mapped[date | None] = mapped_column(Date)
    actual_end_date: Mapped[date | None] = mapped_column(Date)

    # ── Notes ───────────────────────────────────────────
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
    )

    # ── Derived properties ─────────────────────────────
    @property
    def hpp_variance(self) -> float:
        """Positive = we spent less than estimated. Negative = overrun."""
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

    def __repr__(self) -> str:
        return f"<Project {self.code} {self.status}>"


# ════════════════════════════════════════════════════════════════
# PROJECT ITEMS
#
# Each row is a costing line: either a plan (estimated_*) or a
# consumption (actual_*) — often both as work progresses.
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

    # ── Classification ──────────────────────────────────
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)

    # Optional links (required for some categories — enforced by service)
    material_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("materials.id", ondelete="RESTRICT"),
    )
    employee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="RESTRICT"),
    )

    # ── Units ───────────────────────────────────────────
    unit: Mapped[str | None] = mapped_column(String(16))

    # ── Estimated (planning) ────────────────────────────
    estimated_quantity: Mapped[float | None] = mapped_column(Numeric(14, 4))
    estimated_unit_cost: Mapped[float | None] = mapped_column(Numeric(14, 4))
    estimated_cost: Mapped[float] = mapped_column(
        Numeric(14, 2), default=0, nullable=False, server_default="0",
    )

    # ── Actual (execution) ──────────────────────────────
    actual_quantity: Mapped[float | None] = mapped_column(Numeric(14, 4))
    actual_unit_cost: Mapped[float | None] = mapped_column(Numeric(14, 4))
    actual_cost: Mapped[float] = mapped_column(
        Numeric(14, 2), default=0, nullable=False, server_default="0",
    )

    # ── Progress ────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(16), default="PLANNED", nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text)

    project: Mapped[Project] = relationship(back_populates="items")

    def __repr__(self) -> str:
        return f"<ProjectItem {self.category} {self.description[:30]}>"