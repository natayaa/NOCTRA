# modules/inquiry/repository.py
from uuid import UUID
from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, or_, and_, desc, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.base import BaseRepository
from core.constants import InquiryStatus
from .models import (
    CustomerInquiry,
    CustomerInquiryPhoto,
    InquiryActivity,
    InquiryFollowUp,
    WorkshopNote
)


class InquiryRepository(BaseRepository[CustomerInquiry]):
    """Repository untuk Customer Inquiry."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=CustomerInquiry)

    # ==================== READ ====================

    async def get_with_details(self, inquiry_id: UUID) -> Optional[CustomerInquiry]:
        """Get inquiry with all related data."""
        stmt = (
            select(CustomerInquiry)
            .where(CustomerInquiry.id == inquiry_id)
            .options(
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

    async def list_all(
        self,
        status: Optional[str] = None,
        search: Optional[str] = None,
        brand: Optional[str] = None,
        project_status: Optional[str] = None,
        has_project: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[CustomerInquiry], int]:
        """List all inquiries with filters."""
        from modules.projects.models import Project  # ✅ LAZY IMPORT DI SINI

        stmt = select(CustomerInquiry)
        count_stmt = select(func.count()).select_from(CustomerInquiry)

        filters = []

        if status:
            filters.append(CustomerInquiry.status == status)
        if brand:
            filters.append(CustomerInquiry.vehicle_brand == brand)
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

        # ✅ FILTER HAS PROJECT - Gunakan project_id
        if has_project is not None:
            if has_project:
                filters.append(CustomerInquiry.project_id.isnot(None))
            else:
                filters.append(CustomerInquiry.project_id.is_(None))

        # ✅ FILTER PROJECT STATUS - JOIN dengan Project
        if project_status:
            # Join dengan Project
            stmt = stmt.join(Project, CustomerInquiry.project_id == Project.id)
            filters.append(Project.status == project_status)

            # Untuk count, juga perlu join
            count_stmt = count_stmt.join(
                Project, CustomerInquiry.project_id == Project.id)
            count_stmt = count_stmt.where(Project.status == project_status)

        if filters:
            stmt = stmt.where(and_(*filters))
            if not project_status:  # Jika sudah ada join di atas, jangan double
                count_stmt = count_stmt.where(and_(*filters))

        stmt = stmt.options(
            selectinload(CustomerInquiry.project),
            selectinload(CustomerInquiry.photos),
        )
        stmt = stmt.order_by(desc(CustomerInquiry.created_at)
                             ).offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        inquiries = result.scalars().all()

        total = await self.db.scalar(count_stmt) or 0
        return inquiries, total

    async def get_by_phone(self, phone_number: str) -> List[CustomerInquiry]:
        """Get inquiries by phone number."""
        stmt = (
            select(CustomerInquiry)
            .where(CustomerInquiry.customer_phone_number == phone_number)
            .order_by(desc(CustomerInquiry.created_at))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_email(self, email: str) -> List[CustomerInquiry]:
        """Get inquiries by email."""
        stmt = (
            select(CustomerInquiry)
            .where(CustomerInquiry.customer_email == email)
            .order_by(desc(CustomerInquiry.created_at))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_pending_conversion(self) -> List[CustomerInquiry]:
        """Get inquiries that are ready for conversion to project."""
        stmt = (
            select(CustomerInquiry)
            .where(
                CustomerInquiry.status.in_([
                    InquiryStatus.QUOTED,
                    InquiryStatus.CONTACTED,
                    InquiryStatus.APPROVED,
                ]),
                CustomerInquiry.project.is_(None),
            )
            .order_by(CustomerInquiry.created_at)
            .options(selectinload(CustomerInquiry.photos))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_recent(self, limit: int = 10) -> List[CustomerInquiry]:
        """Get recent inquiries."""
        stmt = (
            select(CustomerInquiry)
            .order_by(desc(CustomerInquiry.created_at))
            .limit(limit)
            .options(
                selectinload(CustomerInquiry.project),
                selectinload(CustomerInquiry.photos),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    # ==================== UPDATE - OVERRIDE BASE ====================

    async def update_inquiry(self, pk: UUID, **kwargs) -> Optional[CustomerInquiry]:
        """
        Update inquiry dengan parameter kwargs.
        ✅ Menggunakan nama berbeda untuk menghindari konflik dengan BaseRepository.update()
        """
        obj = await self.get(pk)
        if not obj:
            return None

        for key, value in kwargs.items():
            if hasattr(obj, key) and value is not None:
                setattr(obj, key, value)

        # ✅ Hanya flush, tidak commit (biar service yang handle)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update_status(
        self,
        inquiry_id: UUID,
        new_status: str,
        note: Optional[str] = None
    ) -> bool:
        """Update inquiry status."""
        inquiry = await self.get(inquiry_id)
        if not inquiry:
            return False

        old_status = inquiry.status
        inquiry.status = new_status

        if note:
            inquiry.note = note

        # Track status change timestamps
        status_timestamps = {
            InquiryStatus.CONTACTED: "contacted_at",
            InquiryStatus.QUOTED: "quoted_at",
            InquiryStatus.CONVERTED: "converted_at",
            InquiryStatus.CLOSED: "closed_at",
            InquiryStatus.REJECTED: "closed_at",
        }
        if new_status in status_timestamps:
            setattr(inquiry, status_timestamps[new_status], datetime.now())

        # Add activity for status change
        await self.add_activity(
            inquiry_id=inquiry_id,
            activity_text=f"Status changed: {old_status} → {new_status}",
            activity_type="status_change",
            meta_data={"old_status": old_status, "new_status": new_status}
        )

        await self.db.flush()
        return True

    async def update_conversion_rate(
        self,
        inquiry_id: UUID,
        rate: Decimal
    ) -> bool:
        """Update conversion rate for inquiry."""
        inquiry = await self.get(inquiry_id)
        if not inquiry:
            return False

        inquiry.conversion_rate = rate
        await self.db.flush()
        return True

    # ==================== DELETE - OVERRIDE BASE ====================

    async def delete_inquiry(self, pk: UUID) -> bool:
        """
        Delete inquiry by primary key.
        ✅ Menggunakan nama berbeda untuk menghindari konflik
        """
        obj = await self.get(pk)
        if not obj:
            return False

        await self.db.delete(obj)
        await self.db.flush()
        return True

    # ==================== ACTIVITIES ====================

    async def add_activity(
        self,
        inquiry_id: UUID,
        activity_text: str,
        activity_type: Optional[str] = None,
        performed_by: Optional[str] = None,
        meta_data: Optional[dict] = None
    ) -> InquiryActivity:
        """Add activity to inquiry."""
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

    async def get_activities(
        self,
        inquiry_id: UUID,
        limit: int = 50
    ) -> List[InquiryActivity]:
        """Get all activities for an inquiry."""
        stmt = (
            select(InquiryActivity)
            .where(InquiryActivity.inquiry_id == inquiry_id)
            .order_by(desc(InquiryActivity.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    # ==================== WORKSHOP NOTES ====================

    async def add_workshop_note(
        self,
        inquiry_id: UUID,
        note: str,
        note_type: str = "internal",
        author: Optional[str] = None,
        is_private: bool = False
    ) -> WorkshopNote:
        """Add workshop note to inquiry."""
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

    async def get_workshop_notes(
        self,
        inquiry_id: UUID,
        include_private: bool = False
    ) -> List[WorkshopNote]:
        """Get all workshop notes for an inquiry."""
        stmt = select(WorkshopNote).where(
            WorkshopNote.inquiry_id == inquiry_id)
        if not include_private:
            stmt = stmt.where(WorkshopNote.is_private == False)
        stmt = stmt.order_by(desc(WorkshopNote.created_at))
        result = await self.db.execute(stmt)
        return result.scalars().all()

    # ==================== PHOTOS ====================

    async def add_photo(
        self,
        inquiry_id: UUID,
        photo_data: dict
    ) -> CustomerInquiryPhoto:
        """Add photo to inquiry."""
        existing_photos = await self.get_photos(inquiry_id)
        if not existing_photos:
            photo_data["is_primary"] = True

        photo = CustomerInquiryPhoto(inquiry_id=inquiry_id, **photo_data)
        self.db.add(photo)
        await self.db.flush()
        await self.db.refresh(photo)
        return photo

    async def get_photos(self, inquiry_id: UUID) -> List[CustomerInquiryPhoto]:
        """Get all photos for an inquiry."""
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

    async def set_primary_photo(self, photo_id: UUID) -> bool:
        """Set a photo as primary."""
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
        return True

    async def delete_photo(self, photo_id: UUID) -> bool:
        """Delete a photo."""
        stmt = select(CustomerInquiryPhoto).where(
            CustomerInquiryPhoto.id == photo_id)
        result = await self.db.execute(stmt)
        photo = result.scalar_one_or_none()

        if not photo:
            return False

        if photo.is_primary:
            other_photos = await self.get_photos(photo.inquiry_id)
            if len(other_photos) > 1:
                for p in other_photos:
                    if p.id != photo_id:
                        p.is_primary = True
                        break

        await self.db.delete(photo)
        await self.db.flush()
        return True

    # ==================== FOLLOW-UPS ====================

    async def get_follow_ups(self, inquiry_id: UUID) -> List[InquiryFollowUp]:
        """Get all follow-ups for an inquiry."""
        stmt = (
            select(InquiryFollowUp)
            .where(InquiryFollowUp.inquiry_id == inquiry_id)
            .order_by(InquiryFollowUp.scheduled_at)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_follow_up(self, follow_up_id: UUID) -> Optional[InquiryFollowUp]:
        """Get follow-up by ID."""
        stmt = select(InquiryFollowUp).where(
            InquiryFollowUp.id == follow_up_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def add_follow_up(self, inquiry_id: UUID, data: Dict[str, Any]) -> InquiryFollowUp:
        """Add follow-up to inquiry."""
        follow_up = InquiryFollowUp(inquiry_id=inquiry_id, **data)
        self.db.add(follow_up)
        await self.db.flush()
        await self.db.refresh(follow_up)
        return follow_up

    async def update_follow_up(self, follow_up_id: UUID, data: Dict[str, Any]) -> Optional[InquiryFollowUp]:
        """Update follow-up."""
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
        """Complete follow-up."""
        return await self.update_follow_up(follow_up_id, {
            "status": "done",
            "performed_at": datetime.now(),
            "result": result,
            "note": note
        })

    async def delete_follow_up(self, follow_up_id: UUID) -> bool:
        """Delete follow-up."""
        follow_up = await self.get_follow_up(follow_up_id)
        if not follow_up:
            return False

        await self.db.delete(follow_up)
        await self.db.flush()
        return True

    async def get_pending_follow_ups(self) -> List[InquiryFollowUp]:
        """Get all pending follow-ups."""
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
        """Get upcoming follow-ups within next N hours."""
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
        """Get follow-ups assigned to a specific person."""
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

    # ==================== STATISTICS ====================

    async def get_statistics(self) -> dict:
        """Get inquiry statistics for dashboard."""
        total_stmt = select(func.count()).select_from(CustomerInquiry)
        total = await self.db.scalar(total_stmt) or 0

        # By status
        status_stmt = select(
            CustomerInquiry.status,
            func.count().label('count')
        ).group_by(CustomerInquiry.status)
        result_status = await self.db.execute(status_stmt)
        status_counts = {row.status: row.count for row in result_status.all()}

        # By brand
        brand_stmt = select(
            CustomerInquiry.vehicle_brand,
            func.count().label('count')
        ).group_by(CustomerInquiry.vehicle_brand).order_by(desc('count')).limit(10)
        result_brand = await self.db.execute(brand_stmt)
        brand_counts = {
            row.vehicle_brand: row.count for row in result_brand.all()}

        # By source
        source_stmt = select(
            CustomerInquiry.source,
            func.count().label('count')
        ).group_by(CustomerInquiry.source).order_by(desc('count'))
        result_source = await self.db.execute(source_stmt)
        source_counts = {
            row.source or 'unknown': row.count for row in result_source.all()}

        # Conversion rate
        converted_stmt = select(func.count()).where(
            CustomerInquiry.status == InquiryStatus.CONVERTED
        )
        converted = await self.db.scalar(converted_stmt) or 0

        rejected_stmt = select(func.count()).where(
            CustomerInquiry.status == InquiryStatus.REJECTED
        )
        rejected = await self.db.scalar(rejected_stmt) or 0

        recent = await self.get_recent(10)
        recent_data = []
        for inquiry in recent:
            recent_data.append({
                "id": str(inquiry.id),
                "customer_name": inquiry.customer_name,
                "customer_phone_number": inquiry.customer_phone_number,
                "vehicle_brand": inquiry.vehicle_brand,
                "vehicle_model": inquiry.vehicle_model,
                "project_type": inquiry.project_type,
                "status": inquiry.status,
                "source": inquiry.source,
                "created_at": inquiry.created_at.isoformat() if inquiry.created_at else None,
                "project": {
                    "id": str(inquiry.project.id),
                    "name": inquiry.project.name,
                    "status": inquiry.project.status,
                    "progress": inquiry.project.progress,
                    "estimated_cost": float(inquiry.project.estimated_cost or 0),
                    "actual_cost": float(inquiry.project.actual_cost or 0),
                    "created_at": inquiry.project.created_at.isoformat() if inquiry.project.created_at else None
                } if inquiry.project else None
            })

        return {
            "total": total,
            "by_status": status_counts,
            "by_brand": brand_counts,
            "by_source": source_counts,
            "converted": converted,
            "rejected": rejected,
            "conversion_rate": round((converted / total * 100) if total > 0 else 0, 2),
            "recent": recent_data
        }
