# modules/inquiry/service.py
import os
from pathlib import Path
from uuid import uuid4, UUID
from datetime import datetime, timedelta
from typing import Optional, List
from decimal import Decimal

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import NotFoundError, ValidationError, BusinessError
from core.constants import InquiryStatus, ProjectPriority, ProjectStatus
from .models import (
    CustomerInquiry,
    CustomerInquiryPhoto,
    InquiryFollowUp,
    WorkshopNote,
    InquiryActivity
)
from .repository import InquiryRepository
from .schemas import (
    CustomerInquiryCreate,
    CustomerInquiryUpdate,
    InquiryConvertToProject,
    InquiryFollowUpCreate,
    InquiryFollowUpUpdate,
    InquiryFollowUpComplete,
)

# Gunakan absolute path untuk upload
UPLOAD_DIR = Path("uploads/customer_inquiries")
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'}


class InquiryService:
    """Service untuk Customer Inquiry."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = InquiryRepository(db)

    # ==================== Core CRUD ====================

    async def create_inquiry(
        self,
        request: CustomerInquiryCreate,
        photos: Optional[List[UploadFile]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> CustomerInquiry:
        """Create a new inquiry."""
        # 1. Buat inquiry
        inquiry_data = request.model_dump()
        inquiry = CustomerInquiry(
            **inquiry_data,
            ip_address=ip_address,
            user_agent=user_agent,
            status=InquiryStatus.NEW
        )

        self.db.add(inquiry)
        await self.db.flush()
        await self.db.refresh(inquiry)

        # 2. Handle photos
        if photos:
            for idx, photo in enumerate(photos):
                if photo.filename:
                    photo_obj = await self._save_photo(
                        inquiry.id, photo, "initial", is_primary=(idx == 0)
                    )

        # 3. Add activity
        await self.repo.add_activity(
            inquiry.id,
            f"New inquiry created by {inquiry.customer_name}",
            "creation",
            performed_by="customer"
        )

        await self.db.flush()
        await self.db.refresh(inquiry)
        return inquiry

    async def get_inquiry(self, inquiry_id: UUID) -> Optional[CustomerInquiry]:
        """Get inquiry with details."""
        return await self.repo.get_with_details(inquiry_id)

    async def list_inquiries(
        self,
        status: Optional[str] = None,
        search: Optional[str] = None,
        brand: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[CustomerInquiry], int]:
        """List inquiries with filters."""
        return await self.repo.list_all(status, search, brand, limit, offset)

    async def update_inquiry(
        self,
        inquiry_id: UUID,
        data: CustomerInquiryUpdate
    ) -> Optional[CustomerInquiry]:
        """Update inquiry."""
        inquiry = await self.repo.get(inquiry_id)
        if not inquiry:
            raise NotFoundError(f"Inquiry {inquiry_id} not found")

        update_data = data.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            if hasattr(inquiry, key) and value is not None:
                setattr(inquiry, key, value)

        await self.db.flush()
        await self.db.refresh(inquiry)

        await self.repo.add_activity(
            inquiry_id,
            "Inquiry updated",
            "update",
            performed_by="system"
        )

        return inquiry

    async def delete_inquiry(self, inquiry_id: UUID) -> bool:
        """Delete an inquiry."""
        return await self.repo.delete_inquiry(inquiry_id)

    # ==================== Status Management ====================

    async def update_status(
        self,
        inquiry_id: UUID,
        status: str,
        note: Optional[str] = None
    ) -> bool:
        """Update inquiry status."""
        valid_statuses = [e.value for e in InquiryStatus]
        if status not in valid_statuses:
            raise ValidationError(f"Invalid status: {status}")

        return await self.repo.update_status(inquiry_id, status, note)

    async def contact_customer(
        self,
        inquiry_id: UUID,
        note: Optional[str] = None
    ) -> bool:
        """Mark inquiry as contacted."""
        return await self.update_status(inquiry_id, InquiryStatus.CONTACTED, note)

    async def send_quote(
        self,
        inquiry_id: UUID,
        estimated_cost: Decimal,
        notes: Optional[str] = None
    ) -> bool:
        """Send quotation to customer."""
        inquiry = await self.repo.get(inquiry_id)
        if not inquiry:
            raise NotFoundError(f"Inquiry {inquiry_id} not found")

        inquiry.status = InquiryStatus.QUOTED
        inquiry.quoted_at = datetime.now()
        if notes:
            inquiry.note = notes

        await self.db.flush()

        await self.repo.add_activity(
            inquiry_id,
            f"Quotation sent: Rp {estimated_cost:,.2f}" +
            (f" - {notes}" if notes else ""),
            "quotation",
            performed_by="system"
        )
        return True

    async def reject_inquiry(self, inquiry_id: UUID, reason: str) -> bool:
        """Reject inquiry with reason."""
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

    async def close_inquiry(
        self,
        inquiry_id: UUID,
        reason: str,
        note: Optional[str] = None
    ) -> bool:
        """Close an inquiry."""
        inquiry = await self.repo.get(inquiry_id)
        if not inquiry:
            raise NotFoundError(f"Inquiry {inquiry_id} not found")

        inquiry.status = InquiryStatus.CLOSED
        inquiry.closed_at = datetime.now()
        inquiry.closed_reason = reason
        if note:
            inquiry.note = note

        await self.db.flush()

        await self.repo.add_activity(
            inquiry_id,
            f"Inquiry closed: {reason}" + (f" - {note}" if note else ""),
            "closure",
            performed_by="system"
        )
        return True

    # ==================== Conversion ====================

    async def convert_to_project(
        self,
        inquiry_id: UUID,
        data: InquiryConvertToProject
    ) -> any:  # Project
        """Convert inquiry to project."""
        # Import di sini untuk menghindari circular import
        from modules.projects.models import Project
        from modules.projects.schemas import ProjectCreate
        from modules.projects.services import ProjectService

        inquiry = await self.repo.get_with_details(inquiry_id)
        if not inquiry:
            raise NotFoundError(f"Inquiry {inquiry_id} not found")

        if inquiry.status == InquiryStatus.CONVERTED:
            raise BusinessError("Inquiry already converted to project")

        if inquiry.status in [InquiryStatus.REJECTED, InquiryStatus.CLOSED]:
            raise BusinessError(
                f"Cannot convert inquiry with status: {inquiry.status}")

        project_name = data.project_name or f"Project: {inquiry.vehicle_brand} {inquiry.vehicle_model} - {inquiry.customer_name}"

        project_data = {
            "name": project_name,
            "customer_name": inquiry.customer_name,
            "customer_phone": inquiry.customer_phone_number,
            "customer_email": inquiry.customer_email,
            "vehicle_brand": inquiry.vehicle_brand,
            "vehicle_model": inquiry.vehicle_model,
            "vehicle_year": inquiry.vehicle_year,
            "vehicle_license_plate": inquiry.vehicle_license_plate,
            "estimated_cost": data.estimated_cost or Decimal(inquiry.estimated_budget or 0),
            "project_start_date": data.project_start_date or datetime.now(),
            "project_target_delivery": data.project_target_delivery,
            "status": ProjectStatus.ACTIVE,
            "priority": ProjectPriority.MEDIUM,
            "notes": inquiry.project_description,
            "inquiry_id": inquiry_id,
        }

        project_service = ProjectService(self.db)
        project_create = ProjectCreate(**project_data)
        project = await project_service.create(project_create)

        inquiry.status = InquiryStatus.CONVERTED
        inquiry.converted_at = datetime.now()
        inquiry.conversion_rate = Decimal(100)

        await self.repo.add_activity(
            inquiry_id,
            f"Converted to project: {project.name}",
            "conversion",
            performed_by="system"
        )

        await self.db.flush()
        await self.db.refresh(inquiry)

        return project

    # ==================== Photos ====================

    async def _save_photo(
        self,
        inquiry_id: UUID,
        photo: UploadFile,
        stage: str,
        is_primary: bool = False
    ) -> CustomerInquiryPhoto:
        """Save photo and return photo object."""
        ext = Path(photo.filename).suffix.lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise ValidationError(
                f"Unsupported file type: {ext}. Allowed: {ALLOWED_IMAGE_EXTENSIONS}")

        filename = f"{uuid4()}{ext}"
        inquiry_folder = UPLOAD_DIR / str(inquiry_id)
        inquiry_folder.mkdir(parents=True, exist_ok=True)

        file_path = inquiry_folder / filename
        content = await photo.read()

        # Simpan file
        with open(file_path, "wb") as f:
            f.write(content)

        # Simpan relatif path
        relative_path = str(file_path.relative_to(Path.cwd()))

        photo_obj = CustomerInquiryPhoto(
            inquiry_id=inquiry_id,
            file_path=relative_path,
            file_name=photo.filename,
            file_size=len(content),
            mime_type=photo.content_type,
            stage=stage,
            is_primary=is_primary
        )
        self.db.add(photo_obj)
        await self.db.flush()
        return photo_obj

    async def upload_photos(
        self,
        inquiry_id: UUID,
        photos: List[UploadFile],
        stage: str = "initial"
    ) -> List[CustomerInquiryPhoto]:
        """Upload multiple photos."""
        inquiry = await self.repo.get(inquiry_id)
        if not inquiry:
            raise NotFoundError(f"Inquiry {inquiry_id} not found")

        uploaded = []
        current_photos = await self.repo.get_photos(inquiry_id)
        is_first = len(current_photos) == 0

        for idx, photo in enumerate(photos):
            photo_obj = await self._save_photo(
                inquiry_id, photo, stage, is_primary=(is_first and idx == 0)
            )
            uploaded.append(photo_obj)

        await self.repo.add_activity(
            inquiry_id,
            f"Uploaded {len(uploaded)} photos",
            "photo_upload",
            performed_by="system"
        )

        return uploaded

    async def get_photos(self, inquiry_id: UUID) -> List[CustomerInquiryPhoto]:
        """Get all photos for an inquiry."""
        return await self.repo.get_photos(inquiry_id)

    async def set_primary_photo(self, photo_id: UUID) -> bool:
        """Set a photo as primary."""
        return await self.repo.set_primary_photo(photo_id)

    async def delete_photo(self, photo_id: UUID) -> bool:
        """Delete a photo."""
        return await self.repo.delete_photo(photo_id)

    # ==================== Workshop Notes ====================

    async def add_workshop_note(
        self,
        inquiry_id: UUID,
        note: str,
        note_type: str = "internal",
        author: Optional[str] = None,
        is_private: bool = False
    ) -> WorkshopNote:
        """Add workshop note."""
        return await self.repo.add_workshop_note(
            inquiry_id, note, note_type, author, is_private
        )

    async def get_workshop_notes(
        self,
        inquiry_id: UUID,
        include_private: bool = False
    ) -> List[WorkshopNote]:
        """Get workshop notes."""
        return await self.repo.get_workshop_notes(inquiry_id, include_private)

    # ==================== Activities ====================

    async def get_activities(
        self,
        inquiry_id: UUID,
        limit: int = 50
    ) -> List[InquiryActivity]:
        """Get inquiry activities."""
        return await self.repo.get_activities(inquiry_id, limit)

    # ==================== Statistics ====================

    async def get_statistics(self) -> dict:
        """Get inquiry statistics."""
        return await self.repo.get_statistics()

    async def get_pending_conversion(self) -> List[CustomerInquiry]:
        """Get inquiries ready for conversion."""
        return await self.repo.get_pending_conversion()

    # ==================== Follow-Ups ====================

    async def add_follow_up(
        self,
        inquiry_id: UUID,
        data: InquiryFollowUpCreate
    ) -> InquiryFollowUp:
        """Add follow-up to inquiry."""
        inquiry = await self.repo.get(inquiry_id)
        if not inquiry:
            raise NotFoundError(f"Inquiry {inquiry_id} not found")

        if data.scheduled_at < datetime.now() - timedelta(minutes=5):
            raise ValidationError("Scheduled time cannot be in the past")

        follow_up = await self.repo.add_follow_up(inquiry_id, data.model_dump())

        await self.repo.add_activity(
            inquiry_id,
            f"Follow-up scheduled for {data.scheduled_at.strftime('%Y-%m-%d %H:%M')}",
            "follow_up_add",
            performed_by="system"
        )

        return follow_up

    async def get_follow_ups(self, inquiry_id: UUID) -> List[InquiryFollowUp]:
        """Get all follow-ups for an inquiry."""
        return await self.repo.get_follow_ups(inquiry_id)

    async def get_follow_up(self, follow_up_id: UUID) -> Optional[InquiryFollowUp]:
        """Get follow-up by ID."""
        return await self.repo.get_follow_up(follow_up_id)

    async def update_follow_up(
        self,
        follow_up_id: UUID,
        data: InquiryFollowUpUpdate
    ) -> Optional[InquiryFollowUp]:
        """Update follow-up."""
        return await self.repo.update_follow_up(follow_up_id, data.model_dump(exclude_unset=True))

    async def complete_follow_up(
        self,
        follow_up_id: UUID,
        data: InquiryFollowUpComplete
    ) -> Optional[InquiryFollowUp]:
        """Complete follow-up."""
        follow_up = await self.repo.complete_follow_up(follow_up_id, data.result, data.note)
        if follow_up:
            await self.repo.add_activity(
                follow_up.inquiry_id,
                f"Follow-up completed: {data.result}",
                "follow_up_complete",
                performed_by="system"
            )
        return follow_up

    async def delete_follow_up(self, follow_up_id: UUID) -> bool:
        """Delete follow-up."""
        follow_up = await self.repo.get_follow_up(follow_up_id)
        if follow_up:
            await self.repo.add_activity(
                follow_up.inquiry_id,
                "Follow-up deleted",
                "follow_up_delete",
                performed_by="system"
            )
        return await self.repo.delete_follow_up(follow_up_id)

    async def process_pending_follow_ups(self) -> List[InquiryFollowUp]:
        """Process pending follow-ups (mark as overdue if missed)."""
        pending = await self.repo.get_pending_follow_ups()
        now = datetime.now()
        processed = []

        for follow_up in pending:
            if follow_up.scheduled_at < now - timedelta(hours=1):
                await self.repo.update_follow_up(follow_up.id, {"status": "missed"})
                await self.repo.add_activity(
                    follow_up.inquiry_id,
                    f"Follow-up missed: scheduled for {follow_up.scheduled_at.strftime('%Y-%m-%d %H:%M')}",
                    "follow_up_missed",
                    performed_by="system"
                )
                processed.append(follow_up)

        return processed

    async def send_follow_up_reminders(self) -> List[InquiryFollowUp]:
        """Send reminders for upcoming follow-ups."""
        upcoming = await self.repo.get_upcoming_follow_ups(24)
        sent = []

        for follow_up in upcoming:
            await self.repo.update_follow_up(follow_up.id, {
                "reminder_sent": True,
                "reminder_sent_at": datetime.now()
            })
            sent.append(follow_up)

        return sent

    async def get_follow_ups_by_assignee(self, assigned_to: str) -> List[InquiryFollowUp]:
        """Get follow-ups assigned to a specific person."""
        return await self.repo.get_follow_ups_by_assignee(assigned_to)

    async def check_and_update_inquiry_status(self, inquiry_id: UUID) -> bool:
        """Check if inquiry should be updated based on project status."""
        inquiry = await self.repo.get_with_details(inquiry_id)
        if not inquiry or not inquiry.project:
            return False

        project = inquiry.project
        if project.status == ProjectStatus.COMPLETED:
            if inquiry.status != InquiryStatus.COMPLETED:
                inquiry.status = InquiryStatus.COMPLETED
                await self.db.flush()
                await self.repo.add_activity(
                    inquiry_id,
                    "Auto-updated: Project completed",
                    "auto_update",
                    performed_by="system"
                )
                return True
        return False
