from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.customer_inquiry import CustomerInquiry
from repositories.base import BaseRepository


class InquiryRepo(BaseRepository[CustomerInquiry]):
    def __init__(self, db: AsyncSession):
        super().__init__(self, db=db, model=CustomerInquiry)

    async def find_by_email(self, email: str) -> CustomerInquiry | None:
        stmt = (select(CustomerInquiry).where(
            CustomerInquiry.customer_email == email))

        ret = await self.db.execute(stmt)
        return ret.scalar_one_or_none()

    async def find_by_phone(self, phone_number: str) -> CustomerInquiry | None:
        stmt = (select(CustomerInquiry).where(
            CustomerInquiry.customer_phone_number == phone_number))
        ret = await self.db.execute(stmt)
        return ret.scalar_one_or_none()

    async def get_latest_inquiry(self, limit: int = 10) -> list[CustomerInquiry]:
        stmt = (select(CustomerInquiry).order_by(
            CustomerInquiry.created_at.desc()).limit(limit))
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def search(self, keyword: str, limit: int = 20) -> list[CustomerInquiry]:
        stmt = (select(CustomerInquiry).where(
            CustomerInquiry.customer_name.ilike(f"%{keyword}%")
          | CustomerInquiry.customer_email.ilike(f"%{keyword}%")
          | CustomerInquiry.customer_phone_number.ilike(f"%{keyword}%")
          | CustomerInquiry.vehicle_brand.ilike(f"%{keyword}%")
            ).limit(limit=limit)
        )
        
        res = await self.db.execute(stmt)
        return list(res.scalars().all())