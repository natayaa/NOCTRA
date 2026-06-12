# app/models/inventory/job_material_usage.py
from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base, UUIDMixin, TimestampMixin


class JobMaterialUsage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_inventory_job_material_usage"

    job_id: Mapped[str] = mapped_column(ForeignKey("workshop_jobs.id"), nullable=False)
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id"), nullable=False)

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)