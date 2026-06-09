from pydantic import BaseModel, Field, field_validator, EmailStr

class CustomerInquiryRequest(BaseModel):
    """
        Post Request from Customer
    """
    customer_name: str
    customer_phone_number: str
    customer_email: EmailStr
    vehicle_brand: str
    vehicle_model: str
    vehicle_license_plate: str = ""
    vehicle_condition: str
    project_type: str
    project_description: str
    project_target: str = ""
    reference_link: str
    