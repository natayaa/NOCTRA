# modules/inquiry/services.py
import os
import re
from pathlib import Path
from uuid import uuid4, UUID
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from decimal import Decimal

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from modules.payment.models import InquiryInvoice, InquiryPayment
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
    InquirySendQuotation,
    InquiryReject,
    InquiryClose,
    NoteCreate,
    InquiryStatusUpdate,
)
from modules.settings.services import SettingsService


# ============================================================================
# CONSTANTS
# ============================================================================

# Allowed image extensions
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'}

# Max file size (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# Upload directory (relative to project root)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "uploads" / "customer_inquiries"


# ============================================================================
# SERVICE CLASS
# ============================================================================

class InquiryService:
    """Service untuk Customer Inquiry dengan complete business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = InquiryRepository(db)
        self.settings_service = SettingsService(db)
        self._stats_cache = None
        self._stats_cache_time = None
        self._cache_ttl = 300  # 5 minutes

    # ============================================================
    # 1. CORE CRUD OPERATIONS
    # ============================================================

    async def create_inquiry(self, request: CustomerInquiryCreate,
        photos: Optional[List[UploadFile]] = None,
        ip_address: Optional[str] = None, user_agent: Optional[str] = None
    ) -> CustomerInquiry:
        """
        Create a new inquiry with validation and optional photos.
        
        Args:
            request: Inquiry data
            photos: Optional list of photos
            ip_address: Customer IP address
            user_agent: Customer browser user agent
        
        Returns:
            Created inquiry instance
        
        Raises:
            ValidationError: If validation fails
        """
        # 1. Validate project type from settings
        project_types = await self.settings_service.list_project_types()
        valid_types = [pt.name for pt in project_types if pt.is_active]
        
        if request.project_type not in valid_types:
            raise ValidationError(
                f"Invalid project type: {request.project_type}. "
                f"Available types: {', '.join(valid_types)}"
            )

        # 2. Check for duplicate inquiry (same phone in last 7 days)
        existing = await self.repo.get_by_phone(request.customer_phone_number)
        if existing:
            seven_days_ago = datetime.now() - timedelta(days=7)
            recent = [e for e in existing if e.created_at > seven_days_ago]
            if recent:
                raise ValidationError(
                    f"Customer with phone {request.customer_phone_number} already submitted "
                    f"an inquiry on {recent[0].created_at.strftime('%Y-%m-%d')}. "
                    "Please wait before submitting again."
                )

        # 3. Validate phone format
        cleaned_phone = request.customer_phone_number.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        if not re.match(r'^(\+62|62|08)\d{8,13}$', cleaned_phone):
            raise ValidationError(
                "Invalid phone number format. Use: 081234567890 or +6281234567890"
            )

        # 4. Create inquiry
        inquiry_data = request.model_dump()
        inquiry = await self.repo.create_inquiry(
            inquiry_data,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # 5. Handle photos if provided
        if photos:
            for idx, photo in enumerate(photos):
                if photo.filename:
                    photo_obj = await self._save_photo(
                        inquiry.id, 
                        photo, 
                        "initial", 
                        is_primary=(idx == 0)
                    )

        # 6. Log activity
        await self.repo.add_activity(
            inquiry.id,
            f"New inquiry created by {inquiry.customer_name}",
            "creation",
            performed_by="customer",
            meta_data={
                "source": request.source or "website",
                "project_type": request.project_type,
                "vehicle": f"{request.vehicle_brand} {request.vehicle_model}"
            }
        )

        await self.db.flush()
        await self.db.refresh(inquiry)
        self.invalidate_cache()
        return inquiry

    async def get_inquiry(self, inquiry_id: UUID) -> Optional[CustomerInquiry]:
        """
        Get inquiry with all details.
        
        Args:
            inquiry_id: ID inquiry
        
        Returns:
            Inquiry instance or None
        """
        return await self.repo.get_with_details(inquiry_id)

    async def list_inquiries(self, status: Optional[str] = None,
        search: Optional[str] = None, brand: Optional[str] = None,
        project_status: Optional[str] = None, has_project: Optional[bool] = None,
        limit: int = 100, offset: int = 0,
        include_deleted: bool = False) -> tuple[List[CustomerInquiry], int]:
        """
        List inquiries with filters.
        
        Args:
            status: Filter by inquiry status
            search: Search by name, phone, brand, model, plate
            brand: Filter by vehicle brand
            project_status: Filter by project status
            has_project: Filter by project existence
            limit: Items per page
            offset: Pagination offset
            include_deleted: Include soft-deleted records
        
        Returns:
            Tuple of (inquiries, total_count)
        """
        return await self.repo.list_all(
            status=status,
            search=search,
            brand=brand,
            project_status=project_status,
            has_project=has_project,
            limit=limit,
            offset=offset,
            include_deleted=include_deleted
        )

    async def update_inquiry(self, inquiry_id: UUID, data: CustomerInquiryUpdate) -> Optional[CustomerInquiry]:
        """
        Update inquiry.
        
        Args:
            inquiry_id: ID inquiry
            data: Update data
        
        Returns:
            Updated inquiry instance
        
        Raises:
            NotFoundError: If inquiry not found
        """
        inquiry = await self.repo.get(inquiry_id)
        if not inquiry:
            raise NotFoundError(f"Inquiry {inquiry_id} not found")

        update_data = data.model_dump(exclude_unset=True)
        
        # Validate project type if being updated
        if 'project_type' in update_data:
            project_types = await self.settings_service.list_project_types()
            valid_types = [pt.name for pt in project_types if pt.is_active]
            if update_data['project_type'] not in valid_types:
                raise ValidationError(
                    f"Invalid project type: {update_data['project_type']}. "
                    f"Available types: {', '.join(valid_types)}"
                )

        
        result = await self.repo.update_inquiry(inquiry_id, update_data)
        self.invalidate_cache()
        return result

    async def delete_inquiry(self, inquiry_id: UUID, permanent: bool = False) -> bool:
        """
        Delete an inquiry.
        
        Args:
            inquiry_id: ID inquiry
            permanent: Permanent delete or soft delete
        
        Returns:
            True if deleted
        
        Raises:
            NotFoundError: If inquiry not found
        """
        inquiry = await self.repo.get(inquiry_id)
        if not inquiry:
            raise NotFoundError(f"Inquiry {inquiry_id} not found")
        
        # Prevent deletion of converted inquiries
        if inquiry.is_converted:
            raise BusinessError(
                f"Cannot delete inquiry {inquiry_id} because it has been converted to project"
            )

        if permanent:
            return await self.repo.hard_delete_inquiry(inquiry_id)
        return await self.repo.delete_inquiry(inquiry_id)

    # ============================================================
    # 2. STATUS MANAGEMENT
    # ============================================================

    async def update_status(self, inquiry_id: UUID, status: str, note: Optional[str] = None) -> bool:
        """
        Update inquiry status with transition validation.
        
        Args:
            inquiry_id: ID inquiry
            status: New status
            note: Note for the change
        
        Returns:
            True if updated
        
        Raises:
            NotFoundError: If inquiry not found
            ValidationError: If status transition not allowed
        """
        # Validate status exists
        valid_statuses = [e.value for e in InquiryStatus]
        if status not in valid_statuses:
            raise ValidationError(f"Invalid inquiry status: {status}")

        # Get workflow from settings
        workflow_map = await self.settings_service.get_status_workflow_map()
        if not inquiry.can_transition_to(status, workflow_map):
            raise ValidationError(f"Workflow status for {inquiry_id} for {status} doesn't exists")
        
        # Check if transition is allowed
        inquiry = await self.repo.get(inquiry_id)
        if not inquiry:
            raise NotFoundError(f"Inquiry {inquiry_id} not found")
        
        current_status = inquiry.status
        allowed = workflow_map.get(current_status, [])
        
        if status not in allowed:
            raise ValidationError(
                f"Cannot transition from '{current_status}' to '{status}'. "
                f"Allowed transitions: {allowed}"
            )

        return await self.repo.update_status(inquiry_id, status, note)

    async def contact_customer(self, inquiry_id: UUID, note: Optional[str] = None) -> bool:
        """
        Mark inquiry as contacted.
        
        Args:
            inquiry_id: ID inquiry
            note: Note for the contact
        
        Returns:
            True if updated
        """
        return await self.update_status(inquiry_id, InquiryStatus.CONTACTED, note)

    async def send_quote(self, inquiry_id: UUID, estimated_cost: Decimal, notes: Optional[str] = None) -> bool:
        """
        Send quotation to customer.
        
        Args:
            inquiry_id: ID inquiry
            estimated_cost: Estimated cost
            notes: Notes for quotation
        
        Returns:
            True if updated
        
        Raises:
            NotFoundError: If inquiry not found
        """
        inquiry = await self.repo.get(inquiry_id)
        if not inquiry:
            raise NotFoundError(f"Inquiry {inquiry_id} not found")

        # Update inquiry
        inquiry.status = InquiryStatus.QUOTED
        inquiry.quoted_at = datetime.now()
        if notes:
            inquiry.note = notes

        await self.db.flush()

        # Log activity
        cost_float = float(estimated_cost)
        await self.repo.add_activity(
            inquiry_id,
            f"Quotation sent: Rp {cost_float:,.2f}" + (f" - {notes}" if notes else ""),
            "quotation",
            performed_by="system",
            meta_data={"estimated_cost": cost_float, "notes": notes}
        )
        
        return True

    async def reject_inquiry(self, inquiry_id: UUID, reason: str) -> bool:
        """
        Reject inquiry with reason.
        
        Args:
            inquiry_id: ID inquiry
            reason: Reason for rejection
        
        Returns:
            True if updated
        
        Raises:
            NotFoundError: If inquiry not found
        """
        inquiry = await self.repo.get(inquiry_id)
        if not inquiry:
            raise NotFoundError(f"Inquiry {inquiry_id} not found")

        success = await self.repo.update_status(inquiry_id, InquiryStatus.REJECTED, reason)
        
        if success:
            await self.repo.add_activity(
                inquiry_id,
                f"Inquiry rejected: {reason}",
                "rejection",
                performed_by="system",
                meta_data={"reason": reason}
            )
            await self.repo.add_workshop_note(
                inquiry_id,
                f"Rejected: {reason}",
                "rejection",
                author="system"
            )
        
        return success

    async def close_inquiry(self, inquiry_id: UUID, reason: str, note: Optional[str] = None) -> bool:
        """
        Close an inquiry.
        
        Args:
            inquiry_id: ID inquiry
            reason: Reason for closing
            note: Additional note
        
        Returns:
            True if updated
        
        Raises:
            NotFoundError: If inquiry not found
        """
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
            performed_by="system",
            meta_data={"reason": reason, "note": note}
        )
        
        return True

    # ============================================================
    # 3. CONVERSION TO PROJECT
    # ============================================================

    async def convert_to_project(self, inquiry_id: UUID, data: InquiryConvertToProject) -> Any:  # Project
        """
        Convert inquiry to project.
        
        Args:
            inquiry_id: ID inquiry
            data: Conversion data
        
        Returns:
            Created project instance
        
        Raises:
            NotFoundError: If inquiry not found
            BusinessError: If conversion not allowed
            ValidationError: If validation fails
        """
        from modules.projects.models import Project
        from modules.projects.schemas import ProjectCreate
        from app.modules.projects.services_old import ProjectService

        # 1. Get inquiry with details
        inquiry = await self.repo.get_with_details(inquiry_id)
        if not inquiry:
            raise NotFoundError(f"Inquiry {inquiry_id} not found")

        # 2. Check if already converted
        if inquiry.is_converted or inquiry.project_id is not None:
            raise BusinessError("Inquiry already converted to project")

        # 3. Check if status allows conversion
        allowed_statuses = [
            InquiryStatus.NEW,
            InquiryStatus.UNDER_REVIEW,
            InquiryStatus.CONTACTED,
            InquiryStatus.QUOTED,
            InquiryStatus.APPROVED,
        ]
        if inquiry.status not in allowed_statuses:
            raise BusinessError(
                f"Cannot convert inquiry with status: {inquiry.status}. "
                f"Allowed statuses: {', '.join(allowed_statuses)}"
            )

        # 4. Get pricing settings
        pricing = await self.settings_service.get_pricing_settings()
        if not pricing:
            raise BusinessError("Pricing settings not configured. Please contact administrator.")

        # 5. Calculate estimated cost
        estimated_cost = data.estimated_cost if data.estimated_cost is not None else Decimal(inquiry.estimated_budget or 0)
        if estimated_cost <= 0:
            raise ValidationError("Estimated cost must be greater than 0")

        # 6. Calculate deposit
        deposit_percent = Decimal(str(pricing.deposit_percent)) / Decimal('100')
        deposit_amount = estimated_cost * deposit_percent

        # 7. Calculate estimated revenue (from settings)
        margin_percent = Decimal(str(pricing.default_margin_percent)) / Decimal('100') if pricing else Decimal('0.3')
        estimated_revenue = estimated_cost * (Decimal('1') + margin_percent)

        # 8. Default duration from settings
        default_duration = int(pricing.default_duration_days) if pricing else 14
        target_delivery = data.project_target_delivery or (
            datetime.now() + timedelta(days=default_duration)
        )

        # 9. Generate project name with fallback
        project_name = data.project_name or (
            f"Project: {inquiry.vehicle_brand or 'Unknown'} "
            f"{inquiry.vehicle_model or 'Model'} - "
            f"{inquiry.customer_name or 'Customer'}"
        )

        # 10. Create project data
        project_data = {
            "name": project_name,
            "customer_name": inquiry.customer_name,
            "customer_phone": inquiry.customer_phone_number,
            "customer_email": inquiry.customer_email,
            "vehicle_brand": inquiry.vehicle_brand,
            "vehicle_model": inquiry.vehicle_model,
            "vehicle_year": inquiry.vehicle_year,
            "vehicle_license_plate": inquiry.vehicle_license_plate,
            "estimated_cost": float(estimated_cost),
            "deposit_amount": float(deposit_amount),
            "estimated_revenue": float(estimated_revenue),
            "project_start_date": data.project_start_date or datetime.now(),
            "project_target_delivery": target_delivery,
            "status": ProjectStatus.ACTIVE,
            "priority": ProjectPriority.MEDIUM,
            "notes": inquiry.project_description,
            "inquiry_id": inquiry_id,
        }

        # 11. Create project
        try:
            project_service = ProjectService(self.db)
            project_create = ProjectCreate(**project_data)
            project = await project_service.create(project_create)
        except Exception as e:
            # Log failed conversion
            await self.repo.add_activity(
                inquiry_id,
                f"Conversion failed: {str(e)}",
                "conversion_failed",
                performed_by="system",
                meta_data={"error": str(e)}
            )
            raise BusinessError(f"Failed to create project: {str(e)}")

        # 12. Update inquiry
        inquiry.status = InquiryStatus.CONVERTED
        inquiry.converted_at = datetime.now()
        inquiry.conversion_rate = Decimal('100')
        inquiry.project_id = project.id

        await self.db.flush()
        await self.db.refresh(inquiry)

        # 13. Log activity
        await self.repo.add_activity(
            inquiry_id,
            f"Converted to project: {project.name}",
            "conversion",
            performed_by="system",
            meta_data={
                "project_id": str(project.id),
                "estimated_cost": float(estimated_cost),
                "deposit_amount": float(deposit_amount),
                "estimated_revenue": float(estimated_revenue)
            }
        )

        # 14. Invalidate cache
        self.invalidate_cache()

        return project

    async def on_project_completed(self, project_id: UUID):
        """
        Callback when project is completed.
        Updates inquiry status to completed.
        
        Args:
            project_id: ID project that was completed
        """
        inquiry = await self.repo.get_by_project_id(project_id)
        if inquiry and inquiry.status != InquiryStatus.COMPLETED:
            await self.update_status(
                inquiry.id,
                InquiryStatus.COMPLETED,
                "Auto-updated: Project completed"
            )

    # ============================================================
    # 4. COST CALCULATION
    # ============================================================

    async def calculate_estimated_cost(
        self,
        project_type: str,
        services: Optional[str] = None,
        desired_finish: Optional[str] = None,
        desired_color: Optional[str] = None
    ) -> int:
        """
        Calculate estimated cost based on project type and services.
        
        Args:
            project_type: Type of project
            services: Services selected
            desired_finish: Finish type
            desired_color: Color preference
        
        Returns:
            Estimated cost in Rupiah
        
        Raises:
            ValidationError: If project type not found
        """
        pricing = await self.settings_service.get_pricing_settings()
        if not pricing:
            return 0

        # Base price by project type
        base_price_map = {
            "warna baru": pricing.paint_base_price,
            "mengembalikan ke warna original": pricing.paint_base_price,
            "perbaikan panel yang rusak": pricing.paint_base_price // 2,
            "restorasi total": pricing.restoration_base_price,
            "butuh konsultasi": pricing.paint_base_price // 4,
        }
        
        # Fallback if project type not found
        base = base_price_map.get(project_type.lower(), pricing.paint_base_price)

        # Additional for custom color
        total = base
        if desired_color and desired_color.lower() not in ['standard', 'original', 'default', 'oem']:
            total += pricing.custom_color_surcharge

        # Additional for custom finish
        if desired_finish and desired_finish.lower() in ['pearl', 'candy', 'metallic']:
            total += pricing.custom_color_surcharge // 2

        # Additional based on services
        if services:
            service_bonus = {
                "full cat ulang": 200000,
                "restorasi": 300000,
                "repaint velk": 150000,
                "repaint rangka": 200000,
                "detailing mesin": 100000,
            }
            
            services_lower = services.lower()
            for key, value in service_bonus.items():
                if key in services_lower:
                    total += value

        # Apply margin
        margin_multiplier = 1 + (float(pricing.default_margin_percent) / 100)
        total = int(total * margin_multiplier)

        # Round to nearest 50,000
        total = ((total + 24999) // 50000) * 50000
        
        return total

    # ============================================================
    # 5. PHOTO MANAGEMENT
    # ============================================================

    async def _save_photo(
        self,
        inquiry_id: UUID,
        photo: UploadFile,
        stage: str,
        is_primary: bool = False
    ) -> CustomerInquiryPhoto:
        """
        Save photo and return photo object.
        
        Args:
            inquiry_id: ID inquiry
            photo: Uploaded photo
            stage: Photo stage
            is_primary: Set as primary
        
        Returns:
            Created photo instance
        
        Raises:
            ValidationError: If file type not allowed
        """
        # Validate extension
        ext = Path(photo.filename).suffix.lower() if photo.filename else '.jpg'
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise ValidationError(
                f"Unsupported file type: {ext}. Allowed: {ALLOWED_IMAGE_EXTENSIONS}"
            )

        # Validate file size
        content = await photo.read()
        if len(content) > MAX_FILE_SIZE:
            raise ValidationError(
                f"File too large: {len(content)} bytes. Max: {MAX_FILE_SIZE} bytes"
            )

        # Generate filename
        filename = f"{uuid4()}{ext}"
        inquiry_folder = UPLOAD_DIR / str(inquiry_id)
        inquiry_folder.mkdir(parents=True, exist_ok=True)

        # Save file
        file_path = inquiry_folder / filename
        with open(file_path, "wb") as f:
            f.write(content)

        # Save relative path
        relative_path = str(file_path.relative_to(UPLOAD_DIR.parent))

        # Create photo record
        photo_obj = await self.repo.add_photo(
            inquiry_id=inquiry_id,
            photo_data={
                "file_path": relative_path,
                "file_name": photo.filename or filename,
                "file_size": len(content),
                "mime_type": photo.content_type,
                "stage": stage,
                "sort_order": 0,
            },
            is_primary=is_primary
        )

        return photo_obj

    async def upload_photos(
        self,
        inquiry_id: UUID,
        photos: List[UploadFile],
        stage: str = "initial"
    ) -> List[CustomerInquiryPhoto]:
        """
        Upload multiple photos.
        
        Args:
            inquiry_id: ID inquiry
            photos: List of photos
            stage: Photo stage
        
        Returns:
            List of uploaded photos
        
        Raises:
            NotFoundError: If inquiry not found
        """
        inquiry = await self.repo.get(inquiry_id)
        if not inquiry:
            raise NotFoundError(f"Inquiry {inquiry_id} not found")

        uploaded = []
        current_photos = await self.repo.get_photos(inquiry_id)
        is_first = len(current_photos) == 0

        for idx, photo in enumerate(photos):
            if photo.filename and photo.filename.strip():
                photo_obj = await self._save_photo(
                    inquiry_id, 
                    photo, 
                    stage, 
                    is_primary=(is_first and idx == 0)
                )
                uploaded.append(photo_obj)

        if uploaded:
            await self.repo.add_activity(
                inquiry_id,
                f"Uploaded {len(uploaded)} photos",
                "photo_upload",
                performed_by="system",
                meta_data={"count": len(uploaded), "stage": stage}
            )

        return uploaded

    async def get_photos(self, inquiry_id: UUID) -> List[CustomerInquiryPhoto]:
        """
        Get all photos for an inquiry.
        
        Args:
            inquiry_id: ID inquiry
        
        Returns:
            List of photos
        """
        return await self.repo.get_photos(inquiry_id)

    async def set_primary_photo(self, photo_id: UUID) -> bool:
        """
        Set a photo as primary.
        
        Args:
            photo_id: ID photo
        
        Returns:
            True if updated
        """
        return await self.repo.set_primary_photo(photo_id)

    async def delete_photo(self, photo_id: UUID) -> bool:
        """
        Delete a photo.
        
        Args:
            photo_id: ID photo
        
        Returns:
            True if deleted
        """
        return await self.repo.delete_photo(photo_id)

    # ============================================================
    # 6. WORKSHOP NOTES MANAGEMENT
    # ============================================================

    async def add_workshop_note(
        self,
        inquiry_id: UUID,
        note: str,
        note_type: str = "internal",
        author: Optional[str] = None,
        is_private: bool = False
    ) -> WorkshopNote:
        """
        Add workshop note.
        
        Args:
            inquiry_id: ID inquiry
            note: Note content
            note_type: Type of note
            author: Author name
            is_private: Private note
        
        Returns:
            Created workshop note
        
        Raises:
            NotFoundError: If inquiry not found
        """
        inquiry = await self.repo.get(inquiry_id)
        if not inquiry:
            raise NotFoundError(f"Inquiry {inquiry_id} not found")

        return await self.repo.add_workshop_note(
            inquiry_id,
            note,
            note_type,
            author or "system",
            is_private
        )

    async def get_workshop_notes(
        self,
        inquiry_id: UUID,
        include_private: bool = False
    ) -> List[WorkshopNote]:
        """
        Get workshop notes.
        
        Args:
            inquiry_id: ID inquiry
            include_private: Include private notes
        
        Returns:
            List of workshop notes
        """
        return await self.repo.get_workshop_notes(inquiry_id, include_private)

    # ============================================================
    # 7. ACTIVITIES MANAGEMENT
    # ============================================================

    async def get_activities(
        self,
        inquiry_id: UUID,
        limit: int = 50
    ) -> List[InquiryActivity]:
        """
        Get inquiry activities.
        
        Args:
            inquiry_id: ID inquiry
            limit: Max activities
        
        Returns:
            List of activities
        """
        return await self.repo.get_activities(inquiry_id, limit)

    # ============================================================
    # 8. STATISTICS
    # ============================================================

    async def get_statistics(self) -> Dict[str, Any]:
        """Get inquiry statistics with caching."""
        now = datetime.now()
        
        # Check cache
        if self._stats_cache and self._stats_cache_time:
            if (now - self._stats_cache_time).seconds < self._cache_ttl:
                return self._stats_cache
        
        # Get fresh data
        data = await self.repo.get_statistics()
        
        # Update cache
        self._stats_cache = data
        self._stats_cache_time = now
        
        return data
    
    def invalidate_cache(self):
        """Invalidate statistics cache."""
        self._stats_cache = None
        self._stats_cache_time = None

    async def get_pending_conversion(self) -> List[CustomerInquiry]:
        """
        Get inquiries ready for conversion to project.
        
        Returns:
            List of inquiries ready for conversion
        """
        return await self.repo.get_pending_conversion()

    # ============================================================
    # 9. FOLLOW-UP MANAGEMENT
    # ============================================================

    async def add_follow_up(
        self,
        inquiry_id: UUID,
        data: InquiryFollowUpCreate
    ) -> InquiryFollowUp:
        """
        Add follow-up to inquiry.
        
        Args:
            inquiry_id: ID inquiry
            data: Follow-up data
        
        Returns:
            Created follow-up
        
        Raises:
            NotFoundError: If inquiry not found
            ValidationError: If validation fails
        """
        inquiry = await self.repo.get(inquiry_id)
        if not inquiry:
            raise NotFoundError(f"Inquiry {inquiry_id} not found")

        if data.scheduled_at < datetime.now() - timedelta(minutes=5):
            raise ValidationError("Scheduled time cannot be in the past")

        return await self.repo.add_follow_up(inquiry_id, data.model_dump())

    async def get_follow_ups(self, inquiry_id: UUID) -> List[InquiryFollowUp]:
        """
        Get all follow-ups for an inquiry.
        
        Args:
            inquiry_id: ID inquiry
        
        Returns:
            List of follow-ups
        """
        return await self.repo.get_follow_ups(inquiry_id)

    async def get_follow_up(self, follow_up_id: UUID) -> Optional[InquiryFollowUp]:
        """
        Get follow-up by ID.
        
        Args:
            follow_up_id: ID follow-up
        
        Returns:
            Follow-up instance or None
        """
        return await self.repo.get_follow_up(follow_up_id)

    async def update_follow_up(
        self,
        follow_up_id: UUID,
        data: InquiryFollowUpUpdate
    ) -> Optional[InquiryFollowUp]:
        """
        Update follow-up.
        
        Args:
            follow_up_id: ID follow-up
            data: Update data
        
        Returns:
            Updated follow-up or None
        """
        return await self.repo.update_follow_up(follow_up_id, data.model_dump(exclude_unset=True))

    async def complete_follow_up(
        self,
        follow_up_id: UUID,
        data: InquiryFollowUpComplete
    ) -> Optional[InquiryFollowUp]:
        """
        Complete follow-up.
        
        Args:
            follow_up_id: ID follow-up
            data: Completion data
        
        Returns:
            Updated follow-up or None
        """
        return await self.repo.complete_follow_up(follow_up_id, data.result, data.note)

    async def delete_follow_up(self, follow_up_id: UUID) -> bool:
        """
        Delete follow-up.
        
        Args:
            follow_up_id: ID follow-up
        
        Returns:
            True if deleted
        """
        return await self.repo.delete_follow_up(follow_up_id)

    async def process_pending_follow_ups(self) -> List[InquiryFollowUp]:
        """
        Process pending follow-ups (mark as overdue if missed).
        
        Returns:
            List of processed follow-ups
        """
        return await self.repo.process_pending_follow_ups()

    async def send_follow_up_reminders(self) -> List[InquiryFollowUp]:
        """
        Send reminders for upcoming follow-ups.
        
        Returns:
            List of reminders sent
        """
        return await self.repo.send_follow_up_reminders()

    async def get_follow_ups_by_assignee(self, assigned_to: str) -> List[InquiryFollowUp]:
        """
        Get follow-ups assigned to a specific person.
        
        Args:
            assigned_to: Name of assignee
        
        Returns:
            List of follow-ups
        """
        return await self.repo.get_follow_ups_by_assignee(assigned_to)

    # ============================================================
    # 10. PAYMENT MANAGEMENT
    # ============================================================

    async def add_payment(
        self,
        inquiry_id: UUID,
        payment_type: str,
        amount: Decimal,
        payment_method: Optional[str] = None,
        notes: Optional[str] = None
    ) -> InquiryPayment:
        """
        Add payment to inquiry.
        
        Args:
            inquiry_id: ID inquiry
            payment_type: Type of payment
            amount: Payment amount
            payment_method: Payment method
            notes: Payment notes
        
        Returns:
            Created payment
        
        Raises:
            NotFoundError: If inquiry not found
            ValidationError: If validation fails
        """
        inquiry = await self.repo.get(inquiry_id)
        if not inquiry:
            raise NotFoundError(f"Inquiry {inquiry_id} not found")

        if amount <= 0:
            raise ValidationError("Payment amount must be greater than 0")

        payment = InquiryPayment(
            inquiry_id=inquiry_id,
            payment_type=payment_type,
            amount=amount,
            status="pending",
            payment_method=payment_method,
            notes=notes
        )
        self.db.add(payment)
        await self.db.flush()
        await self.db.refresh(payment)

        await self.repo.add_activity(
            inquiry_id,
            f"Payment added: {payment_type} - Rp {float(amount):,.2f}",
            "payment_add",
            performed_by="system"
        )

        return payment

    async def get_payments(self, inquiry_id: UUID) -> List[InquiryPayment]:
        """
        Get all payments for an inquiry.
        
        Args:
            inquiry_id: ID inquiry
        
        Returns:
            List of payments
        """
        return await self.repo.get_payments(inquiry_id)

    # ============================================================
    # 11. INVOICE MANAGEMENT
    # ============================================================

    async def generate_invoice(
        self,
        inquiry_id: UUID,
        amount: Decimal,
        due_date: Optional[datetime] = None,
        notes: Optional[str] = None
    ) -> InquiryInvoice:
        """
        Generate invoice for inquiry.
        
        Args:
            inquiry_id: ID inquiry
            amount: Invoice amount
            due_date: Due date
            notes: Invoice notes
        
        Returns:
            Created invoice
        
        Raises:
            NotFoundError: If inquiry not found
            ValidationError: If validation fails
        """
        inquiry = await self.repo.get(inquiry_id)
        if not inquiry:
            raise NotFoundError(f"Inquiry {inquiry_id} not found")

        if amount <= 0:
            raise ValidationError("Invoice amount must be greater than 0")

        # Generate invoice number
        invoice_number = f"INV-{datetime.now().strftime('%Y%m')}-{uuid4().hex[:6].upper()}"

        invoice = InquiryInvoice(
            inquiry_id=inquiry_id,
            invoice_number=invoice_number,
            amount=amount,
            status="draft",
            due_date=due_date or (datetime.now() + timedelta(days=14)),
            notes=notes
        )
        self.db.add(invoice)
        await self.db.flush()
        await self.db.refresh(invoice)

        await self.repo.add_activity(
            inquiry_id,
            f"Invoice generated: {invoice_number} - Rp {float(amount):,.2f}",
            "invoice_generate",
            performed_by="system"
        )

        return invoice

    async def get_invoices(self, inquiry_id: UUID) -> List[InquiryInvoice]:
        """
        Get all invoices for an inquiry.
        
        Args:
            inquiry_id: ID inquiry
        
        Returns:
            List of invoices
        """
        return await self.repo.get_invoices(inquiry_id)

    # ============================================================
    # 12. BULK OPERATIONS
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
            Number of inquiries updated
        
        Raises:
            ValidationError: If validation fails
        """
        valid_statuses = [e.value for e in InquiryStatus]
        if new_status not in valid_statuses:
            raise ValidationError(f"Invalid inquiry status: {new_status}")

        return await self.repo.bulk_update_status(inquiry_ids, new_status, note)

    # ============================================================
    # 13. REPORTING
    # ============================================================

    async def get_aging_inquiries(self, days: int = 30) -> List[CustomerInquiry]:
        """
        Get aging inquiries (not updated for N days).
        
        Args:
            days: Number of days threshold
        
        Returns:
            List of aging inquiries
        """
        return await self.repo.get_aging_inquiries(days)

    async def get_conversion_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get conversion report for a date range.
        
        Args:
            start_date: Start date
            end_date: End date
        
        Returns:
            Conversion report
        """
        # Use default date range if not provided
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Get inquiries in date range
        inquiries = await self.repo.get_by_date_range(start_date, end_date)
        total = len(inquiries)

        if total == 0:
            return {
                "total": 0,
                "converted": 0,
                "rejected": 0,
                "pending": 0,
                "conversion_rate": 0,
                "average_response_time": 0
            }

        # Calculate metrics
        converted = sum(1 for i in inquiries if i.status == InquiryStatus.CONVERTED)
        rejected = sum(1 for i in inquiries if i.status == InquiryStatus.REJECTED)
        pending = total - converted - rejected

        # Calculate average response time (to first contact)
        response_times = []
        for i in inquiries:
            if i.contacted_at and i.created_at:
                delta = i.contacted_at - i.created_at
                response_times.append(delta.total_seconds() / 3600)  # hours

        avg_response_time = round(sum(response_times) / len(response_times), 2) if response_times else 0

        return {
            "total": total,
            "converted": converted,
            "rejected": rejected,
            "pending": pending,
            "conversion_rate": round((converted / total * 100), 2),
            "average_response_time": avg_response_time,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }

    # ============================================================
    # 14. WHATSAPP MESSAGE GENERATION
    # ============================================================

    async def generate_whatsapp_message(self, inquiry_id: UUID) -> Dict[str, Any]:
        """
        Generate WhatsApp message using template from settings.
        
        Args:
            inquiry_id: ID inquiry
        
        Returns:
            WhatsApp message data
        
        Raises:
            NotFoundError: If inquiry not found
        """
        inquiry = await self.repo.get(inquiry_id)
        if not inquiry:
            raise NotFoundError(f"Inquiry {inquiry_id} not found")

        # Get template from settings
        default_template = await self.settings_service.get_default_whatsapp_template()

        if default_template:
            # Render template with data
            data = {
                "customer_name": inquiry.customer_name or "Customer",
                "vehicle": f"{inquiry.vehicle_brand} {inquiry.vehicle_model}".strip() or "Vehicle",
                "project_type": inquiry.project_type or "Project",
                "phone": inquiry.customer_phone_number or "",
                "inquiry_id": str(inquiry.id)[:8],
            }
            message = default_template.render(data)
        else:
            # Fallback template
            message = (
                f"Halo {inquiry.customer_name},\n\n"
                f"Kami dari NOCTRA AUTOWORKS ingin menindaklanjuti inquiry Anda mengenai:\n"
                f"• Kendaraan: {inquiry.vehicle_brand} {inquiry.vehicle_model}\n"
                f"• Tipe Proyek: {inquiry.project_type}\n\n"
                f"Ada yang bisa kami bantu? 😊"
            )

        return {
            "message": message,
            "phone": inquiry.customer_phone_number,
            "template_id": str(default_template.id) if default_template else None
        }