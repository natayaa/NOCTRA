from pydantic import (BaseModel, Field, EmailStr, field_validator)
from typing import Optional

class CustomerInquiryRequest(BaseModel):
    customer_name: str = Field(
        min_length=2,
        max_length=100,
    )
    customer_phone_number: str = Field(
        min_length=8,
        max_length=20,
    )
    customer_email: EmailStr
    vehicle_brand: str = Field(
        min_length=1,
        max_length=50,
    )
    vehicle_model: str = Field(
        min_length=1,
        max_length=100,
    )
    vehicle_license_plate: Optional[str] = Field(
        default=None,
        max_length=20,
    )
    vehicle_condition: str = Field(
        min_length=1,
        max_length=100,
    )
    project_type: str = Field(
        min_length=1,
        max_length=50,
    )
    project_description: str = Field(
        min_length=10,
        max_length=5000,
    )
    project_target: Optional[str] = Field(
        default=None,
        max_length=255,
    )
    reference_link: Optional[str] = None
    @field_validator("*", mode="before")
    @classmethod
    def strip_strings(cls, value):
        if isinstance(value, str):
            return value.strip()

        return value