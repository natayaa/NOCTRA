from sqlalchemy import String, Numeric, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from decimal import Decimal
from database.base import Base, UUIDMixin, TimestampMixin, UUID
from schemas.constants import ProjectStatus, InquiryStatus
from datetime import datetime


class Project(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_projects"

    inquiry_id: Mapped[UUID | None] = mapped_column(ForeignKey("tb_customer_inquiry.id", ondelete="SET NULL"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    vehicle_brand: Mapped[str] = mapped_column(String(50), nullable=False)
    vehicle_model: Mapped[str] = mapped_column(String(100), nullable=False)

    status: Mapped[str] = mapped_column(String(50), default=ProjectStatus.ACTIVE, index=True, nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    estimated_cost: Mapped[Decimal] = mapped_column(Numeric(12,2), default=0)
    actual_cost: Mapped[Decimal] = mapped_column(Numeric(12,2), default=0)
    estimated_revenue: Mapped[Decimal] = mapped_column(Numeric(12,2), default=0)
    actual_revenue: Mapped[Decimal] = mapped_column(Numeric(12,2), default=0)

    stage_id: Mapped[UUID | None] = mapped_column(ForeignKey("tb_project_stages.id"), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    final_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_archived: Mapped[bool] = mapped_column(default=False)

    # relationships
    inquiry = relationship("CustomerInquiry", back_populates="project")
    expenses = relationship("ProjectExpense", back_populates="project", cascade="all, delete-orphan")
    stage = relationship("ProjectStage")
    tasks = relationship("ProjectTask", back_populates="project", cascade="all, delete-orphan")
    # models/projects.py
    workshop_job = relationship("WorkshopJob", back_populates="project", uselist=False)
    labor_items = relationship("ProjectLabor", back_populates="project", cascade="all, delete-orphan")
    material_usages = relationship("JobMaterialUsage", back_populates="project", cascade="all, delete-orphan")

class ProjectTask(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_project_tasks"
    project_id: Mapped[UUID] = mapped_column(ForeignKey("tb_projects.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(default="todo", nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(default=0)
    project = relationship("Project", back_populates="tasks")

class ProjectExpense(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_project_expenses"
    project_id: Mapped[UUID] = mapped_column(ForeignKey("tb_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12,2), nullable=False)
    project = relationship("Project", back_populates="expenses")

class ProjectStage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_project_stages"
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    color: Mapped[str | None] = mapped_column(String(50))
    sort_order: Mapped[int] = mapped_column(default=0)
    

class ProjectActivity(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_project_activities"
    project_id: Mapped[UUID] = mapped_column(ForeignKey("tb_projects.id", ondelete="CASCADE"))
    activity: Mapped[str] = mapped_column(String(255))
    
    
class ProjectLabor(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_project_labor"

    project_id: Mapped[UUID] = mapped_column(ForeignKey("tb_projects.id", ondelete="CASCADE"), nullable=False)
    labor_type: Mapped[str] = mapped_column(String(100), nullable=False)   # misal "Painter", "Mechanic", "Assembler"
    hours: Mapped[Decimal] = mapped_column(Numeric(10,2), nullable=False, default=0)
    rate_per_hour: Mapped[Decimal] = mapped_column(Numeric(12,2), nullable=False, default=0)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(12,2), nullable=False, default=0)

    project = relationship("Project", back_populates="labor_items")