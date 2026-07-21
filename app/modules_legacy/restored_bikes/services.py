# modules/restored_bikes/services.py

import uuid
import os
import shutil
from typing import Optional, List, Tuple
from datetime import datetime

from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from repository import (
    RestoredBikeRepository,
    RestoredBikePhotoRepository,
    RestoredBikeDocumentRepository,
)
from .models import RestoredBike, RestoredBikePhoto, RestoredBikeDocument
from .schemas import (
    RestoredBikeCreate,
    RestoredBikeUpdate,
    RestoredBikeResponse,
    RestoredBikeSummary,
    RestoredBikeStats,
    PaginatedRestoredBikeResponse,
)
from core.config import settings
from core.exceptions import NotFoundError, ValidationError


class RestoredBikeService:
    """Service untuk Restored Bike"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = RestoredBikeRepository(session)
        self.photo_repo = RestoredBikePhotoRepository(session)
        self.doc_repo = RestoredBikeDocumentRepository(session)

    # ============================================================
    # MAIN CRUD
    # ============================================================

    async def list_bikes(
        self,
        page: int = 1,
        limit: int = 12,
        search: Optional[str] = None,
        status: Optional[str] = None,
        brand: Optional[str] = None,
    ) -> Tuple[List[RestoredBikeSummary], int, int]:
        """List restored bikes with pagination"""
        bikes, total = await self.repo.list_with_filters(
            page=page,
            limit=limit,
            search=search,
            status=status,
            brand=brand,
        )

        summaries = []
        for bike in bikes:
            photos = await self.photo_repo.get_by_bike(bike.id)
            cover_image = None
            if photos:
                primary = next((p for p in photos if p.is_primary), None)
                cover_image = primary.url if primary else photos[0].url

            summaries.append(
                RestoredBikeSummary(
                    **bike.__dict__,
                    cover_image=cover_image,
                    photo_count=len(photos),
                )
            )

        total_pages = (total + limit - 1) // limit if total > 0 else 1
        return summaries, total, total_pages

    async def get_bike(self, bike_id: uuid.UUID) -> Optional[RestoredBikeResponse]:
        """Get bike detail with photos and documents"""
        bike = await self.repo.get_by_id(bike_id)
        if not bike:
            return None

        # Load photos and documents (already loaded via selectin)
        photos = await self.photo_repo.get_by_bike(bike_id)
        documents = await self.doc_repo.get_by_bike(bike_id)

        response = RestoredBikeResponse.from_orm(bike)
        response.photos = [
            RestoredBikePhotoResponse.from_orm(p) for p in photos]
        response.documents = [
            RestoredBikeDocumentResponse.from_orm(d) for d in documents]

        return response

    async def create_bike(self, data: RestoredBikeCreate) -> RestoredBike:
        """Create a new restored bike"""
        # Validate status
        if data.is_featured and data.status != "completed":
            raise ValidationError(
                "Featured bikes must have 'completed' status")

        bike = RestoredBike(**data.model_dump())
        return await self.repo.create(bike)

    async def update_bike(
        self,
        bike_id: uuid.UUID,
        data: RestoredBikeUpdate,
    ) -> Optional[RestoredBike]:
        """Update a restored bike"""
        bike = await self.repo.get_by_id(bike_id)
        if not bike:
            return None

        # Validate featured status
        if data.is_featured is True and data.status not in [None, "completed"]:
            # If status is being updated, check it
            status = data.status or bike.status
            if status != "completed":
                raise ValidationError(
                    "Featured bikes must have 'completed' status")

        update_data = data.model_dump(exclude_unset=True)
        return await self.repo.update(bike, update_data)

    async def delete_bike(self, bike_id: uuid.UUID) -> bool:
        """Delete a restored bike and all associated files"""
        bike = await self.repo.get_by_id(bike_id)
        if not bike:
            return False

        # Delete photos from storage
        photos = await self.photo_repo.get_by_bike(bike_id)
        for photo in photos:
            file_path = os.path.join(settings.MEDIA_ROOT, photo.file_path)
            if os.path.exists(file_path):
                os.remove(file_path)

        # Delete documents from storage
        documents = await self.doc_repo.get_by_bike(bike_id)
        for doc in documents:
            file_path = os.path.join(settings.MEDIA_ROOT, doc.file_path)
            if os.path.exists(file_path):
                os.remove(file_path)

        return await self.repo.delete(bike_id)

    # ============================================================
    # STATISTICS
    # ============================================================

    async def get_stats(self) -> RestoredBikeStats:
        """Get statistics"""
        stats = await self.repo.get_stats()
        return RestoredBikeStats(**stats)

    # ============================================================
    # PHOTO MANAGEMENT
    # ============================================================

    async def upload_photos(
        self,
        bike_id: uuid.UUID,
        files: List[UploadFile],
    ) -> List[RestoredBikePhoto]:
        """Upload multiple photos for a bike"""
        bike = await self.repo.get_by_id(bike_id)
        if not bike:
            raise NotFoundError("Bike not found")

        uploaded_photos = []
        existing_photos = await self.photo_repo.get_by_bike(bike_id)
        is_first = len(existing_photos) == 0

        for idx, file in enumerate(files):
            # Validate file
            if not file.content_type.startswith("image/"):
                raise ValidationError(f"{file.filename} is not a valid image")

            # Save file
            file_path = await self._save_file(
                file,
                "restored_bikes",
                bike_id,
                "photos",
            )

            photo = RestoredBikePhoto(
                bike_id=bike_id,
                url=f"/media/{file_path}",
                file_path=file_path,
                filename=file.filename,
                file_size=file.size if hasattr(file, "size") else None,
                mime_type=file.content_type,
                is_primary=is_first and idx == 0,
                sort_order=idx,
            )
            uploaded_photos.append(photo)

        await self.photo_repo.bulk_create(uploaded_photos)
        return uploaded_photos

    async def delete_photo(self, photo_id: uuid.UUID) -> bool:
        """Delete a photo"""
        photo = await self.photo_repo.get_by_id(photo_id)
        if not photo:
            return False

        # Delete file from storage
        file_path = os.path.join(settings.MEDIA_ROOT, photo.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)

        return await self.photo_repo.delete(photo_id)

    # ============================================================
    # DOCUMENT MANAGEMENT
    # ============================================================

    async def upload_document(
        self,
        bike_id: uuid.UUID,
        file: UploadFile,
    ) -> RestoredBikeDocument:
        """Upload a document for a bike"""
        bike = await self.repo.get_by_id(bike_id)
        if not bike:
            raise NotFoundError("Bike not found")

        # Save file
        file_path = await self._save_file(
            file,
            "restored_bikes",
            bike_id,
            "documents",
        )

        doc = RestoredBikeDocument(
            bike_id=bike_id,
            filename=file.filename,
            file_path=file_path,
            url=f"/media/{file_path}",
            file_size=file.size if hasattr(file, "size") else None,
            mime_type=file.content_type,
        )

        return await self.doc_repo.create(doc)

    async def delete_document(self, doc_id: uuid.UUID) -> bool:
        """Delete a document"""
        doc = await self.doc_repo.get_by_id(doc_id)
        if not doc:
            return False

        # Delete file from storage
        file_path = os.path.join(settings.MEDIA_ROOT, doc.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)

        return await self.doc_repo.delete(doc_id)

    async def get_document_file_path(self, doc_id: uuid.UUID) -> Optional[str]:
        """Get document file path for download"""
        doc = await self.doc_repo.get_by_id(doc_id)
        if not doc:
            return None
        return os.path.join(settings.MEDIA_ROOT, doc.file_path)

    # ============================================================
    # UTILITY
    # ============================================================

    async def _save_file(
        self,
        file: UploadFile,
        module: str,
        bike_id: uuid.UUID,
        subfolder: str,
    ) -> str:
        """Save uploaded file to storage"""
        # Create directory
        upload_dir = os.path.join(
            settings.MEDIA_ROOT,
            module,
            str(bike_id),
            subfolder,
        )
        os.makedirs(upload_dir, exist_ok=True)

        # Generate unique filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename.replace(' ', '_')}"
        file_path = os.path.join(upload_dir, safe_filename)

        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Return relative path
        return os.path.join(module, str(bike_id), subfolder, safe_filename)
