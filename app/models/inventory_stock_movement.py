# app/models/inventory/stock_movement.py
from sqlalchemy import String, Integer, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base, UUIDMixin, TimestampMixin


class StockMovement(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_inventory_stock_movements"

    item_id: Mapped[str] = mapped_column(ForeignKey("items.id"), nullable=False)

    type: Mapped[str] = mapped_column(String(30), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    reference_type: Mapped[str] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[str] = mapped_column(String(100), nullable=True)

    note: Mapped[str] = mapped_column(Text, nullable=True)