import os
from pathlib import Path
from uuid import uuid4, UUID

from fastapi import UploadFile

from models.customer_inquiry import CustomerInquiry, CustomerInquiryPhoto
from repositories.customer_inquiry import InquiryRepo
from schemas.customer_inquiry import CustomerInquiryRequest
from schemas.constants import InquiryStatus


UPLOAD_DIR = Path("uploads/customer_inquiries")


class InquiryService:
    def __init__(self, repo: InquiryRepo):
        self.repo = repo

    async def create_inquiry(self, request: CustomerInquiryRequest, photos: list[UploadFile] | None = None) -> CustomerInquiry:
        inquiry = CustomerInquiry(**request.model_dump(exclude_none=True))
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        if photos:
            for photo in photos:
                if not photo.filename: continue
                ext = Path(photo.filename).suffix.lower()
                filename = f"{uuid4()}{ext}"
                file_path = UPLOAD_DIR / filename
                content = await photo.read()
                with open(file_path, "wb") as f:
                    f.write(content)
                inquiry.photos.append(CustomerInquiryPhoto(file_path=str(file_path)))
        return await self.repo.create(inquiry)

    async def list_inquiries(self, status: str | None, search: str | None) -> list[CustomerInquiry]:
        return await self.repo.list_all(status=status, search=search)

    async def get_inquiry(self, inquiry_id: UUID) -> CustomerInquiry | None:
        return await self.repo.get_with_details(inquiry_id)

    async def update_status(self, inquiry_id: UUID, status: str) -> bool:
        if status not in [e.value for e in InquiryStatus]:
            raise ValueError("Invalid status")
        return await self.repo.update_status(inquiry_id, status)

    async def reject_inquiry(self, inquiry_id: UUID, reason: str) -> bool:
        success = await self.repo.update_status(inquiry_id, InquiryStatus.REJECTED)
        if success and reason:
            inquiry = await self.repo.get(inquiry_id)
            if inquiry:
                inquiry.note = reason
                await self.repo.db.flush()
        return success

    async def send_quote(self, inquiry_id: UUID, estimated_cost: float) -> bool:
        inquiry = await self.repo.get(inquiry_id)
        if not inquiry:
            return False
        inquiry.status = InquiryStatus.QUOTED
        # store estimated cost somewhere – you can add a field estimated_cost in model
        # For simplicity, we'll add a column later or use note. Adjust as needed.
        inquiry.note = f"Quoted: Rp {estimated_cost:,.2f}"
        await self.repo.db.flush()
        await self.repo.add_activity(inquiry_id, f"Quotation sent: Rp {estimated_cost:,.2f}")
        return True

    async def update_notes(self, inquiry_id: UUID, note: str) -> bool:
        inquiry = await self.repo.get(inquiry_id)
        if not inquiry:
            return False
        inquiry.note = note
        await self.repo.db.flush()
        return True

    async def convert_to_project(self, inquiry_id: UUID) -> CustomerInquiry | None:
        inquiry = await self.repo.get_with_details(inquiry_id)
        if not inquiry:
            return None
        inquiry.status = InquiryStatus.CONVERTED
        await self.repo.db.flush()
        await self.repo.add_activity(inquiry_id, "Converted to project")
        return inquiry

class InquiryPhotoService:
    def __init__(self, repo):
        self.repo = repo
        
    async def upload_photos(self, inquiry_id: UUID, photos: list[UploadFile]):
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        photo_models = []
        for photo in photos:
            extension = Path(photo.filename).suffix.lower()
            filename = (f"{uuid4()}{extension}")
            filepath = (UPLOAD_DIR / filename)
            content = await photo.read()
            
            with open(filepath, "wb") as f:
                f.write(content)
                
            photo_models.append(
                CustomerInquiryPhoto(
                    inquiry_id=inquiry_id, 
                    file_path=str(filepath)
                )
            )
            
        return photo_models