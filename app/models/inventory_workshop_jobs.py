# app/models/inventory/workshop_job.py
from sqlalchemy import String, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base, UUIDMixin, TimestampMixin


class WorkshopJob(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_inventory_workshop_jobs"

    unit_name: Mapped[str] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")

    estimated_cost: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    actual_cost: Mapped[float] = mapped_column(Numeric(12, 2), default=0)