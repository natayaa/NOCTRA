from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base, UUIDMixin, TimestampMixin

class CustomerInquiry(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tb_customer_inquiry"
    
    customer_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    customer_phone_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    customer_email: Mapped[str] = mapped_column(String(50), nullable=False, index=False)
    vehicle_brand: Mapped[str] = mapped_column(String(50), nullable=False)
    vehicle_model: Mapped[str] = mapped_column(String(50), nullable=False)
    vehicle_license_plate: Mapped[str | None] = mapped_column(String(50), nullable=True)
    vehicle_condition: Mapped[str] = mapped_column(String(200), nullable=False)
    project_type: Mapped[str] = mapped_column(String(100), nullable=False)
    project_description: Mapped[str] = mapped_column(Text, nullable=False)
    project_target: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reference_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    