# modules/inquiry/router.py
import csv
from decimal import Decimal
from uuid import UUID
from datetime import datetime, timedelta
from typing import List, Optional
from io import StringIO

from fastapi import APIRouter, HTTPException, status, File, UploadFile, Body, Query, Depends
from fastapi.responses import StreamingResponse

from modules.settings.services import SettingsService
from core.database import get_db
from core.base import BaseResponse, PaginatedResponse
from core.websocket import manager
from core.constants import InquiryStatus
from core.dependencies import success_response, get_service
from core.exceptions import NotFoundError, ValidationError, BusinessError
from modules.inquiry.schemas import (
    CustomerInquiryCreate,
    CustomerInquiryUpdate,
    CustomerInquiryResponse,
    CustomerInquirySummary,
    InquiryFollowUpComplete,
    InquiryFollowUpCreate,
    InquiryFollowUpUpdate,
    InquiryStatusUpdate,
    InquiryReject,
    InquirySendQuotation,
    InquiryConvertToProject,
    InquiryClose,
    NoteCreate,
    InquiryFilterParams,
    InquirySortParams,
    InquiryBulkStatusUpdate,
    InquiryBulkDelete,
    InquiryExportParams,
    WhatsAppMessageResponse,
)
from modules.inquiry.services import InquiryService


inquiry_router = APIRouter(
    prefix="/api/inquiries",
    tags=["Customer Inquiries"]
)


# ============================================================
# 1. LIST & STATISTICS ENDPOINTS
# ============================================================

