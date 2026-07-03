# repositories/customer_inquiry.py
from uuid import UUID
from sqlalchemy import select, or_, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from models.customer_inquiry import (
    CustomerInquiry, 
    CustomerInquiryPhoto, 
    InquiryActivity, 
    WorkshopNote
)
from models.projects import Project
from repositories.base import BaseRepository


class InquiryRepo(BaseRepository[CustomerInquiry]):
    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=CustomerInquiry)

    async def list_all(
        self, 
        status: str | None = None, 
        search: str | None = None, 
        brand: str | None = None,
        limit: int = 100, 
        offset: int = 0
    ) -> list[CustomerInquiry]:
        stmt = (
            select(CustomerInquiry)
            .options(
                selectinload(CustomerInquiry.project),
                selectinload(CustomerInquiry.photos)  # Only load first photo
            )
            .order_by(CustomerInquiry.created_at.desc())
        )
        
        filters = []
        if status:
            filters.append(CustomerInquiry.status == status)
        if brand:
            filters.append(CustomerInquiry.vehicle_brand == brand)
        if search:
            filters.append(
                or_(
                    CustomerInquiry.customer_name.ilike(f"%{search}%"),
                    CustomerInquiry.customer_phone_number.ilike(f"%{search}%"),
                    CustomerInquiry.vehicle_brand.ilike(f"%{search}%"),
                    CustomerInquiry.vehicle_model.ilike(f"%{search}%"),
                    CustomerInquiry.province.ilike(f"%{search}%"),
                    CustomerInquiry.city.ilike(f"%{search}%"),
                )
            )
        
        if filters:
            stmt = stmt.where(and_(*filters))
            
        stmt = stmt.offset(offset).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_with_details(self, inquiry_id: UUID) -> CustomerInquiry | None:
        stmt = (
            select(CustomerInquiry)
            .where(CustomerInquiry.id == inquiry_id)
            .options(
                selectinload(CustomerInquiry.photos),
                selectinload(CustomerInquiry.activities),
                selectinload(CustomerInquiry.workshop_notes),
                selectinload(CustomerInquiry.project).options(
                    selectinload(Project.inquiry),
                    selectinload(Project.tasks),
                    selectinload(Project.expense_items),
                    selectinload(Project.labor_items),
                ),
            )
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_inquiry_with_photos(self, inquiry_id: UUID) -> CustomerInquiry | None:
        stmt = (
            select(CustomerInquiry)
            .where(CustomerInquiry.id == inquiry_id)
            .options(
                selectinload(CustomerInquiry.photos),
                selectinload(CustomerInquiry.project),
            )
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def update_status(self, inquiry_id: UUID, new_status: str, note: str | None = None) -> bool:
        inquiry = await self.get(inquiry_id)
        if not inquiry:
            return False
        
        inquiry.status = new_status
        if note:
            inquiry.note = note
            
        # Track status change
        if new_status == "contacted":
            inquiry.contacted_at = func.now()
        elif new_status == "quoted":
            inquiry.quoted_at = func.now()
        elif new_status == "converted":
            inquiry.converted_at = func.now()
            
        await self.db.flush()
        return True

    async def add_activity(
        self, 
        inquiry_id: UUID, 
        activity_text: str,
        activity_type: str | None = None,
        performed_by: str | None = None,
        meta_data: dict | None = None
    ):
        activity = InquiryActivity(
            inquiry_id=inquiry_id,
            activity=activity_text,
            activity_type=activity_type,
            performed_by=performed_by,
            meta_data=meta_data
        )
        self.db.add(activity)
        await self.db.flush()
        return activity

    async def add_workshop_note(
        self,
        inquiry_id: UUID,
        note: str,
        note_type: str = "internal",
        author: str | None = None,
        is_private: bool = False
    ) -> WorkshopNote:
        workshop_note = WorkshopNote(
            inquiry_id=inquiry_id,
            note=note,
            note_type=note_type,
            author=author,
            is_private=is_private
        )
        self.db.add(workshop_note)
        await self.db.flush()
        return workshop_note

    async def add_photo(self, inquiry_id: UUID, photo_data: dict) -> CustomerInquiryPhoto:
        photo = CustomerInquiryPhoto(
            inquiry_id=inquiry_id,
            **photo_data
        )
        self.db.add(photo)
        await self.db.flush()
        return photo

    async def get_photos(self, inquiry_id: UUID) -> list[CustomerInquiryPhoto]:
        stmt = (
            select(CustomerInquiryPhoto)
            .where(CustomerInquiryPhoto.inquiry_id == inquiry_id)
            .order_by(CustomerInquiryPhoto.sort_order, CustomerInquiryPhoto.created_at)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def delete_photo(self, photo_id: UUID) -> bool:
        stmt = select(CustomerInquiryPhoto).where(CustomerInquiryPhoto.id == photo_id)
        res = await self.db.execute(stmt)
        photo = res.scalar_one_or_none()
        if not photo:
            return False
        await self.db.delete(photo)
        await self.db.flush()
        return True

    async def get_activities(self, inquiry_id: UUID) -> list[InquiryActivity]:
        stmt = (
            select(InquiryActivity)
            .where(InquiryActivity.inquiry_id == inquiry_id)
            .order_by(InquiryActivity.created_at.desc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_inquiry_by_phone(self, phone_number: str) -> list[CustomerInquiry]:
        stmt = (
            select(CustomerInquiry)
            .where(CustomerInquiry.customer_phone_number == phone_number)
            .order_by(CustomerInquiry.created_at.desc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_inquiry_by_email(self, email: str) -> list[CustomerInquiry]:
        stmt = (
            select(CustomerInquiry)
            .where(CustomerInquiry.customer_email == email)
            .order_by(CustomerInquiry.created_at.desc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_statistics(self) -> dict:
        """Get inquiry statistics for dashboard"""
        total_stmt = select(func.count()).select_from(CustomerInquiry)
        total = await self.db.scalar(total_stmt) or 0

        # Count by status
        status_stmt = select(
            CustomerInquiry.status,
            func.count().label('count')
        ).group_by(CustomerInquiry.status)
        res = await self.db.execute(status_stmt)
        status_counts = {row.status: row.count for row in res.all()}

        # Count by brand
        brand_stmt = select(
            CustomerInquiry.vehicle_brand,
            func.count().label('count')
        ).group_by(CustomerInquiry.vehicle_brand).order_by(desc('count'))
        res = await self.db.execute(brand_stmt)
        brand_counts = {row.vehicle_brand: row.count for row in res.all()}

        # Recent inquiries
        recent_stmt = (
            select(CustomerInquiry)
            .order_by(CustomerInquiry.created_at.desc())
            .limit(10)
        )
        res = await self.db.execute(recent_stmt)
        recent = list(res.scalars().all())

        return {
            "total": total,
            "by_status": status_counts,
            "by_brand": brand_counts,
            "recent": recent
        }