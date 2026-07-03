# services/customer_inquiry.py
import re
from pathlib import Path
from uuid import uuid4, UUID
from datetime import datetime
from typing import Optional, List

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from models.customer_inquiry import CustomerInquiry, CustomerInquiryPhoto, InquiryActivity, WorkshopNote
from repositories.customer_inquiry import InquiryRepo
from schemas.customer_inquiry import CustomerInquiryCreate, CustomerInquiryUpdate
from schemas.constants import InquiryStatus


UPLOAD_DIR = Path("uploads/customer_inquiries")


class InquiryService:
    """
    Service layer for customer inquiries.
    Handles creation, status updates, quoting, rejection, conversion to projects,
    and photo uploads.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = InquiryRepo(db)

    # -------------------------------------------------------------------------
    # Core CRUD
    # -------------------------------------------------------------------------

    async def create_inquiry(
        self,
        request: CustomerInquiryCreate,
        photos: list[UploadFile] | None = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> CustomerInquiry:
        """Create a new inquiry with optional photos."""
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        # Create inquiry
        inquiry_data = request.model_dump()
        inquiry = CustomerInquiry(
            **inquiry_data,
            ip_address=ip_address,
            user_agent=user_agent,
            status=InquiryStatus.NEW
        )
        self.db.add(inquiry)
        await self.db.flush()

        # Handle photos
        if photos:
            for photo in photos:
                if not photo.filename:
                    continue
                photo_obj = await self._save_photo(inquiry.id, photo, "initial")
                inquiry.photos.append(photo_obj)

        # Add activity
        await self.repo.add_activity(
            inquiry.id,
            f"New inquiry created by {inquiry.customer_name}",
            "creation",
            performed_by="customer"
        )

        await self.db.flush()
        await self.db.refresh(inquiry)
        return inquiry

    async def _save_photo(self, inquiry_id: UUID, photo: UploadFile, stage: str) -> CustomerInquiryPhoto:
        """Save a photo and return the photo object."""
        ext = Path(photo.filename).suffix.lower()
        if ext not in {'.jpg', '.jpeg', '.png', '.webp', '.gif'}:
            raise ValueError(f"Unsupported file type: {ext}")
        
        filename = f"{uuid4()}{ext}"
        
        # Create folder structure: uploads/customer_inquiries/{inquiry_id}/
        inquiry_folder = UPLOAD_DIR / str(inquiry_id)
        inquiry_folder.mkdir(parents=True, exist_ok=True)
        
        file_path = inquiry_folder / filename
        
        content = await photo.read()
        with open(file_path, "wb") as f:
            f.write(content)

        photo_obj = CustomerInquiryPhoto(
            inquiry_id=inquiry_id,
            file_path=str(file_path.relative_to(UPLOAD_DIR)),
            file_name=photo.filename,
            file_size=len(content),
            mime_type=photo.content_type,
            stage=stage
        )
        self.db.add(photo_obj)
        await self.db.flush()
        return photo_obj

    async def list_inquiries(
        self,
        status: Optional[str] = None,
        search: Optional[str] = None,
        brand: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[CustomerInquiry]:
        """List all inquiries with optional filters."""
        return await self.repo.list_all(status=status, search=search, brand=brand, limit=limit, offset=offset)

    async def get_inquiry(self, inquiry_id: UUID) -> CustomerInquiry | None:
        """Retrieve a single inquiry with all related data."""
        return await self.repo.get_with_details(inquiry_id)

    async def get_inquiry_basic(self, inquiry_id: UUID) -> CustomerInquiry | None:
        """Retrieve a single inquiry without eager loading."""
        return await self.repo.get(inquiry_id)

    # -------------------------------------------------------------------------
    # Status Management
    # -------------------------------------------------------------------------

    async def update_status(self, inquiry_id: UUID, status: str, note: Optional[str] = None) -> bool:
        """Update the status of an inquiry."""
        valid_statuses = [e.value for e in InquiryStatus]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")
        
        success = await self.repo.update_status(inquiry_id, status, note)
        if success:
            await self.repo.add_activity(
                inquiry_id,
                f"Status updated to {status}" + (f" - {note}" if note else ""),
                "status_change",
                performed_by="system"
            )
        return success

    async def reject_inquiry(self, inquiry_id: UUID, reason: str) -> bool:
        """Reject an inquiry with a reason."""
        success = await self.repo.update_status(inquiry_id, InquiryStatus.REJECTED, reason)
        if success:
            await self.repo.add_activity(
                inquiry_id,
                f"Inquiry rejected: {reason}",
                "rejection",
                performed_by="system"
            )
            await self.repo.add_workshop_note(
                inquiry_id,
                f"Rejected: {reason}",
                "rejection",
                author="system"
            )
        return success

    async def send_quote(self, inquiry_id: UUID, estimated_cost: float, notes: Optional[str] = None) -> bool:
        """Send a quotation to the customer."""
        inquiry = await self.repo.get(inquiry_id)
        if not inquiry:
            return False
        
        inquiry.status = InquiryStatus.QUOTED
        inquiry.quoted_at = datetime.now()
        if notes:
            inquiry.note = notes
        
        await self.db.flush()
        
        await self.repo.add_activity(
            inquiry_id,
            f"Quotation sent: Rp {estimated_cost:,.2f}" + (f" - {notes}" if notes else ""),
            "quotation",
            performed_by="sales_team"
        )
        return True

    async def update_notes(self, inquiry_id: UUID, note: str) -> bool:
        """Update the internal notes of an inquiry."""
        inquiry = await self.repo.get(inquiry_id)
        if not inquiry:
            return False
        inquiry.note = note
        await self.db.flush()
        
        await self.repo.add_activity(
            inquiry_id,
            "Notes updated",
            "update",
            performed_by="system"
        )
        return True

    # -------------------------------------------------------------------------
    # Workshop Notes
    # -------------------------------------------------------------------------

    async def add_workshop_note(
        self,
        inquiry_id: UUID,
        note: str,
        note_type: str = "internal",
        author: Optional[str] = None,
        is_private: bool = False
    ) -> WorkshopNote:
        """Add a workshop note to an inquiry."""
        return await self.repo.add_workshop_note(
            inquiry_id, note, note_type, author, is_private
        )

    async def get_workshop_notes(self, inquiry_id: UUID) -> list[WorkshopNote]:
        """Get all workshop notes for an inquiry."""
        inquiry = await self.repo.get_with_details(inquiry_id)
        return inquiry.workshop_notes if inquiry else []

    # -------------------------------------------------------------------------
    # Photos
    # -------------------------------------------------------------------------

    async def upload_photos(
        self,
        inquiry_id: UUID,
        photos: list[UploadFile],
        stage: str = "initial"
    ) -> list[CustomerInquiryPhoto]:
        """Upload multiple photos for an inquiry."""
        inquiry = await self.repo.get(inquiry_id)
        if not inquiry:
            raise ValueError("Inquiry not found")

        uploaded_photos = []
        for photo in photos:
            photo_obj = await self._save_photo(inquiry_id, photo, stage)
            uploaded_photos.append(photo_obj)

        await self.repo.add_activity(
            inquiry_id,
            f"Uploaded {len(uploaded_photos)} photos",
            "photo_upload",
            performed_by="system"
        )
        
        await self.db.flush()
        return uploaded_photos

    async def get_photos(self, inquiry_id: UUID) -> list[CustomerInquiryPhoto]:
        """Get all photos for an inquiry."""
        return await self.repo.get_photos(inquiry_id)

    async def delete_photo(self, photo_id: UUID) -> bool:
        """Delete a photo."""
        return await self.repo.delete_photo(photo_id)

    # -------------------------------------------------------------------------
    # Activities
    # -------------------------------------------------------------------------

    async def get_activities(self, inquiry_id: UUID) -> list[InquiryActivity]:
        """Get all activities for an inquiry."""
        return await self.repo.get_activities(inquiry_id)

    # -------------------------------------------------------------------------
    # Conversion to Project
    # -------------------------------------------------------------------------

    async def convert_to_project(self, inquiry_id: UUID) -> CustomerInquiry | None:
        """Convert an inquiry to a project."""
        inquiry = await self.repo.get_with_details(inquiry_id)
        if not inquiry:
            return None
        
        inquiry.status = InquiryStatus.CONVERTED
        inquiry.converted_at = datetime.now()
        
        await self.db.flush()
        
        await self.repo.add_activity(
            inquiry_id,
            "Converted to project",
            "conversion",
            performed_by="admin"
        )
        
        return inquiry

    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    async def get_statistics(self) -> dict:
        """Get inquiry statistics for dashboard."""
        return await self.repo.get_statistics()

    # -------------------------------------------------------------------------
    # Bulk Operations
    # -------------------------------------------------------------------------

    async def bulk_update_status(self, inquiry_ids: List[UUID], status: str) -> dict:
        """Bulk update status for multiple inquiries."""
        valid_statuses = [e.value for e in InquiryStatus]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}")
        
        success_count = 0
        failed_ids = []
        
        for inquiry_id in inquiry_ids:
            try:
                success = await self.update_status(inquiry_id, status)
                if success:
                    success_count += 1
                else:
                    failed_ids.append(str(inquiry_id))
            except Exception:
                failed_ids.append(str(inquiry_id))
        
        return {
            "success_count": success_count,
            "failed_count": len(failed_ids),
            "failed_ids": failed_ids
        }