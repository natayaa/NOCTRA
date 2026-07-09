# modules/price_list/models.py
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Index, String, Numeric, Text, Boolean, Date, ForeignKey, Integer, DateTime, func, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.base import Base, UUIDMixin, TimestampMixin


class PriceListItem(Base, UUIDMixin, TimestampMixin):
    """Model untuk item price list."""
    __tablename__ = "tb_price_list"

    # ============ Core Fields ============
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True)
    sub_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sku: Mapped[str | None] = mapped_column(
        String(50), nullable=True, unique=True)

    # ============ Pricing ============
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cost_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True)

    # ============ Vehicle Specific ============
    vehicle_brand: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True)
    vehicle_model: Mapped[str | None] = mapped_column(
        String(100), nullable=True)

    # ============ Validity ============
    effective_date: Mapped[date] = mapped_column(
        Date, nullable=False, default=date.today)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True)

    # ============ Additional Fields ============
    min_quantity: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=1)
    max_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discount_percentage: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True, default=0)
    is_taxable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True)
    estimated_duration_hours: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True)
    is_discount_allowed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True)

    # ============ Metadata ============
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ============ Relationships ============
    project_usages = relationship(
        "ProjectPriceListItem", back_populates="price_list_item")
    invoice_items = relationship(
        "InvoiceItem", back_populates="price_list_item")
    price_history = relationship(
        "PriceHistory",
        back_populates="item",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="PriceHistory.changed_at.desc()"
    )
    custom_prices = relationship(
        "CustomPrice",
        back_populates="item",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    # ============ Constraints ============
    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_price_list_price_non_negative"),
        CheckConstraint("cost_price IS NULL OR cost_price >= 0",
                        name="ck_price_list_cost_price_non_negative"),
        CheckConstraint("discount_percentage IS NULL OR discount_percentage >= 0",
                        name="ck_price_list_discount_non_negative"),
        Index("idx_price_list_category_active", "category", "is_active"),
        Index("idx_price_list_vehicle_brand", "vehicle_brand"),
    )

    def __repr__(self):
        return f"<PriceListItem {self.id} - {self.category} - {self.name} - {self.price}>"

    @property
    def is_expired(self) -> bool:
        if not self.expiry_date:
            return False
        return date.today() > self.expiry_date

    @property
    def price_change_count(self) -> int:
        return len(self.price_history) if self.price_history else 0


class PriceListCategory(Base, UUIDMixin, TimestampMixin):
    """Model untuk kategori price list."""
    __tablename__ = "tb_price_list_categories"

    name: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    parent_category: Mapped[str | None] = mapped_column(
        String(50), nullable=True)

    def __repr__(self):
        return f"<PriceListCategory {self.id} - {self.name}>"


class PriceListDiscount(Base, UUIDMixin, TimestampMixin):
    """Model untuk diskon price list."""
    __tablename__ = "tb_price_list_discounts"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    discount_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False)
    discount_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True)

    # Applicable scope
    applies_to_category: Mapped[str | None] = mapped_column(
        String(50), nullable=True)
    applies_to_item_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tb_price_list.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    applies_to_all: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False)

    # Validity period
    valid_from: Mapped[date] = mapped_column(
        Date, nullable=False, default=date.today)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True)

    # Usage limits
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    item = relationship("PriceListItem")

    __table_args__ = (
        CheckConstraint("discount_percentage >= 0 AND discount_percentage <= 100",
                        name="ck_discount_percentage_range"),
        CheckConstraint("max_uses IS NULL OR max_uses > 0",
                        name="ck_discount_max_uses_positive"),
        CheckConstraint("used_count >= 0",
                        name="ck_discount_used_count_non_negative"),
        Index("idx_discount_code_active", "code", "is_active"),
        Index("idx_discount_valid_period", "valid_from", "valid_until"),
    )

    def __repr__(self):
        return f"<PriceListDiscount {self.id} - {self.code} - {self.discount_percentage}%>"

    @property
    def is_valid(self) -> bool:
        today = date.today()
        if not self.is_active:
            return False
        if self.valid_until and today > self.valid_until:
            return False
        if self.max_uses and self.used_count >= self.max_uses:
            return False
        return True


class PriceHistory(Base, UUIDMixin, TimestampMixin):
    """Price history untuk tracking perubahan harga."""
    __tablename__ = "tb_price_history"

    item_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_price_list.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    old_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    new_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    changed_by: Mapped[str] = mapped_column(String(100), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    item = relationship("PriceListItem", back_populates="price_history")

    __table_args__ = (
        Index("idx_price_history_item", "item_id"),
        Index("idx_price_history_changed_at", "changed_at"),
        Index("idx_price_history_item_changed", "item_id", "changed_at"),
    )

    def __repr__(self):
        return f"<PriceHistory {self.id} - {self.item_id} - {self.old_price} -> {self.new_price}>"

    @property
    def price_change(self) -> Decimal:
        return self.new_price - self.old_price

    @property
    def price_change_percent(self) -> float:
        if self.old_price == 0:
            return 0
        return float((self.new_price - self.old_price) / self.old_price * 100)


class CustomPrice(Base, UUIDMixin, TimestampMixin):
    """Custom pricing per customer/project."""
    __tablename__ = "tb_custom_prices"

    item_id: Mapped[UUID] = mapped_column(
        ForeignKey("tb_price_list.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    customer_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tb_customers.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tb_projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    custom_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    item = relationship("PriceListItem", back_populates="custom_prices")
    project = relationship(
        "Project",
        foreign_keys="[CustomPrice.project_id]"
    )

    __table_args__ = (
        CheckConstraint("custom_price >= 0",
                        name="ck_custom_price_non_negative"),
        Index("idx_custom_price_customer", "customer_id"),
        Index("idx_custom_price_project", "project_id"),
        Index("idx_custom_price_valid", "valid_from", "valid_until"),
    )

    def __repr__(self):
        return f"<CustomPrice {self.id} - {self.item_id} - {self.custom_price}>"

    @property
    def is_valid(self) -> bool:
        today = date.today()
        if self.valid_until and today > self.valid_until:
            return False
        return True
