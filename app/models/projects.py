from sqlalchemy import String, Numeric, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from decimal import Decimal

from database.base import Base, UUIDMixin, TimestampMixin, UUID


class Project(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_projects"

    inquiry_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_customer_inquiry.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)

    vehicle_brand: Mapped[str] = mapped_column(String(50), nullable=False)
    vehicle_model: Mapped[str] = mapped_column(String(100), nullable=False)

    status: Mapped[str] = mapped_column(String(50), default="active", index=True, nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    kanban_stage: Mapped[str] = mapped_column(String(50), default="preparation", nullable=False, index=True)
    
    actual_cost: Mapped[float] = mapped_column(Numeric(12,2), default=0, nullable=False)
    actual_revenue: Mapped[float] = mapped_column(Numeric(12,2), default=0, nullable=False)
    estimated_cost: Mapped[Integer] = mapped_column(Numeric(12, 2), default=0)
    estimated_revenue: Mapped[Integer] = mapped_column(Numeric(12, 2), default=0)
    
    stage_id: Mapped[UUID] = mapped_column(ForeignKey("tb_project_stages.id"), index=True)
    
    inquiry = relationship("CustomerInquiry", back_populates="project")
    
    #task = relationship("ProjectTask", back_populates="project", cascade="all, delete-orphan")
    
    expenses = relationship("ProjectExpense", back_populates="project", cascade="all, delete-orphan")
    
    stage = relationship("ProjectStage")
   
    
class ProjectTask(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_project_tasks"
    
    project_id: Mapped[UUID] = mapped_column(ForeignKey("tb_projects.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(default="todo", nullable=False, index=True)
    
    sort_order: Mapped[int] = mapped_column(default=0)
    
    #project = relationship("Project", back_populates="tasks")
    
    
class ProjectExpense(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_project_expenses"
    
    project_id: Mapped[UUID] = mapped_column(ForeignKey("tb_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    
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
    