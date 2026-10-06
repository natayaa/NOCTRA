"""Pricing rule + pricing snapshot models."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDMixin


# ════════════════════════════════════════════════════════════════
# PRICING RULES
#
# A rule matches on (service_interest, vehicle_category). Both can be
# NULL. The most specific match wins.
#
#   service + category  → specificity 3
#   service only        → specificity 2
#   category only       → specificity 1
#   neither (default)   → specificity 0
# ════════════════════════════════════════════════════════════════

class PricingRule(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "pricing_rules"
    __table_args__ = (
        Index("ix_pricing_rules_match", "service_interest", "vehicle_category"),
        Index("ix_pricing_rules_active", "is_active"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    # Match criteria — NULL means "any"
    service_interest: Mapped[str | None] = mapped_column(String(32))
    vehicle_category: Mapped[str | None] = mapped_column(String(50))

    # Pricing math
    target_margin_pct: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=50, server_default="50",
    )
    min_margin_pct: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=30, server_default="30",
    )
    complexity_factor: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=1, server_default="1",
    )
    min_price_floor: Mapped[float | None] = mapped_column(Numeric(14, 2))

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, server_default="true",
    )

    def __repr__(self) -> str:
        s = self.service_interest or "*"
        c = self.vehicle_category or "*"
        return f"<PricingRule {self.name} [{s}/{c}] {self.target_margin_pct}%>"


# ════════════════════════════════════════════════════════════════
# PRICING SNAPSHOTS
#
# Immutable record of a pricing decision. Stored whenever a
# recommendation is applied to an inquiry or project.
# ════════════════════════════════════════════════════════════════

class PricingSnapshot(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "pricing_snapshots"
    __table_args__ = (
        Index("ix_pricing_snapshots_inquiry", "inquiry_id"),
        Index("ix_pricing_snapshots_project", "project_id"),
    )

    # Optional links to the domain object being priced
    inquiry_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("inquiries.id", ondelete="SET NULL"),
    )
    project_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
    )

    # Snapshot of the inputs
    service_interest: Mapped[str | None] = mapped_column(String(32))
    vehicle_category: Mapped[str | None] = mapped_column(String(50))
    hpp_estimate: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)

    # Snapshot of the rule used (denormalized so rule changes don't rewrite history)
    rule_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("pricing_rules.id", ondelete="SET NULL"),
    )
    rule_name: Mapped[str | None] = mapped_column(String(255))
    target_margin_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    min_margin_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    complexity_factor: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=1, server_default="1",
    )

    # The recommendation
    recommended_price: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    minimum_price: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)

    # What was actually quoted (if different from recommended)
    actual_quoted_price: Mapped[float | None] = mapped_column(Numeric(14, 2))
    actual_margin_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))

    notes: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    def __repr__(self) -> str:
        return f"<PricingSnapshot hpp={self.hpp_estimate} → {self.recommended_price}>"