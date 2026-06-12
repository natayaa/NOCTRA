from sqlalchemy import String, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base, UUIDMixin, TimestampMixin


class InventoryItems(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_inventory_items"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)

    cost_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    selling_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0)

    current_stock: Mapped[int] = mapped_column(Integer, default=0)
    min_stock_threshold: Mapped[int] = mapped_column(Integer, default=0)

    status: Mapped[str] = mapped_column(String(20), default="active")