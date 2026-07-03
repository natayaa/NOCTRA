# routers/customer_inquiry.py
from uuid import UUID, uuid4
from decimal import Decimal
from fastapi import APIRouter, Query, HTTPException, File, UploadFile, Body, status
from fastapi.responses import JSONResponse
from typing import List
from datetime import datetime

from database.session import SessionDep
from repositories.customer_inquiry import InquiryRepo
from services.customer_inquiry import InquiryService
from services.projects import ProjectService
from schemas.base_response import BaseResponse
from schemas.customer_inquiry import (
    CustomerInquiryCreate,
    CustomerInquiryResponse,
    CustomerInquirySummary,
    InquiryStatusUpdate,
    InquiryReject,
    InquirySendQuotation,
    NoteUpdate,
    InquiryStatus,
    InquiryConvertToProject,
    CustomerInquiryUpdate
)
from schemas.projects import ProjectCreate

customer_inquiry = APIRouter(prefix="/api/customer/inquiry", tags=["Customer Inquiry"])


@customer_inquiry.get("/", response_model=BaseResponse)
async def list_inquiries(
    status: str | None = Query(None, description="Filter by status"),
    search: str | None = Query(None, description="Search by name, phone, vehicle"),
    brand: str | None = Query(None, description="Filter by vehicle brand"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: SessionDep = None
):
    service = InquiryService(db)
    inquiries = await service.list_inquiries(status, search, brand, limit, offset)
    return BaseResponse(data=[CustomerInquirySummary.model_validate(i).model_dump() for i in inquiries])


@customer_inquiry.get("/statistics", response_model=BaseResponse)
async def get_inquiry_statistics(
    db: SessionDep = None
):
    """Get inquiry statistics for dashboard."""
    service = InquiryService(db)
    data = await service.get_statistics()
    return BaseResponse(data=data)


@customer_inquiry.get("/{inquiry_id}", response_model=BaseResponse)
async def get_inquiry(
    inquiry_id: UUID,
    db: SessionDep
):
    service = InquiryService(db)
    inquiry = await service.get_inquiry(inquiry_id)
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    return BaseResponse(data=CustomerInquiryResponse.model_validate(inquiry).model_dump())


@customer_inquiry.post("/", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_inquiry(
    request: CustomerInquiryCreate,
    db: SessionDep
):
    service = InquiryService(db)
    inquiry = await service.create_inquiry(request)
    await db.commit()
    return BaseResponse(data={"id": str(inquiry.id)})


@customer_inquiry.patch("/{inquiry_id}", response_model=BaseResponse)
async def update_inquiry(
    inquiry_id: UUID,
    request: CustomerInquiryUpdate,
    db: SessionDep
):
    """Update inquiry fields."""
    service = InquiryService(db)
    inquiry = await service.get_inquiry_basic(inquiry_id)
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(inquiry, key):
            setattr(inquiry, key, value)
    
    await db.flush()
    await service.repo.add_activity(inquiry_id, "Inquiry updated", "update", performed_by="system")
    await db.commit()
    return BaseResponse(data={"id": str(inquiry_id)})


@customer_inquiry.patch("/{inquiry_id}/status", response_model=BaseResponse)
async def update_inquiry_status(
    inquiry_id: UUID,
    req: InquiryStatusUpdate,
    db: SessionDep
):
    service = InquiryService(db)
    success = await service.update_status(inquiry_id, req.status, req.note)
    if not success:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    await db.commit()
    return BaseResponse(data={"id": str(inquiry_id), "status": req.status})


@customer_inquiry.post("/{inquiry_id}/reject", response_model=BaseResponse)
async def reject_inquiry(
    inquiry_id: UUID,
    req: InquiryReject,
    db: SessionDep
):
    service = InquiryService(db)
    success = await service.reject_inquiry(inquiry_id, req.reason)
    if not success:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    await db.commit()
    return BaseResponse(data={"id": str(inquiry_id), "status": "rejected"})


@customer_inquiry.post("/{inquiry_id}/quote", response_model=BaseResponse)
async def send_quote(
    inquiry_id: UUID,
    req: InquirySendQuotation,
    db: SessionDep
):
    service = InquiryService(db)
    success = await service.send_quote(inquiry_id, req.estimated_cost, req.notes)
    if not success:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    await db.commit()
    return BaseResponse(data={"id": str(inquiry_id), "status": "quoted"})


@customer_inquiry.patch("/{inquiry_id}/notes", response_model=BaseResponse)
async def update_notes(
    inquiry_id: UUID,
    req: NoteUpdate,
    db: SessionDep
):
    service = InquiryService(db)
    success = await service.update_notes(inquiry_id, req.note)
    if not success:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    await db.commit()
    return BaseResponse(data={"id": str(inquiry_id)})


@customer_inquiry.post("/{inquiry_id}/convert", response_model=BaseResponse)
async def convert_to_project(
    inquiry_id: UUID,
    payload: InquiryConvertToProject = Body(default_factory=dict),
    db: SessionDep = None
):
    service = InquiryService(db)
    inquiry = await service.get_inquiry(inquiry_id)
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")

    if inquiry.status == InquiryStatus.CONVERTED:
        raise HTTPException(status_code=400, detail="Inquiry already converted")

    # Prepare project data
    project_data = ProjectCreate(
        inquiry_id=inquiry.id,
        name=payload.project_name or f"{inquiry.vehicle_brand} {inquiry.vehicle_model} - {inquiry.customer_name}",
        customer_name=inquiry.customer_name,
        customer_phone=inquiry.customer_phone_number,
        customer_email=inquiry.customer_email,
        vehicle_brand=inquiry.vehicle_brand,
        vehicle_model=inquiry.vehicle_model,
        vehicle_year=inquiry.vehicle_year,
        vehicle_license_plate=inquiry.vehicle_license_plate,
        estimated_cost=Decimal(inquiry.estimated_budget or 0),
        estimated_revenue=Decimal(0),
        project_start_date=payload.project_start_date,
        project_target_delivery=payload.project_target_delivery,
        notes=f"Converted from inquiry {inquiry_id}"
    )
    
    project_service = ProjectService(db)
    project = await project_service.create(project_data)

    # Update inquiry status
    inquiry.status = InquiryStatus.CONVERTED
    inquiry.converted_at = datetime.now()
    await service.repo.add_activity(inquiry_id, f"Converted to project: {project.name}", "conversion", performed_by="system")
    await db.commit()

    return BaseResponse(data={"project_id": str(project.id), "inquiry_id": str(inquiry_id)})


@customer_inquiry.post("/{inquiry_id}/photos", response_model=BaseResponse)
async def upload_inquiry_photos(
    inquiry_id: UUID,
    photos: List[UploadFile] = File(..., max_length=10_000_000),
    stage: str = Query("initial", description="Photo stage (initial, before, after)"),
    db: SessionDep = None
):
    service = InquiryService(db)
    inquiry = await service.get_inquiry_basic(inquiry_id)
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")

    uploaded = await service.upload_photos(inquiry_id, photos, stage)
    await db.commit()

    return BaseResponse(data={
        "uploaded": [{"id": str(p.id), "file_path": p.file_path} for p in uploaded]
    })


@customer_inquiry.get("/{inquiry_id}/photos", response_model=BaseResponse)
async def get_inquiry_photos(
    inquiry_id: UUID,
    db: SessionDep = None
):
    service = InquiryService(db)
    photos = await service.get_photos(inquiry_id)
    return BaseResponse(data=[
        {"id": str(p.id), "file_path": p.file_path, "file_name": p.file_name, "stage": p.stage, "created_at": p.created_at}
        for p in photos
    ])


@customer_inquiry.delete("/photos/{photo_id}", response_model=BaseResponse)
async def delete_inquiry_photo(
    photo_id: UUID,
    db: SessionDep = None
):
    service = InquiryService(db)
    deleted = await service.delete_photo(photo_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Photo not found")
    await db.commit()
    return BaseResponse(data={"id": str(photo_id)})


@customer_inquiry.get("/{inquiry_id}/activities", response_model=BaseResponse)
async def get_inquiry_activities(
    inquiry_id: UUID,
    db: SessionDep = None
):
    service = InquiryService(db)
    activities = await service.get_activities(inquiry_id)
    return BaseResponse(data=[
        {"id": str(a.id), "activity": a.activity, "activity_type": a.activity_type, "performed_by": a.performed_by, "created_at": a.created_at}
        for a in activities
    ])


@customer_inquiry.post("/{inquiry_id}/workshop-notes", response_model=BaseResponse)
async def add_workshop_note(
    inquiry_id: UUID,
    note: str = Body(..., embed=True),
    note_type: str = Body("internal", embed=True),
    is_private: bool = Body(False, embed=True),
    db: SessionDep = None
):
    service = InquiryService(db)
    note_obj = await service.add_workshop_note(inquiry_id, note, note_type, "system", is_private)
    await db.commit()
    return BaseResponse(data={"id": str(note_obj.id)})