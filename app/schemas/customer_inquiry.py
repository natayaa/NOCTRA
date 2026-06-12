from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict
from typing_extensions import Optional

from uuid import UUID


class CustomerInquiryRequest(BaseModel):
    customer_name: str = Field(min_length=2, max_length=100,)
    customer_phone_number: str = Field(min_length=8, max_length=20,)
    customer_email: EmailStr
    vehicle_brand: str = Field(min_length=1, max_length=50,)
    vehicle_model: str = Field(min_length=1, max_length=100,)
    vehicle_license_plate: str | None = Field(default=None, max_length=20,)
    vehicle_condition: str = Field(min_length=1, max_length=100,)
    project_type: str = Field(min_length=1, max_length=50,)
    project_description: str = Field(min_length=10, max_length=5000,)
    project_target: str | None = Field(default=None, max_length=255,)
    reference_link: str | None = None
    
    @field_validator("*", mode="before")
    @classmethod
    def strip_strings(cls, value):
        if isinstance(value, str):
            return value.strip()

        return value
    
class CustomerInquiryPhotoResponse(BaseModel):
    id: str
    file_path: str
    
    model_config = {
        "from_attributes": True
    }
    
class CustomerInquiryResponse(BaseModel):
    id: UUID
    
    customer_name: str
    customer_phone_number: str
    customer_email: Optional[str]
    
    message: str
    status: str # NEW | REVIEW | APPROVED | REJECTED | QUOTATION_SENT | NOTIFIED | CONVERTED
    
    model_config = ConfigDict(from_attributes=True)
    
class InquiryApproved(BaseModel):
    note: Optional[str] = None
    
class InquiryReject(BaseModel):
    reason: str
    
class InquirySendQuotation(BaseModel):
    estimated_cost: float
    estimated_revenue: float
    
class InquiryNotifyCustomer(BaseModel):
    channel: str = Field(default="email") # email | Whatsapp | telegram
    