@inquiry_router.get("/", response_model=PaginatedResponse[CustomerInquirySummary])
async def list_inquiries(
    status: Optional[str] = Query(None, description="Filter by inquiry status"),
    search: Optional[str] = Query(None, description="Search by name, phone, brand, model, plate"),
    brand: Optional[str] = Query(None, description="Filter by vehicle brand"),
    project_status: Optional[str] = Query(None, description="Filter by project status"),
    has_project: Optional[bool] = Query(None, description="Filter by project existence (true/false)"),
    include_deleted: bool = Query(False, description="Include soft-deleted records"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    service: InquiryService = Depends(get_service(InquiryService))
):
    """
    List all inquiries with filters.
    
    **Status values**: new, under_review, contacted, quoted, approved, converted, rejected, closed, completed
    **Project status values**: draft, active, in_progress, on_hold, completed, cancelled, preparation, painting, assembly
    """
    inquiries, total = await service.list_inquiries(
        status=status, search=search, brand=brand,
        project_status=project_status, has_project=has_project,
        limit=limit, offset=offset,
        include_deleted=include_deleted
    )

    total_pages = (total + limit - 1) // limit if total > 0 else 0
    current_page = (offset // limit) + 1

    return PaginatedResponse(
        success=True, message="Inquiries retrieved successfully",
        data=[CustomerInquirySummary.model_validate(i).model_dump() for i in inquiries],
        total=total, page=current_page,
        page_size=limit, total_pages=total_pages
    )


@inquiry_router.get("/statistics", response_model=BaseResponse, description="""
    Get inquiry statistics for dashboard.
    
    Returns:
        - Total inquiries
        - By status
        - By brand
        - By source
        - Conversion rate
        - Recent inquiries
    """)
async def get_statistics(service: InquiryService = Depends(get_service(InquiryService))):

    data = await service.get_statistics()
    
    # Convert recent inquiries to summary
    recent_data = []
    for inquiry in data.get('recent', []):
        if hasattr(inquiry, 'model_dump'):
            recent_data.append(CustomerInquirySummary.model_validate(inquiry).model_dump())
        else:
            recent_data.append(inquiry)
    
    data['recent'] = recent_data
    
    return success_response(data, message="Statistics retrieved successfully")


@inquiry_router.get("/pending-conversion", response_model=BaseResponse)
async def get_pending_conversion(service: InquiryService = Depends(get_service(InquiryService))):
    """
    Get inquiries ready for conversion to project.
    
    Returns inquiries with status:
    - quoted
    - contacted
    - approved
    """
    inquiries = await service.get_pending_conversion()
    return success_response(
        [CustomerInquirySummary.model_validate(i).model_dump() for i in inquiries],
        message="Pending conversion inquiries retrieved successfully"
    )


@inquiry_router.get("/aging", response_model=BaseResponse, description="""
    Get aging inquiries that haven't been updated for N days.
    
    Only returns inquiries with status:
    - new
    - under_review
    - contacted
    """)
async def get_aging_inquiries(days: int = Query(30, ge=7, le=90, description="Days threshold for aging"), service: InquiryService = Depends(get_service(InquiryService))):
    inquiries = await service.get_aging_inquiries(days)
    return success_response(
        [CustomerInquirySummary.model_validate(i).model_dump() for i in inquiries],
        message=f"Aging inquiries ({days}+ days) retrieved successfully"
    )


@inquiry_router.get("/conversion-report", response_model=BaseResponse, description="""
    Get conversion report for a date range.
    
    Returns:
        - Total inquiries
        - Converted count
        - Rejected count
        - Pending count
        - Conversion rate
        - Average response time
    """)
async def get_conversion_report(start_date: Optional[datetime] = Query(None, description="Start date (ISO format)"), end_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
    service: InquiryService = Depends(get_service(InquiryService))):
    
    report = await service.get_conversion_report(start_date, end_date)
    return success_response(report, message="Conversion report retrieved successfully")


# ============================================================
# 2. DETAIL ENDPOINTS
# ============================================================

@inquiry_router.get("/{inquiry_id}", response_model=BaseResponse, description="""
    Get inquiry detail with all related data.
    
    Includes:
    - Customer info
    - Vehicle info
    - Project info
    - Photos
    - Activities
    - Workshop notes
    - Project (if converted)
    - Payments
    """)
async def get_inquiry(inquiry_id: UUID, service: InquiryService = Depends(get_service(InquiryService))):
    inquiry = await service.get_inquiry(inquiry_id)
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    
    return success_response(
        CustomerInquiryResponse.model_validate(inquiry).model_dump(),
        message="Inquiry retrieved successfully"
    )


# ============================================================
# 3. CREATE ENDPOINT
# ============================================================

@inquiry_router.post("/", response_model=BaseResponse, status_code=status.HTTP_201_CREATED, description="""
    Create a new inquiry.
    
    All fields are validated against the schema.
    Phone number must be in Indonesian format.
    Project type must be valid from settings.
    """)
async def create_inquiry(request: CustomerInquiryCreate, service: InquiryService = Depends(get_service(InquiryService))):
    try:
        inquiry = await service.create_inquiry(request)

        # Broadcast to all connected admins
        await manager.broadcast({
            "type": "new_inquiry",
            "data": {
                "id": str(inquiry.id),
                "customer_name": inquiry.customer_name,
                "vehicle": f"{inquiry.vehicle_brand} {inquiry.vehicle_model}",
                "created_at": inquiry.created_at.isoformat()
            }
        })

        return success_response(
            {"id": str(inquiry.id)},
            message="Inquiry created successfully"
        )

    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ============================================================
# 4. UPDATE ENDPOINTS
# ============================================================

@inquiry_router.patch("/{inquiry_id}", response_model=BaseResponse, description="""
    Update inquiry.
    
    All fields are optional. Only provided fields will be updated.
    """)
async def update_inquiry(inquiry_id: UUID, request: CustomerInquiryUpdate, service: InquiryService = Depends(get_service(InquiryService))):
    try:
        inquiry = await service.update_inquiry(inquiry_id, request)
        if not inquiry:
            raise HTTPException(status_code=404, detail="Inquiry not found")

        return success_response(
            {"id": str(inquiry_id)},
            message="Inquiry updated successfully"
        )
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@inquiry_router.delete("/{inquiry_id}", response_model=BaseResponse, description="""
    Delete an inquiry.
    
    By default, performs soft delete (recoverable).
    Use permanent=true for hard delete (cannot be undone).
    """)
async def delete_inquiry(inquiry_id: UUID, permanent: bool = Query(False, description="Permanent delete (cannot be undone)"), service: InquiryService = Depends(get_service(InquiryService))):
    try:
        deleted = await service.delete_inquiry(inquiry_id, permanent)
        if not deleted:
            raise HTTPException(status_code=404, detail="Inquiry not found")

        return success_response(
            {"id": str(inquiry_id)},
            message=f"Inquiry {'' if permanent else 'soft '}deleted successfully"
        )
    except BusinessError as e:
        await service.db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ============================================================
# 5. STATUS MANAGEMENT ENDPOINTS
# ============================================================

@inquiry_router.patch("/{inquiry_id}/status", response_model=BaseResponse, description="""
    Update inquiry status with transition validation.
    
    **Allowed transitions**:
    - new → under_review, contacted, rejected
    - under_review → contacted, quoted, rejected
    - contacted → quoted, rejected
    - quoted → approved, rejected
    - approved → converted, rejected
    - converted → completed, rejected
    - rejected → closed
    - closed → (final)
    - completed → (final)
    """)
async def update_status(inquiry_id: UUID, request: InquiryStatusUpdate, service: InquiryService = Depends(get_service(InquiryService))):
    try:
        success = await service.update_status(inquiry_id, request.status, request.note)
        if not success:
            raise HTTPException(status_code=404, detail="Inquiry not found")

        return success_response(
            {"id": str(inquiry_id), "status": request.status},
            message=f"Status updated to {request.status}"
        )
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@inquiry_router.post("/{inquiry_id}/contact", response_model=BaseResponse, description="""
    Mark inquiry as contacted.
    
    This will change status to 'contacted' if transition is allowed.
    """)
async def contact_customer(inquiry_id: UUID, note: Optional[str] = Body(None, embed=True), service: InquiryService = Depends(get_service(InquiryService))):
    try:
        success = await service.contact_customer(inquiry_id, note)
        if not success:
            raise HTTPException(status_code=404, detail="Inquiry not found")

        return success_response(
            {"id": str(inquiry_id), "status": "contacted"},
            message="Customer contacted"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@inquiry_router.post("/{inquiry_id}/reject", response_model=BaseResponse, description="""
    Reject inquiry with reason.
    
    This will change status to 'rejected' if transition is allowed.
    """)
async def reject_inquiry(inquiry_id: UUID, request: InquiryReject, service: InquiryService = Depends(get_service(InquiryService))):
    try:
        success = await service.reject_inquiry(inquiry_id, request.reason)
        if not success:
            raise HTTPException(status_code=404, detail="Inquiry not found")

        return success_response(
            {"id": str(inquiry_id), "status": "rejected"},
            message="Inquiry rejected"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@inquiry_router.post("/{inquiry_id}/quote", 
                     response_model=BaseResponse, 
                     description="""
    Send quotation to customer.
    
    This will change status to 'quoted' if transition is allowed.
    """)
async def send_quote(inquiry_id: UUID, request: InquirySendQuotation, service: InquiryService = Depends(get_service(InquiryService))):
    try:
        success = await service.send_quote(inquiry_id, request.estimated_cost, request.notes)
        if not success:
            raise HTTPException(status_code=404, detail="Inquiry not found")

        return success_response(
            {"id": str(inquiry_id), "status": "quoted"},
            message=f"Quotation sent: Rp {float(request.estimated_cost):,.2f}"
        )
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@inquiry_router.post("/{inquiry_id}/close", response_model=BaseResponse)
async def close_inquiry(inquiry_id: UUID, request: InquiryClose, service: InquiryService = Depends(get_service(InquiryService))):
    """
    Close an inquiry.
    
    This will change status to 'closed' if transition is allowed.
    """
    try:
        success = await service.close_inquiry(inquiry_id, request.reason, request.note)
        if not success:
            raise HTTPException(status_code=404, detail="Inquiry not found")

        return success_response(
            {"id": str(inquiry_id), "status": "closed"},
            message="Inquiry closed"
        )
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# 6. CONVERSION ENDPOINT
# ============================================================

@inquiry_router.post("/{inquiry_id}/convert-to-project", response_model=BaseResponse, status_code=status.HTTP_201_CREATED, description="""
    Convert inquiry to project.
    
    This will:
    1. Create a new project
    2. Link the inquiry to the project
    3. Update inquiry status to 'converted'
    4. Calculate deposit based on settings
    """)
async def convert_to_project(inquiry_id: UUID, request: InquiryConvertToProject, service: InquiryService = Depends(get_service(InquiryService))):
    try:
        project = await service.convert_to_project(inquiry_id, request)

        return success_response(
            {"id": str(project.id), "inquiry_id": str(inquiry_id)},
            message=f"Successfully converted inquiry to project: {project.name}"
        )
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessError as e:
        await service.db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ============================================================
# 7. CALCULATION ENDPOINT
# ============================================================

@inquiry_router.post("/calculate-cost", response_model=BaseResponse, description="""
    Calculate estimated cost based on project type and services.
    
    Returns estimated cost in Rupiah.
    """)
async def calculate_estimated_cost(
    project_type: str = Body(..., embed=True, description="Project type"),
    services: Optional[str] = Body(None, embed=True, description="Services selected"),
    desired_finish: Optional[str] = Body(None, embed=True, description="Desired finish"),
    desired_color: Optional[str] = Body(None, embed=True, description="Desired color"),
    service: InquiryService = Depends(get_service(InquiryService))
):
    try:
        cost = await service.calculate_estimated_cost(
            project_type=project_type,
            services=services,
            desired_finish=desired_finish,
            desired_color=desired_color
        )
        
        return success_response(
            {
                "estimated_cost": cost,
                "formatted": f"Rp {cost:,.2f}"
            },
            message="Estimated cost calculated successfully"
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ============================================================
# 8. WORKSHOP NOTES ENDPOINTS
# ============================================================

@inquiry_router.post("/{inquiry_id}/notes", response_model=BaseResponse, description="""
    Add workshop note to inquiry.
    
    Note types: internal, customer, rejection, quotation, follow_up, general
    """)
async def add_workshop_note(inquiry_id: UUID, request: NoteCreate, service: InquiryService = Depends(get_service(InquiryService))):
    try:
        note = await service.add_workshop_note(
            inquiry_id,
            request.note,
            request.note_type,
            "system",
            request.is_private
        )

        return success_response(
            {"id": str(note.id)},
            message="Workshop note added"
        )
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@inquiry_router.get("/{inquiry_id}/notes", response_model=BaseResponse, description="""
    Get all workshop notes for inquiry.
    """)
async def get_workshop_notes(inquiry_id: UUID, include_private: bool = Query(False, description="Include private notes"), service: InquiryService = Depends(get_service(InquiryService))):
    notes = await service.get_workshop_notes(inquiry_id, include_private)
    return success_response([
        {
            "id": str(n.id),
            "note": n.note,
            "note_type": n.note_type,
            "author": n.author,
            "is_private": n.is_private,
            "created_at": n.created_at.isoformat() if n.created_at else None,
            "updated_at": n.updated_at.isoformat() if n.updated_at else None
        }
        for n in notes
    ], message="Workshop notes retrieved successfully")


# ============================================================
# 9. PHOTO ENDPOINTS
# ============================================================

@inquiry_router.post("/{inquiry_id}/photos", response_model=BaseResponse, description="""
    Upload photos for inquiry.
    
    Supported formats: jpg, jpeg, png, webp, gif, bmp
    Max file size: 10MB per photo
    Max photos: 10 per request
    """)
async def upload_photos(
    inquiry_id: UUID,
    photos: List[UploadFile] = File(..., max_length=10_000_000, description="Photos to upload"),
    stage: str = Query("initial", description="Photo stage (initial, progress, final)"),
    service: InquiryService = Depends(get_service(InquiryService))
):
    try:
        # Limit photos to 10
        if len(photos) > 10:
            raise ValidationError("Maximum 10 photos per upload")
        
        uploaded = await service.upload_photos(inquiry_id, photos, stage)

        return success_response(
            {
                "uploaded": [
                    {
                        "id": str(p.id),
                        "file_path": p.file_path,
                        "file_name": p.file_name
                    } for p in uploaded
                ],
                "count": len(uploaded)
            },
            message=f"Uploaded {len(uploaded)} photos"
        )
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@inquiry_router.get("/{inquiry_id}/photos", response_model=BaseResponse)
async def get_photos(
    inquiry_id: UUID,
    service: InquiryService = Depends(get_service(InquiryService))
):
    """
    Get all photos for inquiry.
    """
    photos = await service.get_photos(inquiry_id)
    return success_response([
        {
            "id": str(p.id),
            "file_path": p.file_path,
            "file_name": p.file_name,
            "file_size": p.file_size,
            "mime_type": p.mime_type,
            "stage": p.stage,
            "is_primary": p.is_primary,
            "sort_order": p.sort_order,
            "created_at": p.created_at.isoformat() if p.created_at else None
        }
        for p in photos
    ], message="Photos retrieved successfully")


@inquiry_router.post("/photos/{photo_id}/set-primary", response_model=BaseResponse)
async def set_primary_photo(
    photo_id: UUID,
    service: InquiryService = Depends(get_service(InquiryService))
):
    """
    Set a photo as primary.
    """
    try:
        result = await service.set_primary_photo(photo_id)
        if not result:
            raise HTTPException(status_code=404, detail="Photo not found")

        return success_response(
            {"id": str(photo_id)},
            message="Primary photo updated"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@inquiry_router.delete("/photos/{photo_id}", response_model=BaseResponse)
async def delete_photo(
    photo_id: UUID,
    service: InquiryService = Depends(get_service(InquiryService))
):
    """
    Delete a photo.
    """
    try:
        deleted = await service.delete_photo(photo_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Photo not found")

        return success_response(
            {"id": str(photo_id)},
            message="Photo deleted"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# 10. ACTIVITY ENDPOINTS
# ============================================================

@inquiry_router.get("/{inquiry_id}/activities", response_model=BaseResponse)
async def get_activities(
    inquiry_id: UUID,
    limit: int = Query(50, ge=1, le=200, description="Max activities to return"),
    service: InquiryService = Depends(get_service(InquiryService))
):
    """
    Get all activities for inquiry.
    """
    activities = await service.get_activities(inquiry_id, limit)
    return success_response([
        {
            "id": str(a.id),
            "activity": a.activity,
            "activity_type": a.activity_type,
            "performed_by": a.performed_by,
            "meta_data": a.meta_data,
            "created_at": a.created_at.isoformat() if a.created_at else None
        }
        for a in activities
    ], message="Activities retrieved successfully")


# ============================================================
# 11. FOLLOW-UP ENDPOINTS
# ============================================================

@inquiry_router.post("/{inquiry_id}/follow-ups", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def add_follow_up(
    inquiry_id: UUID,
    request: InquiryFollowUpCreate,
    service: InquiryService = Depends(get_service(InquiryService))
):
    """
    Add follow-up to inquiry.
    """
    try:
        follow_up = await service.add_follow_up(inquiry_id, request)

        return success_response(
            {"id": str(follow_up.id)},
            message="Follow-up added successfully"
        )
    except (NotFoundError, ValidationError) as e:
        await service.db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@inquiry_router.get("/{inquiry_id}/follow-ups", response_model=BaseResponse)
async def get_follow_ups(
    inquiry_id: UUID,
    service: InquiryService = Depends(get_service(InquiryService))
):
    """
    Get all follow-ups for an inquiry.
    """
    follow_ups = await service.get_follow_ups(inquiry_id)
    return success_response(
        [
            {
                "id": str(f.id),
                "scheduled_at": f.scheduled_at.isoformat(),
                "performed_at": f.performed_at.isoformat() if f.performed_at else None,
                "status": f.status,
                "note": f.note,
                "result": f.result,
                "assigned_to": f.assigned_to,
                "is_overdue": f.is_overdue,
                "created_at": f.created_at.isoformat(),
                "updated_at": f.updated_at.isoformat() if f.updated_at else None
            }
            for f in follow_ups
        ],
        message="Follow-ups retrieved successfully"
    )


@inquiry_router.patch("/follow-ups/{follow_up_id}", response_model=BaseResponse)
async def update_follow_up(
    follow_up_id: UUID,
    request: InquiryFollowUpUpdate,
    service: InquiryService = Depends(get_service(InquiryService))
):
    """
    Update follow-up.
    """
    try:
        follow_up = await service.update_follow_up(follow_up_id, request)
        if not follow_up:
            raise HTTPException(status_code=404, detail="Follow-up not found")

        return success_response(
            {"id": str(follow_up.id)},
            message="Follow-up updated successfully"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@inquiry_router.post("/follow-ups/{follow_up_id}/complete", response_model=BaseResponse)
async def complete_follow_up(
    follow_up_id: UUID,
    request: InquiryFollowUpComplete,
    service: InquiryService = Depends(get_service(InquiryService))
):
    """
    Complete follow-up.
    """
    try:
        follow_up = await service.complete_follow_up(follow_up_id, request)
        if not follow_up:
            raise HTTPException(status_code=404, detail="Follow-up not found")

        return success_response(
            {"id": str(follow_up.id), "status": "done"},
            message="Follow-up completed successfully"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@inquiry_router.delete("/follow-ups/{follow_up_id}", response_model=BaseResponse)
async def delete_follow_up(
    follow_up_id: UUID,
    service: InquiryService = Depends(get_service(InquiryService))
):
    """
    Delete follow-up.
    """
    try:
        deleted = await service.delete_follow_up(follow_up_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Follow-up not found")

        return success_response(
            {"id": str(follow_up_id)},
            message="Follow-up deleted successfully"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@inquiry_router.get("/follow-ups/pending", response_model=BaseResponse)
async def get_pending_follow_ups(
    service: InquiryService = Depends(get_service(InquiryService))
):
    """
    Get all pending follow-ups (system-wide).
    """
    follow_ups = await service.repo.get_pending_follow_ups()
    return success_response(
        [
            {
                "id": str(f.id),
                "inquiry_id": str(f.inquiry_id),
                "customer_name": f.inquiry.customer_name if f.inquiry else "Unknown",
                "scheduled_at": f.scheduled_at.isoformat(),
                "assigned_to": f.assigned_to,
                "note": f.note,
                "is_overdue": f.is_overdue
            }
            for f in follow_ups
        ],
        message="Pending follow-ups retrieved successfully"
    )


@inquiry_router.post("/follow-ups/process", response_model=BaseResponse)
async def process_follow_ups(
    service: InquiryService = Depends(get_service(InquiryService))
):
    """
    Process pending follow-ups (mark overdue).
    """
    try:
        processed = await service.process_pending_follow_ups()

        return success_response(
            {"processed": len(processed)},
            message=f"Processed {len(processed)} follow-ups"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@inquiry_router.post("/follow-ups/send-reminders", response_model=BaseResponse)
async def send_follow_up_reminders(
    service: InquiryService = Depends(get_service(InquiryService))
):
    """
    Send reminders for upcoming follow-ups.
    """
    try:
        sent = await service.send_follow_up_reminders()

        return success_response(
            {"sent": len(sent)},
            message=f"Sent {len(sent)} reminders"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@inquiry_router.get("/follow-ups/by-assignee/{assignee}", response_model=BaseResponse)
async def get_follow_ups_by_assignee(
    assignee: str,
    service: InquiryService = Depends(get_service(InquiryService))
):
    """
    Get follow-ups assigned to a specific person.
    """
    follow_ups = await service.get_follow_ups_by_assignee(assignee)
    return success_response(
        [
            {
                "id": str(f.id),
                "inquiry_id": str(f.inquiry_id),
                "customer_name": f.inquiry.customer_name if f.inquiry else "Unknown",
                "scheduled_at": f.scheduled_at.isoformat(),
                "note": f.note,
                "is_overdue": f.is_overdue
            }
            for f in follow_ups
        ],
        message=f"Follow-ups assigned to {assignee} retrieved successfully"
    )


# ============================================================
# 12. PAYMENT ENDPOINTS
# ============================================================

@inquiry_router.post("/{inquiry_id}/payments", response_model=BaseResponse)
async def add_payment(
    inquiry_id: UUID,
    payment_type: str = Body(..., description="Type: deposit, payment, refund"),
    amount: Decimal = Body(..., gt=0, description="Payment amount"),
    payment_method: Optional[str] = Body(None, description="Method: cash, bank_transfer, credit_card, e_wallet, qris"),
    notes: Optional[str] = Body(None, description="Payment notes"),
    service: InquiryService = Depends(get_service(InquiryService))
):
    """
    Add payment to inquiry.
    """
    try:
        payment = await service.add_payment(
            inquiry_id=inquiry_id,
            payment_type=payment_type,
            amount=amount,
            payment_method=payment_method,
            notes=notes
        )

        return success_response(
            {"id": str(payment.id)},
            message=f"Payment added: {payment_type} - Rp {float(amount):,.2f}"
        )
    except (NotFoundError, ValidationError) as e:
        await service.db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@inquiry_router.get("/{inquiry_id}/payments", response_model=BaseResponse)
async def get_payments(
    inquiry_id: UUID,
    service: InquiryService = Depends(get_service(InquiryService))
):
    """
    Get all payments for an inquiry.
    """
    payments = await service.get_payments(inquiry_id)
    return success_response(
        [
            {
                "id": str(p.id),
                "payment_type": p.payment_type,
                "amount": float(p.amount),
                "status": p.status,
                "payment_method": p.payment_method,
                "paid_at": p.paid_at.isoformat() if p.paid_at else None,
                "reference": p.reference,
                "notes": p.notes,
                "created_at": p.created_at.isoformat() if p.created_at else None
            }
            for p in payments
        ],
        message="Payments retrieved successfully"
    )


# ============================================================
# 13. INVOICE ENDPOINTS
# ============================================================

@inquiry_router.post("/{inquiry_id}/invoices", response_model=BaseResponse)
async def generate_invoice(
    inquiry_id: UUID,
    amount: Decimal = Body(..., gt=0, description="Invoice amount"),
    due_date: Optional[datetime] = Body(None, description="Due date"),
    notes: Optional[str] = Body(None, description="Invoice notes"),
    service: InquiryService = Depends(get_service(InquiryService))
):
    """
    Generate invoice for inquiry.
    """
    try:
        invoice = await service.generate_invoice(
            inquiry_id=inquiry_id,
            amount=amount,
            due_date=due_date,
            notes=notes
        )

        return success_response(
            {
                "id": str(invoice.id),
                "invoice_number": invoice.invoice_number
            },
            message=f"Invoice generated: {invoice.invoice_number}"
        )
    except (NotFoundError, ValidationError) as e:
        await service.db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@inquiry_router.get("/{inquiry_id}/invoices", response_model=BaseResponse)
async def get_invoices(
    inquiry_id: UUID,
    service: InquiryService = Depends(get_service(InquiryService))
):
    """
    Get all invoices for an inquiry.
    """
    invoices = await service.get_invoices(inquiry_id)
    return success_response(
        [
            {
                "id": str(i.id),
                "invoice_number": i.invoice_number,
                "amount": float(i.amount),
                "status": i.status,
                "issued_at": i.issued_at.isoformat() if i.issued_at else None,
                "due_date": i.due_date.isoformat() if i.due_date else None,
                "paid_at": i.paid_at.isoformat() if i.paid_at else None,
                "file_path": i.file_path,
                "notes": i.notes,
                "created_at": i.created_at.isoformat() if i.created_at else None
            }
            for i in invoices
        ],
        message="Invoices retrieved successfully"
    )


# ============================================================
# 14. WHATSAPP ENDPOINT
# ============================================================

@inquiry_router.get("/{inquiry_id}/whatsapp-message", response_model=BaseResponse)
async def get_whatsapp_message(
    inquiry_id: UUID,
    service: InquiryService = Depends(get_service(InquiryService)),
    settings_service: SettingsService = Depends(get_service(SettingsService))
):
    """
    Generate WhatsApp message using template from settings.
    """
    try:
        inquiry = await service.get_inquiry(inquiry_id)
        if not inquiry:
            raise HTTPException(status_code=404, detail="Inquiry not found")

        result = await service.generate_whatsapp_message(inquiry_id)
        
        return success_response(
            {
                "message": result["message"],
                "phone": result["phone"],
                "template_id": result["template_id"],
                "whatsapp_url": f"https://wa.me/{result['phone'].replace('+', '').replace(' ', '').replace('-', '')}?text={result['message']}"
            },
            message="WhatsApp message generated successfully"
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ============================================================
# 15. BULK OPERATIONS ENDPOINTS
# ============================================================

@inquiry_router.post("/bulk/status", response_model=BaseResponse)
async def bulk_update_status(
    request: InquiryBulkStatusUpdate,
    service: InquiryService = Depends(get_service(InquiryService))
):
    """
    Bulk update status for multiple inquiries.
    """
    try:
        updated = await service.bulk_update_status(
            inquiry_ids=request.inquiry_ids,
            new_status=request.status,
            note=request.note
        )

        return success_response(
            {"updated": updated, "total": len(request.inquiry_ids)},
            message=f"Updated {updated} inquiries to {request.status}"
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@inquiry_router.post("/bulk/delete", response_model=BaseResponse)
async def bulk_delete_inquiries(
    request: InquiryBulkDelete,
    service: InquiryService = Depends(get_service(InquiryService))
):
    """
    Bulk delete inquiries.
    
    By default performs soft delete. Use permanent=true for hard delete.
    """
    try:
        deleted = 0
        for inquiry_id in request.inquiry_ids:
            try:
                if await service.delete_inquiry(inquiry_id, request.permanent):
                    deleted += 1
            except BusinessError:
                # Skip inquiries that cannot be deleted
                continue

        return success_response(
            {"deleted": deleted, "total": len(request.inquiry_ids)},
            message=f"Deleted {deleted} inquiries ({'permanent' if request.permanent else 'soft'})"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ============================================================
# 16. EXPORT ENDPOINT
# ============================================================

@inquiry_router.get("/export", response_class=StreamingResponse)
async def export_inquiries(
    status: Optional[str] = Query(None, description="Filter by inquiry status"),
    search: Optional[str] = Query(None, description="Search by name, phone, brand, model, plate"),
    brand: Optional[str] = Query(None, description="Filter by vehicle brand"),
    date_from: Optional[datetime] = Query(None, description="Start date (ISO format)"),
    date_to: Optional[datetime] = Query(None, description="End date (ISO format)"),
    max_records: int = Query(10000, ge=1, le=50000, description="Max records to export"),
    service: InquiryService = Depends(get_service(InquiryService))
):
    """
    Export inquiries to CSV.
    
    Max records: 50,000
    """
    # Build filters
    inquiries, total = await service.list_inquiries(
        status=status,
        search=search,
        brand=brand,
        limit=min(max_records, 50000),
        offset=0
    )

    # Filter by date range if provided
    if date_from or date_to:
        inquiries = [
            i for i in inquiries
            if (not date_from or i.created_at >= date_from) and
               (not date_to or i.created_at <= date_to)
        ]

    # Create CSV
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "ID", "Customer", "Phone", "Email", "Province", "City",
        "Vehicle Brand", "Vehicle Model", "Year", "License Plate",
        "Project Type", "Services", "Desired Finish", "Desired Color",
        "Estimated Budget", "Status", "Source", "Created At",
        "Has Project", "Project Status", "Converted At"
    ])

    for inquiry in inquiries:
        writer.writerow([
            str(inquiry.id),
            inquiry.customer_name or "",
            inquiry.customer_phone_number or "",
            inquiry.customer_email or "",
            inquiry.province or "",
            inquiry.city or "",
            inquiry.vehicle_brand or "",
            inquiry.vehicle_model or "",
            inquiry.vehicle_year or "",
            inquiry.vehicle_license_plate or "",
            inquiry.project_type or "",
            inquiry.services or "",
            inquiry.desired_finish or "",
            inquiry.desired_color or "",
            inquiry.estimated_budget or 0,
            inquiry.status,
            inquiry.source or "",
            inquiry.created_at.isoformat() if inquiry.created_at else "",
            "Yes" if inquiry.project else "No",
            inquiry.project.status if inquiry.project else "",
            inquiry.converted_at.isoformat() if inquiry.converted_at else ""
        ])

    output.seek(0)
    filename = f"inquiries_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )