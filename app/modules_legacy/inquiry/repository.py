# modules/inquiry/repository.py
from uuid import UUID
from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, or_, and_, desc, func, update, exists
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.base import BaseRepository
from core.constants import InquiryStatus
from .models import (
    CustomerInquiry,
    CustomerInquiryPhoto,
    InquiryActivity,
    InquiryFollowUp,
    WorkshopNote,
)


class InquiryRepository(BaseRepository[CustomerInquiry]):
    """Repository untuk Customer Inquiry dengan complete CRUD operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=CustomerInquiry)

    # ============================================================
    # 1. READ OPERATIONS
    # ============================================================

    async def get_with_details(self, inquiry_id: UUID) -> Optional[CustomerInquiry]:
        """
        Get inquiry with all related data, optimized with eager loading.
        """
        stmt = (
            select(CustomerInquiry).where(
                CustomerInquiry.id == inquiry_id,
                CustomerInquiry.is_deleted == False  # Soft delete filter
            ).options(
                selectinload(CustomerInquiry.photos),
                selectinload(CustomerInquiry.activities),
                selectinload(CustomerInquiry.workshop_notes),
                selectinload(CustomerInquiry.project),
                selectinload(CustomerInquiry.payments),
                selectinload(CustomerInquiry.invoices),
                selectinload(CustomerInquiry.follow_ups),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone_number: str, include_deleted: bool = False) -> List[CustomerInquiry]:
        """
        Get inquiries by phone number.

        Args:
            phone_number: Nomor telepon customer
            include_deleted: Include soft-deleted records
        """
        stmt = (select(CustomerInquiry).where(CustomerInquiry.customer_phone_number == phone_number)
                .order_by(desc(CustomerInquiry.created_at)))
        if not include_deleted:
            stmt = stmt.where(CustomerInquiry.is_deleted == False)

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_email(self, email: str, include_deleted: bool = False) -> List[CustomerInquiry]:
        """
        Get inquiries by email.

        Args:
            email: Email customer
            include_deleted: Include soft-deleted records
        """
        stmt = (select(CustomerInquiry).where(CustomerInquiry.customer_email ==
                email).order_by(desc(CustomerInquiry.created_at)))
        if not include_deleted:
            stmt = stmt.where(CustomerInquiry.is_deleted == False)

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_project_id(self, project_id: UUID) -> Optional[CustomerInquiry]:
        """
        Get inquiry by project ID.

        Args:
            project_id: ID project yang terkonversi
        """
        stmt = (
            select(CustomerInquiry)
            .where(
                CustomerInquiry.project_id == project_id,
                CustomerInquiry.is_deleted == False
            )
            .options(
                selectinload(CustomerInquiry.project),
                selectinload(CustomerInquiry.photos),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_plate_number(self, plate_number: str) -> Optional[CustomerInquiry]:
        """
        Get inquiry by vehicle license plate.

        Args:
            plate_number: Plat nomor kendaraan
        """
        stmt = (
            select(CustomerInquiry)
            .where(
                CustomerInquiry.vehicle_license_plate == plate_number,
                CustomerInquiry.is_deleted == False
            )
            .order_by(desc(CustomerInquiry.created_at))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_pending_conversion(self) -> List[CustomerInquiry]:
        """
        Get inquiries that are ready for conversion to project.
        Hanya inquiry dengan status tertentu dan belum punya project.
        """
        stmt = (
            select(CustomerInquiry)
            .where(
                CustomerInquiry.status.in_([
                    InquiryStatus.QUOTED,
                    InquiryStatus.CONTACTED,
                    InquiryStatus.APPROVED,
                ]),
                CustomerInquiry.project_id.is_(None),
                CustomerInquiry.is_deleted == False,
            )
            .order_by(CustomerInquiry.created_at)
            .options(
                selectinload(CustomerInquiry.photos),
                selectinload(CustomerInquiry.activities),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    # Tambahkan di repository.py:
    async def process_pending_follow_ups(self) -> List[InquiryFollowUp]:
        """Process pending follow-ups (mark as overdue if missed)."""
        pending = await self.get_pending_follow_ups()
        processed = []
        now = datetime.now()
        
        for follow_up in pending:
            if follow_up.scheduled_at < now - timedelta(hours=1):
                await self.update_follow_up(follow_up.id, {"status": "missed"})
                processed.append(follow_up)
        
        return processed

    async def get_recent(self, limit: int = 10, include_deleted: bool = False) -> List[CustomerInquiry]:
        """
        Get recent inquiries.

        Args:
            limit: Jumlah maksimal
            include_deleted: Include soft-deleted records
        """
        stmt = (
            select(CustomerInquiry)
            .order_by(desc(CustomerInquiry.created_at))
            .limit(limit)
            .options(
                selectinload(CustomerInquiry.project),
                selectinload(CustomerInquiry.photos).limit(1),  # Hanya 1 foto
                selectinload(CustomerInquiry.activities).limit(
                    3),  # 3 aktivitas terakhir
            )
        )
        if not include_deleted:
            stmt = stmt.where(CustomerInquiry.is_deleted == False)

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_status(self, status: str, limit: int = 100) -> List[CustomerInquiry]:
        """
        Get inquiries by status.

        Args:
            status: Status inquiry
            limit: Jumlah maksimal
        """
        stmt = (
            select(CustomerInquiry)
            .where(
                CustomerInquiry.status == status,
                CustomerInquiry.is_deleted == False
            )
            .order_by(desc(CustomerInquiry.created_at))
            .limit(limit)
            .options(
                selectinload(CustomerInquiry.project),
                selectinload(CustomerInquiry.photos).limit(1),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        status: Optional[str] = None
    ) -> List[CustomerInquiry]:
        """
        Get inquiries by date range.

        Args:
            start_date: Tanggal mulai
            end_date: Tanggal akhir
            status: Filter status (optional)
        """
        stmt = (
            select(CustomerInquiry)
            .where(
                CustomerInquiry.created_at >= start_date,
                CustomerInquiry.created_at <= end_date,
                CustomerInquiry.is_deleted == False
            )
            .order_by(desc(CustomerInquiry.created_at))
        )
        if status:
            stmt = stmt.where(CustomerInquiry.status == status)

        result = await self.db.execute(stmt)
        return result.scalars().all()

    # ============================================================
    # 2. LIST WITH FILTERS (OPTIMIZED)
    # ============================================================

    async def list_all(
        self,
        status: Optional[str] = None,
        search: Optional[str] = None,
        brand: Optional[str] = None,
        project_status: Optional[str] = None,
        has_project: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
        include_deleted: bool = False
    ) -> tuple[List[CustomerInquiry], int]:
        """
        List all inquiries with filters.
        Optimized with proper eager loading and indexes.

        Args:
            status: Filter by inquiry status
            search: Search by name, phone, brand, model, plate
            brand: Filter by vehicle brand
            project_status: Filter by project status
            has_project: Filter by project existence (true/false)
            limit: Items per page
            offset: Pagination offset
            include_deleted: Include soft-deleted records

        Returns:
            Tuple of (inquiries, total_count)
        """
        from modules.projects.models import Project

        # Base query dengan eager loading
        stmt = select(CustomerInquiry).options(
            selectinload(CustomerInquiry.project),
            selectinload(CustomerInquiry.photos).limit(1),  # Hanya 1 foto
            selectinload(CustomerInquiry.activities).limit(
                5),  # 5 aktivitas terakhir
        )

        # Count query
        count_stmt = select(func.count()).select_from(CustomerInquiry)

        # Build filters
        filters = []

        # Soft delete filter
        if not include_deleted:
            filters.append(CustomerInquiry.is_deleted == False)

        # Status filter
        if status:
            filters.append(CustomerInquiry.status == status)

        # Brand filter
        if brand:
            filters.append(CustomerInquiry.vehicle_brand == brand)

        # Search filter (multiple columns)
        if search:
            search_filter = or_(
                CustomerInquiry.customer_name.ilike(f"%{search}%"),
                CustomerInquiry.customer_phone_number.ilike(f"%{search}%"),
                CustomerInquiry.customer_email.ilike(f"%{search}%"),
                CustomerInquiry.vehicle_brand.ilike(f"%{search}%"),
                CustomerInquiry.vehicle_model.ilike(f"%{search}%"),
                CustomerInquiry.vehicle_license_plate.ilike(f"%{search}%"),
            )
            filters.append(search_filter)

        # Has project filter
        if has_project is not None:
            if has_project:
                filters.append(CustomerInquiry.project_id.isnot(None))
            else:
                filters.append(CustomerInquiry.project_id.is_(None))

        # Project status filter (using EXISTS for better performance)
        if project_status:
            filters.append(
                exists().where(
                    and_(
                        Project.id == CustomerInquiry.project_id,
                        Project.status == project_status,
                        Project.is_deleted == False,
                    )
                )
            )

        # Apply filters
        if filters:
            stmt = stmt.where(and_(*filters))
            count_stmt = count_stmt.where(and_(*filters))

        # Apply pagination
        stmt = stmt.order_by(desc(CustomerInquiry.created_at)
                             ).offset(offset).limit(limit)

        # Execute queries
        result = await self.db.execute(stmt)
        inquiries = result.scalars().all()

        total = await self.db.scalar(count_stmt) or 0

        return inquiries, total

    # ============================================================
    # 3. CREATE OPERATIONS
    # ============================================================

    async def create_inquiry(
        self,
        data: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> CustomerInquiry:
        """
        Create new inquiry with metadata.

        Args:
            data: Inquiry data dictionary
            ip_address: Customer IP address
            user_agent: Customer browser user agent

        Returns:
            Created inquiry instance
        """
        inquiry = CustomerInquiry(
            **data,
            ip_address=ip_address,
            user_agent=user_agent,
            status=InquiryStatus.NEW
        )

        self.db.add(inquiry)
        await self.db.flush()
        await self.db.refresh(inquiry)

        # Add initial activity
        await self.add_activity(
            inquiry.id,
            f"New inquiry created by {inquiry.customer_name}",
            "creation",
            performed_by="customer",
            meta_data={"source": data.get('source', 'website')}
        )

        return inquiry

    async def add_photo(
        self,
        inquiry_id: UUID,
        photo_data: dict,
        is_primary: bool = False
    ) -> CustomerInquiryPhoto:
        """
        Add photo to inquiry.

        Args:
            inquiry_id: ID inquiry
            photo_data: Photo data dictionary
            is_primary: Set as primary photo

        Returns:
            Created photo instance
        """
        # Check if this should be primary
        if is_primary:
            # Reset all photos for this inquiry
            await self.db.execute(
                update(CustomerInquiryPhoto)
                .where(CustomerInquiryPhoto.inquiry_id == inquiry_id)
                .values(is_primary=False)
            )

        photo = CustomerInquiryPhoto(
            inquiry_id=inquiry_id,
            is_primary=is_primary,
            **photo_data
        )
        self.db.add(photo)
        await self.db.flush()
        await self.db.refresh(photo)
        return photo

    async def add_activity(
        self,
        inquiry_id: UUID,
        activity_text: str,
        activity_type: Optional[str] = None,
        performed_by: Optional[str] = None,
        meta_data: Optional[dict] = None
    ) -> InquiryActivity:
        """
        Add activity to inquiry for audit trail.

        Args:
            inquiry_id: ID inquiry
            activity_text: Deskripsi aktivitas
            activity_type: Tipe aktivitas
            performed_by: Yang melakukan
            meta_data: Metadata tambahan

        Returns:
            Created activity instance
        """
        activity = InquiryActivity(
            inquiry_id=inquiry_id,
            activity=activity_text,
            activity_type=activity_type,
            performed_by=performed_by or "system",
            meta_data=meta_data
        )
        self.db.add(activity)
        await self.db.flush()
        await self.db.refresh(activity)
        return activity

    async def add_workshop_note(
        self,
        inquiry_id: UUID,
        note: str,
        note_type: str = "internal",
        author: Optional[str] = None,
        is_private: bool = False
    ) -> WorkshopNote:
        """
        Add workshop note to inquiry.

        Args:
            inquiry_id: ID inquiry
            note: Isi catatan
            note_type: Tipe catatan
            author: Penulis
            is_private: Catatan privat

        Returns:
            Created workshop note instance
        """
        workshop_note = WorkshopNote(
            inquiry_id=inquiry_id,
            note=note,
            note_type=note_type,
            author=author or "system",
            is_private=is_private
        )
        self.db.add(workshop_note)
        await self.db.flush()
        await self.db.refresh(workshop_note)
        return workshop_note

    async def add_follow_up(
        self,
        inquiry_id: UUID,
        data: Dict[str, Any]
    ) -> InquiryFollowUp:
        """
        Add follow-up to inquiry.

        Args:
            inquiry_id: ID inquiry
            data: Follow-up data dictionary

        Returns:
            Created follow-up instance
        """
        follow_up = InquiryFollowUp(
            inquiry_id=inquiry_id,
            **data
        )
        self.db.add(follow_up)
        await self.db.flush()
        await self.db.refresh(follow_up)

        # Log activity
        await self.add_activity(
            inquiry_id,
            f"Follow-up scheduled for {follow_up.scheduled_at.strftime('%Y-%m-%d %H:%M')}",
            "follow_up_add",
            performed_by="system"
        )

        return follow_up

    # ============================================================
    # 4. UPDATE OPERATIONS
    # ============================================================

    async def update_inquiry(
        self,
        inquiry_id: UUID,
        data: Dict[str, Any]
    ) -> Optional[CustomerInquiry]:
        """
        Update inquiry with data.

        Args:
            inquiry_id: ID inquiry
            data: Data to update

        Returns:
            Updated inquiry or None if not found
        """
        inquiry = await self.get(inquiry_id)
        if not inquiry or inquiry.is_deleted:
            return None

        # Update only fields that exist
        for key, value in data.items():
            if hasattr(inquiry, key) and value is not None:
                setattr(inquiry, key, value)

        inquiry.updated_at = datetime.now()
        await self.db.flush()
        await self.db.refresh(inquiry)

        # Log activity
        await self.add_activity(
            inquiry_id,
            "Inquiry updated",
            "update",
            performed_by="system",
            meta_data={"updated_fields": list(data.keys())}
        )

        return inquiry

    async def update_status(
        self,
        inquiry_id: UUID,
        new_status: str,
        note: Optional[str] = None
    ) -> bool:
        """
        Update inquiry status with validation.

        Args:
            inquiry_id: ID inquiry
            new_status: Status baru
            note: Catatan perubahan

        Returns:
            True if updated, False if not found
        """
        inquiry = await self.get(inquiry_id)
        if not inquiry or inquiry.is_deleted:
            return False

        old_status = inquiry.status

        # Use model's transition method
        try:
            inquiry.transition_to(new_status, note)
        except ValueError as e:
            # Re-raise with more context
            raise ValueError(f"Inquiry {inquiry_id}: {str(e)}")

        # Update note if provided
        if note:
            inquiry.note = note

        # Add activity for status change
        await self.add_activity(
            inquiry_id,
            f"Status changed: {old_status} → {new_status}",
            "status_change",
            performed_by="system",
            meta_data={
                "old_status": old_status,
                "new_status": new_status,
                "note": note
            }
        )

        await self.db.flush()
        await self.db.refresh(inquiry)
        return True

    async def update_conversion_rate(
        self,
        inquiry_id: UUID,
        rate: Decimal
    ) -> bool:
        """
        Update conversion rate for inquiry.

        Args:
            inquiry_id: ID inquiry
            rate: Conversion rate percentage

        Returns:
            True if updated, False if not found
        """
        inquiry = await self.get(inquiry_id)
        if not inquiry or inquiry.is_deleted:
            return False

        inquiry.conversion_rate = rate
        inquiry.estimated_conversion_date = datetime.now()
        await self.db.flush()

        await self.add_activity(
            inquiry_id,
            f"Conversion rate updated to {rate}%",
            "update",
            performed_by="system"
        )

        return True

    async def set_primary_photo(self, photo_id: UUID) -> bool:
        """
        Set a photo as primary.

        Args:
            photo_id: ID photo

        Returns:
            True if updated, False if not found
        """
        stmt = select(CustomerInquiryPhoto).where(
            CustomerInquiryPhoto.id == photo_id)
        result = await self.db.execute(stmt)
        photo = result.scalar_one_or_none()

        if not photo:
            return False

        # Reset all photos for this inquiry
        await self.db.execute(
            update(CustomerInquiryPhoto)
            .where(CustomerInquiryPhoto.inquiry_id == photo.inquiry_id)
            .values(is_primary=False)
        )

        photo.is_primary = True
        await self.db.flush()

        await self.add_activity(
            photo.inquiry_id,
            f"Primary photo set: {photo.file_name}",
            "photo_update",
            performed_by="system"
        )

        return True

    async def update_follow_up(
        self,
        follow_up_id: UUID,
        data: Dict[str, Any]
    ) -> Optional[InquiryFollowUp]:
        """
        Update follow-up.

        Args:
            follow_up_id: ID follow-up
            data: Data to update

        Returns:
            Updated follow-up or None if not found
        """
        follow_up = await self.get_follow_up(follow_up_id)
        if not follow_up:
            return None

        for key, value in data.items():
            if hasattr(follow_up, key) and value is not None:
                setattr(follow_up, key, value)

        await self.db.flush()
        await self.db.refresh(follow_up)
        return follow_up

    async def complete_follow_up(
        self,
        follow_up_id: UUID,
        result: str,
        note: Optional[str] = None
    ) -> Optional[InquiryFollowUp]:
        """
        Complete follow-up.

        Args:
            follow_up_id: ID follow-up
            result: Hasil follow-up
            note: Catatan tambahan

        Returns:
            Updated follow-up or None if not found
        """
        return await self.update_follow_up(follow_up_id, {
            "status": "done",
            "performed_at": datetime.now(),
            "result": result,
            "note": note
        })

    # ============================================================
    # 5. DELETE OPERATIONS (Soft Delete)
    # ============================================================

    async def delete_inquiry(self, inquiry_id: UUID) -> bool:
        """
        Soft delete inquiry.

        Args:
            inquiry_id: ID inquiry

        Returns:
            True if deleted, False if not found
        """
        inquiry = await self.get(inquiry_id)
        if not inquiry:
            return False

        # Soft delete
        inquiry.is_deleted = True
        inquiry.deleted_at = datetime.now()

        await self.db.flush()

        # Log activity
        await self.add_activity(
            inquiry_id,
            "Inquiry soft deleted",
            "deletion",
            performed_by="system"
        )

        return True

    async def hard_delete_inquiry(self, inquiry_id: UUID) -> bool:
        """
        Hard delete inquiry (permanent).
        Warning: This cannot be undone!

        Args:
            inquiry_id: ID inquiry

        Returns:
            True if deleted, False if not found
        """
        inquiry = await self.get(inquiry_id, include_deleted=True)
        if not inquiry:
            return False

        # Hapus semua related data (cascade akan handle)
        await self.db.delete(inquiry)
        await self.db.flush()
        return True

    async def delete_photo(self, photo_id: UUID) -> bool:
        """
        Delete a photo.

        Args:
            photo_id: ID photo

        Returns:
            True if deleted, False if not found
        """
        stmt = select(CustomerInquiryPhoto).where(
            CustomerInquiryPhoto.id == photo_id)
        result = await self.db.execute(stmt)
        photo = result.scalar_one_or_none()

        if not photo:
            return False

        # If this was primary, set another as primary
        if photo.is_primary:
            other_photos = await self.get_photos(photo.inquiry_id)
            if len(other_photos) > 1:
                for p in other_photos:
                    if p.id != photo_id:
                        p.is_primary = True
                        break

        await self.db.delete(photo)
        await self.db.flush()

        await self.add_activity(
            photo.inquiry_id,
            f"Photo deleted: {photo.file_name}",
            "photo_delete",
            performed_by="system"
        )

        return True

    async def delete_follow_up(self, follow_up_id: UUID) -> bool:
        """
        Delete follow-up.

        Args:
            follow_up_id: ID follow-up

        Returns:
            True if deleted, False if not found
        """
        follow_up = await self.get_follow_up(follow_up_id)
        if not follow_up:
            return False

        await self.db.delete(follow_up)
        await self.db.flush()

        await self.add_activity(
            follow_up.inquiry_id,
            "Follow-up deleted",
            "follow_up_delete",
            performed_by="system"
        )

        return True

    # ============================================================
    # 6. GET OPERATIONS (READ)
    # ============================================================

    async def get_photos(self, inquiry_id: UUID) -> List[CustomerInquiryPhoto]:
        """
        Get all photos for an inquiry.

        Args:
            inquiry_id: ID inquiry

        Returns:
            List of photos sorted by primary and order
        """
        stmt = (
            select(CustomerInquiryPhoto)
            .where(CustomerInquiryPhoto.inquiry_id == inquiry_id)
            .order_by(
                CustomerInquiryPhoto.is_primary.desc(),
                CustomerInquiryPhoto.sort_order,
                CustomerInquiryPhoto.created_at
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_activities(
        self,
        inquiry_id: UUID,
        limit: int = 50
    ) -> List[InquiryActivity]:
        """
        Get all activities for an inquiry.

        Args:
            inquiry_id: ID inquiry
            limit: Max activities to return

        Returns:
            List of activities sorted by created_at desc
        """
        stmt = (
            select(InquiryActivity)
            .where(InquiryActivity.inquiry_id == inquiry_id)
            .order_by(desc(InquiryActivity.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_workshop_notes(
        self,
        inquiry_id: UUID,
        include_private: bool = False
    ) -> List[WorkshopNote]:
        """
        Get all workshop notes for an inquiry.

        Args:
            inquiry_id: ID inquiry
            include_private: Include private notes

        Returns:
            List of workshop notes sorted by created_at desc
        """
        stmt = select(WorkshopNote).where(
            WorkshopNote.inquiry_id == inquiry_id
        )
        if not include_private:
            stmt = stmt.where(WorkshopNote.is_private == False)

        stmt = stmt.order_by(desc(WorkshopNote.created_at))
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    # Tambahkan di repository.py:
    async def send_follow_up_reminders(self) -> List[InquiryFollowUp]:
        """Send reminders for upcoming follow-ups."""
        upcoming = await self.get_upcoming_follow_ups(24)
        sent = []
        
        for follow_up in upcoming:
            await self.update_follow_up(follow_up.id, {
                "reminder_sent": True,
                "reminder_sent_at": datetime.now()
            })
            sent.append(follow_up)
        
        return sent

    async def get_follow_ups(self, inquiry_id: UUID) -> List[InquiryFollowUp]:
        """
        Get all follow-ups for an inquiry.

        Args:
            inquiry_id: ID inquiry

        Returns:
            List of follow-ups sorted by scheduled_at
        """
        stmt = (
            select(InquiryFollowUp)
            .where(InquiryFollowUp.inquiry_id == inquiry_id)
            .order_by(InquiryFollowUp.scheduled_at)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_follow_up(self, follow_up_id: UUID) -> Optional[InquiryFollowUp]:
        """
        Get follow-up by ID.

        Args:
            follow_up_id: ID follow-up

        Returns:
            Follow-up instance or None
        """
        stmt = select(InquiryFollowUp).where(
            InquiryFollowUp.id == follow_up_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_pending_follow_ups(self) -> List[InquiryFollowUp]:
        """
        Get all pending follow-ups (overdue).

        Returns:
            List of pending follow-ups
        """
        now = datetime.now()
        stmt = (
            select(InquiryFollowUp)
            .where(
                InquiryFollowUp.status == "pending",
                InquiryFollowUp.scheduled_at <= now
            )
            .order_by(InquiryFollowUp.scheduled_at)
            .options(selectinload(InquiryFollowUp.inquiry))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_upcoming_follow_ups(self, hours: int = 24) -> List[InquiryFollowUp]:
        """
        Get upcoming follow-ups within next N hours.

        Args:
            hours: Hours ahead to check

        Returns:
            List of upcoming follow-ups
        """
        now = datetime.now()
        future = now + timedelta(hours=hours)
        stmt = (
            select(InquiryFollowUp)
            .where(
                InquiryFollowUp.status == "pending",
                InquiryFollowUp.scheduled_at >= now,
                InquiryFollowUp.scheduled_at <= future,
                InquiryFollowUp.reminder_sent == False
            )
            .order_by(InquiryFollowUp.scheduled_at)
            .options(selectinload(InquiryFollowUp.inquiry))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_follow_ups_by_assignee(self, assigned_to: str) -> List[InquiryFollowUp]:
        """
        Get follow-ups assigned to a specific person.

        Args:
            assigned_to: Nama assignee

        Returns:
            List of follow-ups
        """
        stmt = (
            select(InquiryFollowUp)
            .where(
                InquiryFollowUp.assigned_to == assigned_to,
                InquiryFollowUp.status == "pending"
            )
            .order_by(InquiryFollowUp.scheduled_at)
            .options(selectinload(InquiryFollowUp.inquiry))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    # ============================================================
    # 7. STATISTICS
    # ============================================================

    async def get_statistics(self) -> dict:
        """
        Get inquiry statistics for dashboard.

        Returns:
            Dictionary with statistics
        """
        # Total inquiries
        total_stmt = select(func.count()).select_from(CustomerInquiry).where(
            CustomerInquiry.is_deleted == False
        )
        total = await self.db.scalar(total_stmt) or 0

        # By status
        status_stmt = (
            select(
                CustomerInquiry.status,
                func.count().label('count')
            )
            .where(CustomerInquiry.is_deleted == False)
            .group_by(CustomerInquiry.status)
        )
        result_status = await self.db.execute(status_stmt)
        status_counts = {row.status: row.count for row in result_status.all()}

        # By brand (top 10)
        brand_stmt = (
            select(
                CustomerInquiry.vehicle_brand,
                func.count().label('count')
            )
            .where(CustomerInquiry.is_deleted == False)
            .group_by(CustomerInquiry.vehicle_brand)
            .order_by(desc('count'))
            .limit(10)
        )
        result_brand = await self.db.execute(brand_stmt)
        brand_counts = {
            row.vehicle_brand: row.count for row in result_brand.all()}

        # By source
        source_stmt = (
            select(
                CustomerInquiry.source,
                func.count().label('count')
            )
            .where(
                CustomerInquiry.is_deleted == False,
                CustomerInquiry.source.isnot(None)
            )
            .group_by(CustomerInquiry.source)
            .order_by(desc('count'))
        )
        result_source = await self.db.execute(source_stmt)
        source_counts = {
            row.source or 'unknown': row.count for row in result_source.all()}

        # Converted
        converted_stmt = select(func.count()).where(
            CustomerInquiry.status == InquiryStatus.CONVERTED,
            CustomerInquiry.is_deleted == False
        )
        converted = await self.db.scalar(converted_stmt) or 0

        # Rejected
        rejected_stmt = select(func.count()).where(
            CustomerInquiry.status == InquiryStatus.REJECTED,
            CustomerInquiry.is_deleted == False
        )
        rejected = await self.db.scalar(rejected_stmt) or 0

        # Recent inquiries (10)
        recent = await self.get_recent(10)

        return {
            "total": total,
            "by_status": status_counts,
            "by_brand": brand_counts,
            "by_source": source_counts,
            "converted": converted,
            "rejected": rejected,
            "conversion_rate": round((converted / total * 100) if total > 0 else 0, 2),
            "recent": recent
        }

    # ============================================================
    # 8. BULK OPERATIONS
    # ============================================================

    async def bulk_update_status(
        self,
        inquiry_ids: List[UUID],
        new_status: str,
        note: Optional[str] = None
    ) -> int:
        """
        Bulk update status for multiple inquiries.

        Args:
            inquiry_ids: List of inquiry IDs
            new_status: New status
            note: Note for the update

        Returns:
            Number of updated inquiries
        """
        updated = 0
        for inquiry_id in inquiry_ids:
            if await self.update_status(inquiry_id, new_status, note):
                updated += 1

        return updated

    async def get_active_inquiries_count(self) -> int:
        """
        Get count of active inquiries (not completed, rejected, or closed).

        Returns:
            Number of active inquiries
        """
        active_statuses = [
            InquiryStatus.NEW,
            InquiryStatus.UNDER_REVIEW,
            InquiryStatus.CONTACTED,
            InquiryStatus.QUOTED,
            InquiryStatus.APPROVED,
        ]
        stmt = select(func.count()).where(
            CustomerInquiry.status.in_(active_statuses),
            CustomerInquiry.is_deleted == False
        )
        return await self.db.scalar(stmt) or 0

    async def get_aging_inquiries(self, days: int = 30) -> List[CustomerInquiry]:
        """
        Get inquiries that have been in status for more than N days.

        Args:
            days: Number of days threshold

        Returns:
            List of aging inquiries
        """
        threshold = datetime.now() - timedelta(days=days)
        stmt = (
            select(CustomerInquiry)
            .where(
                CustomerInquiry.created_at <= threshold,
                CustomerInquiry.status.in_([
                    InquiryStatus.NEW,
                    InquiryStatus.UNDER_REVIEW,
                    InquiryStatus.CONTACTED,
                ]),
                CustomerInquiry.is_deleted == False
            )
            .order_by(CustomerInquiry.created_at)
            .options(selectinload(CustomerInquiry.photos).limit(1))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()


# ============================================================
# 9. OVERRIDE BASE REPOSITORY METHODS
# ============================================================

    # Override get untuk include soft delete filter

    async def get(self, pk: UUID, include_deleted: bool = False) -> Optional[CustomerInquiry]:
        """
        Get by primary key with optional soft delete filter.

        Args:
            pk: Primary key (ID)
            include_deleted: Include soft-deleted records

        Returns:
            Inquiry instance or None
        """
        stmt = select(self.model).where(self.model.id == pk)
        if not include_deleted and hasattr(self.model, 'is_deleted'):
            stmt = stmt.where(self.model.is_deleted == False)

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
