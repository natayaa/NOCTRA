from __future__ import annotations

from decimal import Decimal
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Index, String, Numeric, ForeignKey,
    Integer, Text, Boolean,
    DateTime, func, Date, JSON, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.base import Base, UUIDMixin, TimestampMixin
from core.constants import ProjectStatus, ProjectPriority


class Project(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_projects"

    # ============ Foreign Keys ============
    inquiry_id: Mapped[UUID | None] = mapped_column(ForeignKey("tb_customer_inquiry.id", ondelete="SET NULL"), nullable=True, index=True)
    stage_id: Mapped[UUID | None] = mapped_column(ForeignKey("tb_project_stages.id", ondelete="SET NULL"), nullable=True, index=True)

    # ============ Core Fields ============
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    project_code: Mapped[str | None] = mapped_column(String(50), nullable=True, unique=True, index=True, comment="Kode project unik (auto-generate)")
    
    # ============ Denormalized from Inquiry (untuk performance) ============
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True, comment="Denormalized from inquiry")
    customer_phone: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True, comment="Denormalized from inquiry")
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="Denormalized from inquiry")
    customer_address: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Denormalized from inquiry")

    # Vehicle Information (denormalized from inquiry)
    vehicle_brand: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    vehicle_model: Mapped[str] = mapped_column(String(100), nullable=False)
    vehicle_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vehicle_license_plate: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="Sumber project (inquiry, direct, etc)")
    
    # ============ Status & Progress ============
    status: Mapped[str] = mapped_column(String(100), nullable=False, default=ProjectStatus.ACTIVE, index=True)
    priority: Mapped[str] = mapped_column(String(50), nullable=False, default=ProjectPriority.MEDIUM, index=True)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ============ Financial ============
    estimated_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    actual_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    # ============ Timeline ============
    project_start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    project_target_delivery: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_delivery_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ============ Notes & Metadata ============
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)  # NEW
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # NEW

    # ============ Relationships ============
    inquiry = relationship("CustomerInquiry", back_populates="project", lazy="selectin")
    stage = relationship("ProjectStage", back_populates="projects", lazy="selectin")
    tasks = relationship("ProjectTask", back_populates="project", cascade="all, delete-orphan", lazy="selectin")
    workshop_job = relationship("ProjectWorkshopTask", back_populates="project", uselist=False, lazy="selectin", foreign_keys="[ProjectWorkshopTask.project_id]")
    labor_items = relationship("ProjectLabor", back_populates="project", cascade="all, delete-orphan", lazy="selectin", foreign_keys="[ProjectLabor.project_id]")
    material_usages = relationship("InventoryMaterialUsage", back_populates="project", cascade="all, delete-orphan", lazy="selectin", foreign_keys="[InventoryMaterialUsage.project_id]")
    activities = relationship("ProjectActivity", back_populates="project", order_by="ProjectActivity.created_at.desc()", lazy="selectin", foreign_keys="[ProjectActivity.project_id]")
    expenses = relationship("ProjectExpense", back_populates="project", cascade="all, delete-orphan", lazy="selectin", foreign_keys="[ProjectExpense.project_id]")
    price_list_items = relationship("ProjectPriceListItem", back_populates="project", cascade="all, delete-orphan", lazy="selectin", foreign_keys="[ProjectPriceListItem.project_id]")
    timeline = relationship("ProjectTimeline", back_populates="project", cascade="all, delete-orphan", lazy="selectin", foreign_keys="[ProjectTimeline.project_id]")
    documents = relationship("ProjectDocument", back_populates="project", cascade="all, delete-orphan", lazy="selectin", foreign_keys="[ProjectDocument.project_id]")
    team_members = relationship("ProjectTeam", back_populates="project", cascade="all, delete-orphan", lazy="selectin", foreign_keys="[ProjectTeam.project_id]")

    # ============ Constraints ============
    __table_args__ = (
        CheckConstraint("progress >= 0 AND progress <= 100", name="ck_project_progress_range"),
        CheckConstraint("estimated_cost >= 0", name="ck_project_estimated_cost_non_negative"),
        CheckConstraint("actual_cost >= 0", name="ck_project_actual_cost_non_negative"),
        Index("idx_project_inquiry_id", "inquiry_id"),
        Index("idx_project_stage_id", "stage_id"),
        Index("idx_project_status_priority", "status", "priority"),
        Index("idx_project_created_at", "created_at"),
        Index("idx_project_code", "project_code"),
    )


    def __repr__(self):
        return f"<Project {self.id} - {self.name} - {self.customer_name}>"

    @property
    def is_over_budget(self) -> bool:
        """Cek apakah project melebihi estimasi biaya."""
        return self.actual_cost > self.estimated_cost

    @property
    def display_name(self) -> str:
        """Display name untuk UI."""
        return f"{self.project_code or 'PRJ'} - {self.name}"


