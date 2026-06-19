# models/price_list.py
from sqlalchemy import String, Numeric, Text, Boolean, Date
from sqlalchemy.orm import Mapped, mapped_column
from datetime import date
from database.base import Base, UUIDMixin, TimestampMixin


class PriceListItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_price_list"

    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # e.g. "service", "material", "labor", "bike_model"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)  # "per job", "per liter", "per hour"

    # Optional: link to a specific bike brand/model (if price varies by vehicle)
    vehicle_brand: Mapped[str | None] = mapped_column(String(50), nullable=True)
    vehicle_model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    effective_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # For services, you might also store estimated time, etc. (optional)