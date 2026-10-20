from __future__ import annotations

from uuid import UUID

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDMixin


class VehicleBrand(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "vehicle_brands"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    country: Mapped[str | None] = mapped_column(String(64))

    def __repr__(self) -> str:
        return f"<VehicleBrand {self.name}>"


class VehicleModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "vehicle_models"
    __table_args__ = (
        UniqueConstraint("brand_id", "name", name="uq_vehicle_models_brand_name"),
    )

    # Composite unique (brand_id, name) serves as the index for brand_id
    # lookups — no standalone index needed.
    brand_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("vehicle_brands.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str | None] = mapped_column(String(20))

    def __repr__(self) -> str:
        return f"<VehicleModel {self.name}>"


class Vehicle(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "vehicles"
    __table_args__ = (
        Index("ix_vehicles_customer", "customer_id"),
        Index("ix_vehicles_plate", "plate_number"),
        Index("ix_vehicles_brand", "brand_id"),
        Index("ix_vehicles_model", "model_id"),
        # DB-level guard against duplicate plate per customer. Service layer
        # also enforces this; the constraint is the final backstop against
        # a race between two concurrent creates.
        UniqueConstraint(
            "customer_id", "plate_number", name="uq_vehicles_customer_plate",
        ),
    )

    # `index=True` removed — covered by ix_vehicles_customer.
    customer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
    )

    plate_number: Mapped[str | None] = mapped_column(String(20))
    brand: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    year: Mapped[int | None] = mapped_column(Integer)
    color: Mapped[str | None] = mapped_column(String(64))
    category: Mapped[str | None] = mapped_column(String(20), index=True)
    vin: Mapped[str | None] = mapped_column(String(64))
    engine_number: Mapped[str | None] = mapped_column(String(64))
    notes: Mapped[str | None] = mapped_column(Text)

    brand_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("vehicle_brands.id", ondelete="SET NULL"),
    )
    model_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("vehicle_models.id", ondelete="SET NULL"),
    )

    def __repr__(self) -> str:
        plate = self.plate_number or "—"
        return f"<Vehicle {self.brand} {self.model} {plate}>"