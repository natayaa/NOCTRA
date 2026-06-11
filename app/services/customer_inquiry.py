from repositories.customer_inquiry import InquiryRepo
from models.customer_inquiry import CustomerInquiry
from schemas.customer_inquiry import CustomerInquiryRequest

class InquiryService:
    def __init__(self, repo: InquiryRepo):
        self.repo = repo
        
    async def create_inquiry(self, request: CustomerInquiryRequest) -> CustomerInquiry:
        inquiry = CustomerInquiry(**request.model_dump())
        return await self.repo.create(inquiry)
    