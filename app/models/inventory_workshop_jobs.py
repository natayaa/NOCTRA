# models/inventory/inventory_workshop_jobs.py
from sqlalchemy import String, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.base import Base, UUIDMixin, TimestampMixin
from uuid import UUID

class WorkshopJob(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_inventory_workshop_jobs"

    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tb_projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    unit_name: Mapped[str] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")

    estimated_cost: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    actual_cost: Mapped[float] = mapped_column(Numeric(12, 2), default=0)

    # relationships
    project = relationship("Project", back_populates="workshop_job")
    material_usages = relationship(
        "JobMaterialUsage",
        back_populates="job",
        cascade="all, delete-orphan"
    )