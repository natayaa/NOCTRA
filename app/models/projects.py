# models/projects.py
from __future__ import annotations

from decimal import Decimal
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    String,
    Numeric,
    ForeignKey,
    Integer,
    Text,
    Boolean,
    Enum,
    DateTime, 
    func,
    Date,
    JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, UUIDMixin, TimestampMixin
from schemas.constants import ProjectStatus, ProjectPriority


class Project(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_projects"

    # ============ Core Information ============
    inquiry_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tb_customer_inquiry.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    customer_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    vehicle_brand: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    vehicle_model: Mapped[str] = mapped_column(String(100), nullable=False)
    vehicle_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vehicle_license_plate: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)

    # ============ Status & Progress ============
    status: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default=ProjectStatus.ACTIVE,   
        index=True,
    )
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ProjectPriority.MEDIUM,
        index=True
    )
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ============ Financial ============
    estimated_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    actual_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    estimated_revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    actual_revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    
    deposit_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    deposit_paid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deposit_paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ============ Timeline ============
    stage_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tb_project_stages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    project_start_date: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=True, 
        server_default=func.now()
    )
    project_target_delivery: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    actual_delivery_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ============ Notes & Metadata ============
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # ============ Relationships ============
    inquiry = relationship("CustomerInquiry", back_populates="project")
    
    # Ganti nama back_populates menjadi 'expense_items' untuk menghindari konflik
    expense_items = relationship(
        "Expense",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    
    # Untuk ProjectExpense dari models/projects.py
    project_expenses = relationship(
        "ProjectExpense",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    
    stage = relationship("ProjectStage", back_populates="projects")
    tasks = relationship(
        "ProjectTask",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    workshop_job = relationship(
        "ProjectWorkshopTask",
        back_populates="project",
        uselist=False,
    )
    labor_items = relationship(
        "ProjectLabor",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    material_usages = relationship(
        "InventoryMaterialUsage",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    activities = relationship(
        "ProjectActivity",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectActivity.created_at.desc()",
    )

    def __repr__(self):
        return f"<Project {self.id} - {self.name} - {self.customer_name}>"


class ProjectTask(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_project_tasks"

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), 
        nullable=False, 
        default="todo", 
        index=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Additional fields
    assigned_to: Mapped[str | None] = mapped_column(String(100), nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")

    project = relationship("Project", back_populates="tasks")

    def __repr__(self):
        return f"<ProjectTask {self.id} - {self.title}>"


# models/projects.py (bagian ProjectExpense)

class ProjectExpense(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_project_expenses"

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    
    # Additional fields
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    expense_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    receipt_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_billable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Gunakan back_populates yang berbeda dari Expense
    project = relationship("Project", back_populates="project_expenses")

    def __repr__(self):
        return f"<ProjectExpense {self.id} - {self.name} - {self.amount}>"


class ProjectStage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_project_stages"

    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # Relationships
    projects = relationship("Project", back_populates="stage")

    def __repr__(self):
        return f"<ProjectStage {self.id} - {self.name}>"


class ProjectActivity(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_project_activities"

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    activity: Mapped[str] = mapped_column(String(255), nullable=False)
    activity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    performed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    meta_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    project = relationship("Project", back_populates="activities")

    def __repr__(self):
        return f"<ProjectActivity {self.id} - {self.activity}>"


class ProjectLabor(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_project_labor"

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    labor_type: Mapped[str] = mapped_column(String(100), nullable=False)
    hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    rate_per_hour: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    
    # Additional fields
    technician_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    date_performed: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="labor_items")

    def __repr__(self):
        return f"<ProjectLabor {self.id} - {self.labor_type} - {self.hours}h"