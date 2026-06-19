from sqlalchemy import String, Integer, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from database.base import Base, UUIDMixin, TimestampMixin
from uuid import UUID

class StockMovement(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_inventory_stock_movements"

    item_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_inventory_items.id", ondelete="CASCADE"),
        nullable=False
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[UUID | None] = mapped_column(nullable=True)  # ← UUID, bukan String
    note: Mapped[str | None] = mapped_column(Text, nullable=True)