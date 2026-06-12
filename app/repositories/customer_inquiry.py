from uuid import UUID

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.customer_inquiry import CustomerInquiry
from repositories.base import BaseRepository


class InquiryRepo(BaseRepository[CustomerInquiry]):
    def __init__(self, db: AsyncSession):
        super().__init__(db=db, model=CustomerInquiry)

    async def find_by_email(self, email: str) -> CustomerInquiry | None:
        stmt = select(CustomerInquiry).where(
            CustomerInquiry.customer_email == email
        )

        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def find_by_phone(self, phone_number: str) -> CustomerInquiry | None:
        stmt = select(CustomerInquiry).where(
            CustomerInquiry.customer_phone_number == phone_number
        )

        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_latest_inquiry(self, limit: int = 10) -> list[CustomerInquiry]:
        stmt = (
            select(CustomerInquiry)
            .order_by(CustomerInquiry.created_at.desc())
            .limit(limit)
        )

        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def search(self, keyword: str, limit: int = 20) -> list[CustomerInquiry]:
        stmt = (
            select(CustomerInquiry)
            .where(
                or_(
                    CustomerInquiry.customer_name.ilike(f"%{keyword}%"),
                    CustomerInquiry.customer_email.ilike(f"%{keyword}%"),
                    CustomerInquiry.customer_phone_number.ilike(f"%{keyword}%"),
                    CustomerInquiry.vehicle_brand.ilike(f"%{keyword}%"),
                    CustomerInquiry.vehicle_model.ilike(f"%{keyword}%"),
                )
            )
            .order_by(CustomerInquiry.created_at.desc())
            .limit(limit)
        )

        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_inquiry_with_photos(self, inquiry_id: UUID) -> CustomerInquiry | None:
        stmt = (
            select(CustomerInquiry)
            .options(selectinload(CustomerInquiry.photos))
            .where(CustomerInquiry.id == inquiry_id)
        )

        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()