# modules/restored_bikes/repositories.py

import uuid
from typing import Optional, Tuple, List
from datetime import datetime

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import BaseRepository
from .models import RestoredBike, RestoredBikePhoto, RestoredBikeDocument
from core.enum import RestoredBikeStatus


class RestoredBikeRepository(BaseRepository[RestoredBike]):
    """Repository untuk Restored Bike"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, RestoredBike)

    async def list_with_filters(
        self,
        page: int = 1,
        limit: int = 12,
        search: Optional[str] = None,
        status: Optional[str] = None,
        brand: Optional[str] = None,
    ) -> Tuple[List[RestoredBike], int]:
        """List restored bikes dengan filters dan pagination"""
        query = select(RestoredBike)
        count_query = select(func.count()).select_from(RestoredBike)

        conditions = []

        if search:
            search_pattern = f"%{search}%"
            conditions.append(
                or_(
                    RestoredBike.brand.ilike(search_pattern),
                    RestoredBike.model.ilike(search_pattern),
                    RestoredBike.customer_name.ilike(search_pattern),
                    RestoredBike.license_plate.ilike(search_pattern),
                )
            )

        if status:
            conditions.append(RestoredBike.status == status)

        if brand:
            conditions.append(RestoredBike.brand.ilike(f"%{brand}%"))

        if conditions:
            query = query.where(*conditions)
            count_query = count_query.where(*conditions)

        # Order by status (featured first, then created_at desc)
        query = query.order_by(
            RestoredBike.is_featured.desc(),
            RestoredBike.created_at.desc(),
        )

        # Pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        # Execute
        result = await self.session.execute(query)
        items = result.scalars().all()

        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one() or 0

        return items, total

    async def get_stats(self) -> dict:
        """Get statistics for restored bikes"""
        # Total
        total_result = await self.session.execute(
            select(func.count()).select_from(RestoredBike)
        )
        total = total_result.scalar_one() or 0

        # Completed
        completed_result = await self.session.execute(
            select(func.count()).select_from(RestoredBike)
            .where(RestoredBike.status == RestoredBikeStatus.COMPLETED)
        )
        completed = completed_result.scalar_one() or 0

        # In Progress
        in_progress_result = await self.session.execute(
            select(func.count()).select_from(RestoredBike)
            .where(RestoredBike.status == RestoredBikeStatus.IN_PROGRESS)
        )
        in_progress = in_progress_result.scalar_one() or 0

        # Featured
        featured_result = await self.session.execute(
            select(func.count()).select_from(RestoredBike)
            .where(RestoredBike.is_featured == True)
        )
        featured = featured_result.scalar_one() or 0

        # By brand (top 5)
        brand_result = await self.session.execute(
            select(RestoredBike.brand, func.count().label("count"))
            .group_by(RestoredBike.brand)
            .order_by(func.count().desc())
            .limit(5)
        )
        by_brand = {row.brand: row.count for row in brand_result.all()}

        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "featured": featured,
            "by_brand": by_brand,
        }


class RestoredBikePhotoRepository(BaseRepository[RestoredBikePhoto]):
    """Repository untuk Restored Bike Photos"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, RestoredBikePhoto)

    async def get_by_bike(self, bike_id: uuid.UUID) -> List[RestoredBikePhoto]:
        """Get all photos for a bike"""
        query = select(RestoredBikePhoto).where(
            RestoredBikePhoto.bike_id == bike_id
        ).order_by(RestoredBikePhoto.is_primary.desc(), RestoredBikePhoto.sort_order)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def set_primary(self, photo_id: uuid.UUID, bike_id: uuid.UUID) -> bool:
        """Set a photo as primary for a bike"""
        # Reset all photos for this bike
        await self.session.execute(
            select(RestoredBikePhoto).where(
                RestoredBikePhoto.bike_id == bike_id)
        )
        # Set the selected photo as primary
        photo = await self.get_by_id(photo_id)
        if photo and photo.bike_id == bike_id:
            photo.is_primary = True
            await self.session.commit()
            return True
        return False


class RestoredBikeDocumentRepository(BaseRepository[RestoredBikeDocument]):
    """Repository untuk Restored Bike Documents"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, RestoredBikeDocument)

    async def get_by_bike(self, bike_id: uuid.UUID) -> List[RestoredBikeDocument]:
        """Get all documents for a bike"""
        query = select(RestoredBikeDocument).where(
            RestoredBikeDocument.bike_id == bike_id
        ).order_by(RestoredBikeDocument.created_at.desc())
        result = await self.session.execute(query)
        return result.scalars().all()
