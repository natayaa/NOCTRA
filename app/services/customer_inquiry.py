import os
from pathlib import Path
from uuid import uuid4, UUID

from fastapi import UploadFile

from models.customer_inquiry import CustomerInquiry, CustomerInquiryPhoto
from repositories.customer_inquiry import InquiryRepo
from schemas.customer_inquiry import CustomerInquiryRequest


UPLOAD_DIR = Path("uploads/customer_inquiries")


class InquiryService:
    def __init__(self, repo: InquiryRepo):
        self.repo = repo

    # -----------------------------
    # CREATE INQUIRY + PHOTOS
    # -----------------------------
    async def create_inquiry(
        self,
        request: CustomerInquiryRequest,
        photos: list[UploadFile] | None = None,
    ) -> CustomerInquiry:

        inquiry = CustomerInquiry(
            **request.model_dump(exclude_none=True)
        )

        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        if photos:
            inquiry.photos = []

            for photo in photos:
                if not photo.filename:
                    continue

                extension = Path(photo.filename).suffix.lower()
                filename = f"{uuid4()}{extension}"
                file_path = UPLOAD_DIR / filename

                content = await photo.read()

                with open(file_path, "wb") as f:
                    f.write(content)

                inquiry.photos.append(
                    CustomerInquiryPhoto(
                        file_path=str(file_path)
                    )
                )

        return await self.repo.create(inquiry)
    
    # ADD PHOTOS
    async def add_photos(self, inquiry_id: UUID, photos: list[UploadFile]):
        inquiry = await self.repo.get(inquiry_id)

        if not inquiry:
            raise ValueError("Inquiry not found")

        upload_dir = Path(f"{UPLOAD_DIR}/{inquiry_id}")
        upload_dir.mkdir(parents=True, exist_ok=True)

        photo_entities = []

        for photo in photos:
            if not photo.filename:
                continue

            extension = Path(photo.filename).suffix.lower()
            filename = f"{uuid4()}{extension}"
            file_path = upload_dir / filename

            content = await photo.read()

            with open(file_path, "wb") as f:
                f.write(content)

            photo_entities.append(
                CustomerInquiryPhoto(
                    inquiry_id=inquiry_id,
                    file_path=str(file_path)
                )
            )

        self.repo.db.add_all(photo_entities)
        await self.repo.db.commit()

        return len(photo_entities)

    # -----------------------------
    # GET INQUIRY
    # -----------------------------
    async def get_inquiry(self, inquiry_id: UUID) -> CustomerInquiry | None:
        return await self.repo.get(inquiry_id)

    async def get_inquiry_with_photos(self, inquiry_id: UUID) -> CustomerInquiry | None:
        return await self.repo.get_inquiry_with_photos(inquiry_id)

    # -----------------------------
    # DELETE INQUIRY
    # -----------------------------
    async def delete_inquiry(self, inquiry_id: UUID) -> bool:
        return await self.repo.delete(inquiry_id)

    # -----------------------------
    # WORKFLOW: APPROVE
    # -----------------------------
    async def approve_inquiry(self, inquiry_id: UUID) -> CustomerInquiry | None:
        inquiry = await self.repo.get(inquiry_id)

        if not inquiry:
            return None

        inquiry.status = "APPROVED"

        await self.repo.db.flush()
        return inquiry

    # -----------------------------
    # WORKFLOW: REJECT
    # -----------------------------
    async def reject_inquiry(
        self,
        inquiry_id: UUID,
        reason: str
    ) -> CustomerInquiry | None:

        inquiry = await self.repo.get(inquiry_id)

        if not inquiry:
            return None

        inquiry.status = "REJECTED"
        inquiry.note = reason

        await self.repo.db.flush()
        return inquiry

    # -----------------------------
    # WORKFLOW: SEND QUOTATION
    # -----------------------------
    async def send_quotation(
        self,
        inquiry_id: UUID,
        estimated_cost: float,
        estimated_revenue: float
    ) -> CustomerInquiry | None:

        inquiry = await self.repo.get(inquiry_id)

        if not inquiry:
            return None

        inquiry.status = "QUOTATION_SENT"
        inquiry.estimated_cost = estimated_cost
        inquiry.estimated_revenue = estimated_revenue

        await self.repo.db.flush()
        return inquiry

    # -----------------------------
    # WORKFLOW: NOTIFY CUSTOMER
    # -----------------------------
    async def notify_customer(
        self,
        inquiry_id: UUID,
        channel: str = "email"
    ) -> CustomerInquiry | None:

        inquiry = await self.repo.get(inquiry_id)

        if not inquiry:
            return None

        inquiry.status = "NOTIFIED"

        # placeholder integration (email / whatsapp / sms)
        # nanti bisa dipindah ke service external
        print(f"Notify via {channel}: {inquiry.customer_name}")

        await self.repo.db.flush()
        return inquiry

    # -----------------------------
    # WORKFLOW: CONVERT TO PROJECT
    # -----------------------------
    async def convert_to_project(
        self,
        inquiry_id: UUID
    ):
        """
        Placeholder hook:
        nanti dihubungkan ke ProjectService
        """

        inquiry = await self.repo.get(inquiry_id)

        if not inquiry:
            return None

        inquiry.status = "CONVERTED"

        await self.repo.db.flush()
        return inquiry
    
    async def _save_photos(
        self,
        inquiry: CustomerInquiry,
        photos: list[UploadFile]
    ):
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        inquiry.photos = []

        for photo in photos:
            if not photo.filename:
                continue

            ext = Path(photo.filename).suffix.lower()
            filename = f"{uuid4()}{ext}"
            path = UPLOAD_DIR / filename

            content = await photo.read()

            with open(path, "wb") as f:
                f.write(content)

            inquiry.photos.append(
                CustomerInquiryPhoto(
                    inquiry_id=inquiry.id,   # penting untuk consistency
                    file_path=str(path)
                )
            )
            
    async def delete_inquiry(self, inquiry_id: UUID) -> bool:
        inquiry = await self.repo.get_inquiry_with_photos(inquiry_id)

        if not inquiry:
            return False

        # delete physical files
        for photo in inquiry.photos:
            try:
                if photo.file_path and os.path.exists(photo.file_path):
                    os.remove(photo.file_path)
            except Exception:
                pass

        return await self.repo.delete(inquiry_id)

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