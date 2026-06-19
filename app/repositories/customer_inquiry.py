from uuid import UUID
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.customer_inquiry import CustomerInquiry
from models.projects import Project
from repositories.base import BaseRepository  # assumes you have this
from schemas.constants import InquiryStatus

class InquiryRepo(BaseRepository[CustomerInquiry]):
    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=CustomerInquiry)

    async def list_all(
        self,
        status: str | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[CustomerInquiry]:
        stmt = (
            select(CustomerInquiry)
            .options(selectinload(CustomerInquiry.project))   # ← WAJIB
            .order_by(CustomerInquiry.created_at.desc())
        )
        if status:
            stmt = stmt.where(CustomerInquiry.status == status)
        if search:
            stmt = stmt.where(
                or_(
                    CustomerInquiry.customer_name.ilike(f"%{search}%"),
                    CustomerInquiry.customer_phone_number.ilike(f"%{search}%"),
                    CustomerInquiry.vehicle_brand.ilike(f"%{search}%"),
                    CustomerInquiry.vehicle_model.ilike(f"%{search}%"),
                )
            )
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
                selectinload(CustomerInquiry.project),   # ← TAMBAHKAN INI
            )
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def update_status(self, inquiry_id: UUID, new_status: str) -> bool:
        inquiry = await self.get(inquiry_id)
        if not inquiry:
            return False
        inquiry.status = new_status
        await self.db.flush()
        return True

    async def add_activity(self, inquiry_id: UUID, activity_text: str):
        from models.customer_inquiry import InquiryActivity
        activity = InquiryActivity(inquiry_id=inquiry_id, activity=activity_text)
        self.db.add(activity)
        await self.db.flush()
        
    async def get_inquiry(self, inquiry_id: UUID):
        """Basic get without eager loading (for simple queries)."""
        stmt = select(CustomerInquiry).where(CustomerInquiry.id == inquiry_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_inquiry_with_details(self, inquiry_id: UUID):
        stmt = (
            select(CustomerInquiry)
            .where(CustomerInquiry.id == inquiry_id)
            .options(
                selectinload(CustomerInquiry.photos),
                selectinload(CustomerInquiry.activities),
                selectinload(CustomerInquiry.project).load_only(  # atau selectinload penuh
                    Project.id,
                    Project.name,
                    Project.status,
                    Project.progress,
                    Project.estimated_cost,
                    Project.actual_cost,
                    Project.estimated_revenue,
                    Project.actual_revenue,
                )
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()