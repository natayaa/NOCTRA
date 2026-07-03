# models/price_list.py
from sqlalchemy import String, Numeric, Text, Boolean, Date, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import date
from uuid import UUID

from database.base import Base, UUIDMixin, TimestampMixin


class PriceListItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_price_list"

    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # e.g. "service", "material", "labor", "bike_model", "paint", "finish"

    sub_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)  # "per job", "per liter", "per hour", "per panel"

    # Optional: link to specific vehicle brand/model
    vehicle_brand: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    vehicle_model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Pricing metadata
    effective_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    # Additional fields
    min_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True, default=1)
    max_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discount_percentage: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True, default=0)
    is_taxable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    # For services, store estimated time
    estimated_duration_hours: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    
    # Metadata
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    def __repr__(self):
        return f"<PriceListItem {self.id} - {self.category} - {self.name} - {self.price}>"


class PriceListCategory(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_price_list_categories"

    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)  # For UI

    def __repr__(self):
        return f"<PriceListCategory {self.id} - {self.name}>"


class PriceListDiscount(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_price_list_discounts"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    discount_percentage: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    discount_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    
    # Applicable scope
    applies_to_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    applies_to_item_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tb_price_list.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Validity period
    valid_from: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    # Usage limits
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Relationships
    item = relationship("PriceListItem")

    def __repr__(self):
        return f"<PriceListDiscount {self.id} - {self.code} - {self.discount_percentage}%>"