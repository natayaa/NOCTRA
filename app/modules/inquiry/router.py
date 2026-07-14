import csv
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
from core.dependencies import InquiryQueryParams, success_response, get_service
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
)
from modules.inquiry.services import InquiryService


inquiry_router = APIRouter(
    prefix="/api/inquiries",
    tags=["Customer Inquiries"]
)


# ==================== List & Statistics ====================

@inquiry_router.get("/", response_model=PaginatedResponse[CustomerInquirySummary])
async def list_inquiries(
    status: Optional[str] = Query(
        None, description="Filter by inquiry status"),
    search: Optional[str] = Query(
        None, description="Search by name, phone, brand, model, plate"),
    brand: Optional[str] = Query(None, description="Filter by vehicle brand"),
    project_status: Optional[str] = Query(
        None, description="Filter by project status"),
    has_project: Optional[bool] = Query(
        None, description="Filter by project existence (true/false)"),
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
        status=status,
        search=search,
        brand=brand,
        project_status=project_status,
        has_project=has_project,
        limit=limit,
        offset=offset
    )

    return PaginatedResponse.from_paginated(
        items=[CustomerInquirySummary.model_validate(
            i).model_dump() for i in inquiries],
        total=total,
        page=(offset // limit) + 1,
        page_size=limit,
        message="Inquiries retrieved successfully"
    )


@inquiry_router.get("/statistics", response_model=BaseResponse)
async def get_statistics(
    service: InquiryService = Depends(get_service(InquiryService))
):
    """Get inquiry statistics for dashboard."""
    data = await service.get_statistics()
    return success_response(data, message="Statistics retrieved successfully")


@inquiry_router.get("/pending-conversion", response_model=BaseResponse)
async def get_pending_conversion(
    service: InquiryService = Depends(get_service(InquiryService))
):
    """Get inquiries ready for conversion to project."""
    inquiries = await service.get_pending_conversion()
    return success_response(
        [CustomerInquirySummary.model_validate(
            i).model_dump() for i in inquiries],
        message="Pending conversion inquiries retrieved successfully"
    )


# ==================== Detail ====================

@inquiry_router.get("/{inquiry_id}", response_model=BaseResponse)
async def get_inquiry(
    inquiry_id: UUID,
    service: InquiryService = Depends(get_service(InquiryService))
):
    """Get inquiry detail."""
    inquiry = await service.get_inquiry(inquiry_id)
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    return success_response(
        CustomerInquiryResponse.model_validate(inquiry).model_dump(),
        message="Inquiry retrieved successfully"
    )


# ==================== EXPORT ====================
@inquiry_router.get("/export", response_class=StreamingResponse)
async def export_inquiries(status: Optional[str] = Query(None), search: Optional[str] = Query(None), service: InquiryService = Depends(get_service(InquiryService))):
    """Export all inquiries into csv"""
    inquiries, total = await service.list_inquiries(status=status, search=search, limit=10000, offset=0)
    output = StringIO()
    writer = csv.writer()
    # Header
    writer.writerow([
        "ID", "Customer", "Phone", "Email", "Province", "City",
        "Vehicle Brand", "Vehicle Model", "Year", "License Plate",
        "Project Type", "Services", "Desired Finish", "Desired Color",
        "Estimated Budget", "Status", "Created At", "Source",
        "Has Project", "Project Status"
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
            inquiry.created_at.isoformat() if inquiry.created_at else "",
            inquiry.source or "",
            "Yes" if inquiry.project else "No",
            inquiry.project.status if inquiry.project else ""
        ])

    output.seek(0)
    filename = f"inquiries_export_{datetime.now().strftime('%Y%m%d')}.csv"

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# ==================== Create ====================


@inquiry_router.post("/", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_inquiry(
    request: CustomerInquiryCreate,
    service: InquiryService = Depends(get_service(InquiryService))
):
    """Create a new inquiry."""
    try:
        inquiry = await service.create_inquiry(request)

        # 🔥 Broadcast ke semua admin yang connected
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


# ==================== Update ====================

@inquiry_router.patch("/{inquiry_id}", response_model=BaseResponse, description="""
    Update inquiry status dengan validasi transisi.
    
    Status yang diperbolehkan:
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
async def update_inquiry(
    inquiry_id: UUID,
    request: CustomerInquiryUpdate,
    service: InquiryService = Depends(get_service(InquiryService))
):
    """Update inquiry."""
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


@inquiry_router.delete("/{inquiry_id}", response_model=BaseResponse)
async def delete_inquiry(
    inquiry_id: UUID,
    service: InquiryService = Depends(get_service(InquiryService))
):
    """Delete an inquiry."""
    try:
        deleted = await service.delete_inquiry(inquiry_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Inquiry not found")

        return success_response(
            {"id": str(inquiry_id)},
            message="Inquiry deleted successfully"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Status ====================

@inquiry_router.patch("/{inquiry_id}/status", response_model=BaseResponse)
async def update_status(
    inquiry_id: UUID,
    request: InquiryStatusUpdate,
    service: InquiryService = Depends(get_service(InquiryService))
):
    """Update inquiry status."""
    try:
        success = await service.update_status(inquiry_id, request.status, request.note)
        if not success:
            raise HTTPException(status_code=404, detail="Inquiry not found")

        return success_response(
            {"id": str(inquiry_id), "status": request.status},
            message=f"Status updated to {request.status}"
        )
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@inquiry_router.post("/{inquiry_id}/contact", response_model=BaseResponse)
async def contact_customer(
    inquiry_id: UUID,
    note: Optional[str] = Body(None, embed=True),
    service: InquiryService = Depends(get_service(InquiryService))
):
    """Mark inquiry as contacted."""
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


# ==================== Reject ====================

@inquiry_router.post("/{inquiry_id}/reject", response_model=BaseResponse)
async def reject_inquiry(
    inquiry_id: UUID,
    request: InquiryReject,
    service: InquiryService = Depends(get_service(InquiryService))
):
    """Reject inquiry."""
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


# ==================== Quote ====================

@inquiry_router.post("/{inquiry_id}/quote", response_model=BaseResponse)
async def send_quote(
    inquiry_id: UUID,
    request: InquirySendQuotation,
    service: InquiryService = Depends(get_service(InquiryService))
):
    """Send quotation."""
    try:
        success = await service.send_quote(inquiry_id, request.estimated_cost, request.notes)
        if not success:
            raise HTTPException(status_code=404, detail="Inquiry not found")

        return success_response(
            {"id": str(inquiry_id), "status": "quoted"},
            message=f"Quotation sent: Rp {request.estimated_cost:,.2f}"
        )
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=404, detail=str(e))


# ==================== Convert to Project ====================
# modules/inquiry/router.py - TAMBAHKAN DI BAWAH ENDPOINT QUOTE

# ==================== Convert to Project ====================

@inquiry_router.post("/{inquiry_id}/convert-to-project", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def convert_to_project(
    inquiry_id: UUID,
    request: InquiryConvertToProject,
    service: InquiryService = Depends(get_service(InquiryService))
):
    """Convert inquiry to project."""
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
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Close ====================

@inquiry_router.post("/{inquiry_id}/close", response_model=BaseResponse)
async def close_inquiry(
    inquiry_id: UUID,
    request: InquiryClose,
    service: InquiryService = Depends(get_service(InquiryService))
):
    """Close an inquiry."""
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


# ==================== Notes ====================

@inquiry_router.post("/{inquiry_id}/notes", response_model=BaseResponse)
async def add_workshop_note(
    inquiry_id: UUID,
    request: NoteCreate,
    service: InquiryService = Depends(get_service(InquiryService))
):
    """Add workshop note."""
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


@inquiry_router.get("/{inquiry_id}/notes", response_model=BaseResponse)
async def get_workshop_notes(
    inquiry_id: UUID,
    include_private: bool = Query(False, description="Include private notes"),
    service: InquiryService = Depends(get_service(InquiryService))
):
    """Get all workshop notes for inquiry."""
    notes = await service.get_workshop_notes(inquiry_id, include_private)
    return success_response([
        {
            "id": str(n.id),
            "note": n.note,
            "note_type": n.note_type,
            "author": n.author,
            "is_private": n.is_private,
            "created_at": n.created_at.isoformat() if n.created_at else None
        }
        for n in notes
    ], message="Workshop notes retrieved successfully")


# ==================== Photos ====================

@inquiry_router.post("/{inquiry_id}/photos", response_model=BaseResponse)
async def upload_photos(
    inquiry_id: UUID,
    photos: List[UploadFile] = File(..., max_length=10_000_000),
    stage: str = Query("initial", description="Photo stage"),
    service: InquiryService = Depends(get_service(InquiryService))
):
    """Upload photos for inquiry."""
    try:
        uploaded = await service.upload_photos(inquiry_id, photos, stage)

        return success_response(
            {"uploaded": [{"id": str(p.id), "file_path": p.file_path}
                          for p in uploaded]},
            message=f"Uploaded {len(uploaded)} photos"
        )
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@inquiry_router.get("/{inquiry_id}/photos", response_model=BaseResponse)
async def get_photos(
    inquiry_id: UUID,
    service: InquiryService = Depends(get_service(InquiryService))
):
    """Get all photos for inquiry."""
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
            "created_at": p.created_at.isoformat() if p.created_at else None
        }
        for p in photos
    ], message="Photos retrieved successfully")


@inquiry_router.post("/photos/{photo_id}/set-primary", response_model=BaseResponse)
async def set_primary_photo(
    photo_id: UUID,
    service: InquiryService = Depends(get_service(InquiryService))
):
    """Set a photo as primary."""
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
    """Delete a photo."""
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


# ==================== Activities ====================

@inquiry_router.get("/{inquiry_id}/activities", response_model=BaseResponse)
async def get_activities(
    inquiry_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    service: InquiryService = Depends(get_service(InquiryService))
):
    """Get all activities for inquiry."""
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


# ============================================================================
# Follow-Up Endpoints
# ============================================================================

@inquiry_router.post("/{inquiry_id}/follow-ups", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def add_follow_up(
    inquiry_id: UUID,
    request: InquiryFollowUpCreate,
    service: InquiryService = Depends(get_service(InquiryService))
):
    """Add follow-up to inquiry."""
    try:
        follow_up = await service.add_follow_up(inquiry_id, request)

        return success_response(
            {"id": str(follow_up.id)},
            message="Follow-up added successfully"
        )
    except (NotFoundError, ValidationError) as e:
        await service.db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@inquiry_router.get("/{inquiry_id}/follow-ups", response_model=BaseResponse)
async def get_follow_ups(
    inquiry_id: UUID,
    service: InquiryService = Depends(get_service(InquiryService))
):
    """Get all follow-ups for an inquiry."""
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
                "created_at": f.created_at.isoformat()
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
    """Update follow-up."""
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
    """Complete follow-up."""
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
    """Delete follow-up."""
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
    """Get all pending follow-ups (system-wide)."""
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
            }
            for f in follow_ups
        ],
        message="Pending follow-ups retrieved successfully"
    )


@inquiry_router.post("/follow-ups/process", response_model=BaseResponse)
async def process_follow_ups(
    service: InquiryService = Depends(get_service(InquiryService))
):
    """Process pending follow-ups (mark overdue)."""
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
    """Send reminders for upcoming follow-ups."""
    try:
        sent = await service.send_follow_up_reminders()

        return success_response(
            {"sent": len(sent)},
            message=f"Sent {len(sent)} reminders"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@inquiry_router.get("/{inquiry_id}/whatsapp-message", response_model=BaseResponse)
async def get_whatsapp_message(
    inquiry_id: UUID,
    service: InquiryService = Depends(get_service(InquiryService)),
    settings_service: SettingsService = Depends(get_service(SettingsService))
):
    """Generate WhatsApp message menggunakan template dari settings."""
    inquiry = await service.get_inquiry(inquiry_id)
    if not inquiry:
        raise HTTPException(404, "Inquiry not found")

    # Ambil template dari settings
    default_template = await settings_service.get_default_whatsapp_template()

    if default_template:
        # Render template dengan data inquiry
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
        message = f"Halo {inquiry.customer_name},\n\nKami dari NOCTRA ingin menindaklanjuti inquiry Anda mengenai:\n• Kendaraan: {inquiry.vehicle_brand} {inquiry.vehicle_model}\n• Tipe Proyek: {inquiry.project_type}\n\nAda yang bisa kami bantu? 😊"

    return success_response({
        "message": message,
        "phone": inquiry.customer_phone_number,
        "template_id": str(default_template.id) if default_template else None
    })
