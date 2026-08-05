from typing_extensions import Dict, Optional, List
from uuid import uuid4
from datetime import datetime

from sqlalchemy import (
    UUID, Boolean, DateTime,
    Float, Integer, String, Text, Enum as SQLEnum,
    ForeignKey, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from core.base import Base, UUIDMixin, TimestampMixin
from core.enum import RestoredBikeStatus, InitialCondition


class RestoredBike(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_restored_bikes"
    # id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Vehicle Information
    brand: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    license_plate: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True)

    # Customer & Purchase
    customer_name: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True)
    purchase_price: Mapped[Optional[float]
                           ] = mapped_column(Float, nullable=True)
    purchase_source: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True)
    initial_condition: Mapped[Optional[InitialCondition]] = mapped_column(
        SQLEnum(InitialCondition, name="initial_condition"), nullable=True)

    # Restoration Details
    restoration_cost: Mapped[Optional[float]
                             ] = mapped_column(Float, nullable=True)
    restoration_duration: Mapped[Optional[int]
                                 ] = mapped_column(Integer, nullable=True)
    technician_name: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True)
    status: Mapped[RestoredBikeStatus] = mapped_column(SQLEnum(
        RestoredBikeStatus, name="restored_bike_status"), nullable=False, default=RestoredBikeStatus.COMPLETED)
    restoration_notes: Mapped[Optional[str]
                              ] = mapped_column(Text, nullable=True)

    # Meta Data
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationship
    photos: Mapped[List['RestoredBikePhoto']] = relationship(
        "RestoredBikePhoto", back_populates="bike", cascade="all, delete-orphan", lazy="selectin")
    documents: Mapped[List['RestoredBikeDocument']] = relationship(
        "RestoredBikeDocument", back_populates="bike", cascade="all, delete-orphan", lazy="selectin")

    __table_args__ = (
        Index("ix_restored_bikes_brand_model", "brand", "model"),
        Index("ix_restored_bikes_status", "status"),
        Index("ix_restored_bikes_customer_name", "customer_name")
    )

    def __repr__(self):
        return f"<RestoredBike {self.brand} - {self.model}>"


class RestoredBikePhoto(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_restored_bike_photos"

    bike_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey(
        "restored_bikes.id", ondelete="CASCADE"), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    filename: Mapped[str] = mapped_column(String(200), nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # relationship
    bike: Mapped["RestoredBike"] = relationship(
        "RestoredBike", back_populates="photos")

    __table_args__ = (
        Index("ix_restored_bike_photos_bike_id", "bike_id"),
        Index("ix_restored_bike_photos_is_primary", "is_primary")
    )

    def __repr__(self):
        return f"<RestoredBikePhotos {self.filename}>"


class RestoredBikeDocument(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_restored_bike_document"

    bike_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    filename: Mapped[str] = mapped_column(String(200), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    document_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    bike: Mapped["RestoredBike"] = relationship(
        "RestoredBike",
        back_populates="documents",
    )

    __table_args__ = (
        Index("ix_restored_bike_documents_bike_id", "bike_id"),
        Index("ix_restored_bike_documents_document_type", "document_type"),
    )

    def __repr__(self):
        return f"<RestoredBikeDocument {self.filename}>"
