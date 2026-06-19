# services/customer_inquiry.py
import os
from pathlib import Path
from uuid import uuid4, UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from models.customer_inquiry import CustomerInquiry, CustomerInquiryPhoto
from repositories.customer_inquiry import InquiryRepo
from schemas.customer_inquiry import CustomerInquiryRequest
from schemas.constants import InquiryStatus


UPLOAD_DIR = Path("uploads/customer_inquiries")


class InquiryService:
    """
    Service layer for customer inquiries.
    Handles creation, status updates, quoting, rejection, conversion to projects,
    and photo uploads.
    """

    def __init__(self, repo: InquiryRepo):
        self.repo = repo

    # -------------------------------------------------------------------------
    # Core CRUD
    # -------------------------------------------------------------------------

    async def create_inquiry(
        self,
        request: CustomerInquiryRequest,
        photos: list[UploadFile] | None = None,
    ) -> CustomerInquiry:
        """
        Create a new inquiry with optional photo uploads.
        """
        inquiry = CustomerInquiry(**request.model_dump(exclude_none=True))
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        if photos:
            for photo in photos:
                if not photo.filename:
                    continue
                ext = Path(photo.filename).suffix.lower()
                filename = f"{uuid4()}{ext}"
                file_path = UPLOAD_DIR / filename
                content = await photo.read()
                with open(file_path, "wb") as f:
                    f.write(content)
                inquiry.photos.append(
                    CustomerInquiryPhoto(file_path=str(file_path))
                )

        return await self.repo.create(inquiry)

    async def list_inquiries(
        self,
        status: str | None = None,
        search: str | None = None,
    ) -> list[CustomerInquiry]:
        """List all inquiries with optional status and search filters."""
        return await self.repo.list_all(status=status, search=search)

    async def get_inquiry(self, inquiry_id: UUID) -> CustomerInquiry | None:
        """Retrieve a single inquiry with all related data (photos, activities, project)."""
        return await self.repo.get_inquiry_with_details(inquiry_id)

    # -------------------------------------------------------------------------
    # Status Management
    # -------------------------------------------------------------------------

    async def update_status(self, inquiry_id: UUID, status: str) -> bool:
        """Update the status of an inquiry. Raises ValueError if status is invalid."""
        if status not in [e.value for e in InquiryStatus]:
            raise ValueError(f"Invalid status: {status}")
        return await self.repo.update_status(inquiry_id, status)

    async def reject_inquiry(self, inquiry_id: UUID, reason: str) -> bool:
        """
        Reject an inquiry with an optional reason.
        Stores the reason in the 'note' field.
        """
        success = await self.repo.update_status(inquiry_id, InquiryStatus.REJECTED)
        if success and reason:
            inquiry = await self.repo.get_inquiry(inquiry_id)
            if inquiry:
                inquiry.note = reason
                await self.repo.db.flush()
        return success

    async def send_quote(self, inquiry_id: UUID, estimated_cost: float) -> bool:
        """
        Send a quotation to the customer.
        Updates status to 'quoted' and stores the quote amount in the note.
        Also adds an activity entry.
        """
        inquiry = await self.repo.get_inquiry(inquiry_id)
        if not inquiry:
            return False
        inquiry.status = InquiryStatus.QUOTED
        inquiry.note = f"Quoted: Rp {estimated_cost:,.2f}"
        await self.repo.db.flush()
        await self.repo.add_activity(
            inquiry_id,
            f"Quotation sent: Rp {estimated_cost:,.2f}"
        )
        return True

    async def update_notes(self, inquiry_id: UUID, note: str) -> bool:
        """Update the internal notes of an inquiry."""
        inquiry = await self.repo.get_inquiry(inquiry_id)
        if not inquiry:
            return False
        inquiry.note = note
        await self.repo.db.flush()
        return True

    # -------------------------------------------------------------------------
    # Conversion to Project
    # -------------------------------------------------------------------------

    async def convert_to_project(self, inquiry_id: UUID) -> CustomerInquiry | None:
        """
        Convert an inquiry to a project.
        Updates status to 'converted' and adds an activity entry.
        """
        inquiry = await self.repo.get_inquiry_with_details(inquiry_id)
        if not inquiry:
            return None
        inquiry.status = InquiryStatus.CONVERTED
        await self.repo.db.flush()
        await self.repo.add_activity(inquiry_id, "Converted to project")
        return inquiry


class InquiryPhotoService:
    """
    Service for handling photo uploads related to inquiries.
    Separated from InquiryService to keep single responsibility.
    """

    def __init__(self, repo: InquiryRepo):
        self.repo = repo

    async def upload_photos(
        self,
        inquiry_id: UUID,
        photos: list[UploadFile],
    ) -> list[CustomerInquiryPhoto]:
        """
        Upload multiple photos for an inquiry.
        Saves files to disk and creates Photo records in the database.
        """
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        photo_models = []

        for photo in photos:
            if not photo.filename:
                continue
            ext = Path(photo.filename).suffix.lower()
            filename = f"{uuid4()}{ext}"
            file_path = UPLOAD_DIR / filename

            content = await photo.read()
            with open(file_path, "wb") as f:
                f.write(content)

            photo_models.append(
                CustomerInquiryPhoto(
                    inquiry_id=inquiry_id,
                    file_path=str(file_path),
                )
            )

        return photo_models