class ProjectTask(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_project_tasks"

    project_id: Mapped[UUID] = mapped_column(ForeignKey("tb_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="todo", index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assigned_to: Mapped[str | None] = mapped_column(String(100), nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    estimated_hours: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)  # NEW
    actual_hours: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)  # NEW

    project = relationship("Project", back_populates="tasks")

    __table_args__ = (
        CheckConstraint("sort_order >= 0", name="ck_task_sort_order_non_negative"),
        Index("idx_project_tasks_status", "status"),
        Index("idx_project_tasks_assigned_to", "assigned_to"),
    )

    def __repr__(self):
        return f"<ProjectTask {self.id} - {self.title}>"

class ProjectExpense(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_project_expenses"

    project_id: Mapped[UUID] = mapped_column(ForeignKey("tb_projects.id", ondelete="CASCADE"), nullable=False, index=True )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    expense_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    receipt_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_billable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    approved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)  # NEW
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # NEW

    project = relationship("Project", back_populates="expenses")

    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_expense_amount_non_negative"),
        Index("idx_project_expenses_category", "category")
    )

    def __repr__(self):
        return f"<ProjectExpense {self.id} - {self.name} - {self.amount}>"


class ProjectStage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_project_stages"

    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    color: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True)  # NEW

    projects = relationship("Project", back_populates="stage")

    def __repr__(self):
        return f"<ProjectStage - {self.id} - {self.name}>"


class ProjectActivity(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_project_activities"

    project_id: Mapped[UUID] = mapped_column(ForeignKey("tb_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    activity: Mapped[str] = mapped_column(String(255), nullable=False)
    activity_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    performed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meta_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    project = relationship("Project", back_populates="activities")
    
    __table_args__ = (
        Index("idx_project_activities_type", "activity_type"),
        Index("idx_project_activities_performed_by", "performed_by")
    )
    
    def __repr__(self):
        return f"<ProjectActivity - {self.id} - {self.activity}>"


class ProjectLabor(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_project_labor"

    project_id: Mapped[UUID] = mapped_column(ForeignKey("tb_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    labor_type: Mapped[str] = mapped_column(String(100), nullable=False)
    hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    rate_per_hour: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    technical_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    date_performed: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    project = relationship("Project", back_populates="labor_items")

    __table_args__ = (
        CheckConstraint("hours >= 0", name="ck_labor_hours_non_negative"),
        CheckConstraint("rate_per_hour >= 0", name="ck_labor_rate_non_negative"),
        Index("idx_project_labor_type", "labor_type")
    )

    def __repr__(self):
        return f"<ProjectLabor - {self.id} - {self.labor_type} - {self.hours}>"


# =============================================================================
# Project Price List Item (Junction Table)
# =============================================================================

class ProjectPriceListItem(Base, UUIDMixin, TimestampMixin):
    """Junction table untuk project dan price list items."""
    __tablename__ = "tb_project_price_list_items"

    project_id: Mapped[UUID] = mapped_column(ForeignKey("tb_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    price_list_item_id: Mapped[UUID] = mapped_column(ForeignKey("tb_price_list.id", ondelete="CASCADE"), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True, default=0)
    final_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    project = relationship("Project", back_populates="price_list_items")
    price_list_item = relationship("PriceListItem", back_populates="project_usages")

    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="ck_project_price_quantity_positive"
        ),
        CheckConstraint(
            "unit_price >= 0",
            name="ck_project_price_unit_price_non_negative"
        ),
        CheckConstraint(
            "total_price >= 0",
            name="ck_project_price_total_price_non_negative"
        ),
        CheckConstraint(
            "final_price >= 0",
            name="ck_project_price_final_price_non_negative"
        ),
        Index("idx_project_price_project", "project_id"),
        Index("idx_project_price_item", "price_list_item_id"),
        Index("idx_project_price_project_item", "project_id", "price_list_item_id", unique=True),
    )

    def __repr__(self):
        return f"<ProjectPriceListItem {self.id} - {self.project_id} - {self.price_list_item_id}>"


class ProjectDocument(Base, UUIDMixin, TimestampMixin):
    """Dokumen project."""
    __tablename__ = "tb_project_documents"

    project_id: Mapped[UUID] = mapped_column(ForeignKey("tb_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # spk, bast, invoice, design, photo, other
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    uploaded_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True)

    # Relationships
    project = relationship("Project", back_populates="documents")

    __table_args__ = (
        Index("idx_project_documents_project_type", "project_id", "document_type"),
        Index("idx_project_documents_type", "document_type")
    )

    def __repr__(self):
        return f"<ProjectDocument {self.id} - {self.name}>"


class ProjectTeam(Base, UUIDMixin, TimestampMixin):
    """Tim project."""
    __tablename__ = "tb_project_teams"

    project_id: Mapped[UUID] = mapped_column(ForeignKey("tb_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("tb_users.id", ondelete="CASCADE"), nullable=False, index=True)
    # project_manager, supervisor, technician
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    project = relationship("Project", back_populates="team_members")
    
    __table_args__ = (
        Index("idx_project_team_project", "project_id"),
        Index("idx_project_team_user", "user_id"),
        Index("idx_project_team_role", "role")
    )


class ProjectTimeline(Base, UUIDMixin, TimestampMixin):
    """Timeline/milestone project."""
    __tablename__ = "tb_project_timelines"

    project_id: Mapped[UUID] = mapped_column(ForeignKey("tb_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    milestone_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True) 
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending") # pending, in_progress, completed, overdue, cancelled
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reminder_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    project = relationship("Project", back_populates="timeline")

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'in_progress', 'completed', 'overdue', 'cancelled')", name="ck_timeline_status"),
        Index("idx_project_timelines_project_status", "project_id", "status"),
        Index("idx_project_timelines_due_date", "due_date"),
        Index("idx_project_timelines_status", 'status')
    )

    def __repr__(self):
        return f"<ProjectTimeline {self.id} - {self.milestone_name}>"

