from sqlalchemy import ForeignKey, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.base import Base, UUIDMixin, TimestampMixin
from uuid import UUID

class JobMaterialUsage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_inventory_job_material_usage"

    job_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tb_inventory_workshop_jobs.id", ondelete="SET NULL"),
        nullable=True  # ← WAJIB ada
    )
    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tb_projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    item_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_inventory_items.id", ondelete="CASCADE"),
        nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    job = relationship("WorkshopJob", back_populates="material_usages")
    project = relationship("Project", back_populates="material_usages")
    item = relationship("InventoryItems")