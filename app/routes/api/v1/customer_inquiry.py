from uuid import UUID, uuid4
from decimal import Decimal
from fastapi import APIRouter, Query, HTTPException, File, UploadFile, Body
from fastapi.responses import JSONResponse
from typing import List

from database.session import SessionDep
from repositories.customer_inquiry import InquiryRepo
from services.customer_inquiry import InquiryService, InquiryPhotoService
from services.projects import ProjectService
from schemas.base_response import BaseResponse
from schemas.customer_inquiry import (
    CustomerInquiryRequest,
    CustomerInquiryResponse,
    CustomerInquirySummary,
    InquiryStatusUpdate,
    InquiryReject,
    InquirySendQuotation,
    NoteUpdate,
    InquiryStatus,
    ConvertToProjectRequest
)
from schemas.projects import ProjectCreate

customer_inquiry = APIRouter(prefix="/api/customer/inquiry", tags=["Customer Inquiry"])


def get_inquiry_service(db: SessionDep) -> InquiryService:
    repo = InquiryRepo(db)
    return InquiryService(repo)


def get_photo_service(db: SessionDep) -> InquiryPhotoService:
    repo = InquiryRepo(db)
    return InquiryPhotoService(repo)

# Inquiry list
@customer_inquiry.get("/", response_class=JSONResponse)
async def list_inquiries(status: str | None = Query(None), search: str | None = Query(None), db: SessionDep = None):
    service = get_inquiry_service(db)
    inquiries = await service.list_inquiries(status, search)
    return BaseResponse(data=[CustomerInquirySummary.model_validate(i) for i in inquiries])

# Inquiry Detail of customer
@customer_inquiry.get("/{inquiry_id}", response_class=JSONResponse)
async def get_inquiry(inquiry_id: UUID, db: SessionDep):
    service = get_inquiry_service(db)
    inquiry = await service.get_inquiry(inquiry_id)
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    return BaseResponse(data=CustomerInquiryResponse.model_validate(inquiry))


@customer_inquiry.post("/", response_class=JSONResponse)
async def create_inquiry(request: CustomerInquiryRequest, db: SessionDep):
    service = get_inquiry_service(db)
    inquiry = await service.create_inquiry(request)
    return BaseResponse(data={"id": str(inquiry.id)})


@customer_inquiry.patch("/{inquiry_id}/status", response_class=JSONResponse)
async def update_inquiry_status(inquiry_id: UUID, req: InquiryStatusUpdate, db: SessionDep):
    service = get_inquiry_service(db)
    success = await service.update_status(inquiry_id, req.status)
    if not success:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    await db.commit()
    return BaseResponse(data={"id": str(inquiry_id), "status": req.status})


@customer_inquiry.post("/{inquiry_id}/reject", response_class=JSONResponse)
async def reject_inquiry(inquiry_id: UUID, req: InquiryReject, db: SessionDep):
    service = get_inquiry_service(db)
    success = await service.reject_inquiry(inquiry_id, req.reason)
    if not success:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    await db.commit()
    return BaseResponse(data={"id": str(inquiry_id), "status": "rejected"})


@customer_inquiry.post("/{inquiry_id}/quote", response_class=JSONResponse)
async def send_quote(inquiry_id: UUID, req: InquirySendQuotation, db: SessionDep):
    service = get_inquiry_service(db)
    success = await service.send_quote(inquiry_id, req.estimated_cost)
    if not success:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    await db.commit()
    return BaseResponse(data={"id": str(inquiry_id), "status": "quoted"})


@customer_inquiry.patch("/{inquiry_id}/notes", response_class=JSONResponse)
async def update_notes(inquiry_id: UUID, req: NoteUpdate, db: SessionDep):
    service = get_inquiry_service(db)
    success = await service.update_notes(inquiry_id, req.note)
    if not success:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    await db.commit()
    return BaseResponse(data={"id": str(inquiry_id)})


@customer_inquiry.post("/{inquiry_id}/convert", response_class=JSONResponse)
async def convert_to_project(
    inquiry_id: UUID,
    db: SessionDep,
    payload: ConvertToProjectRequest = Body(default_factory=dict),
):
    service = get_inquiry_service(db)
    inquiry = await service.get_inquiry(inquiry_id)
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")

    if inquiry.status == InquiryStatus.CONVERTED:
        raise HTTPException(status_code=400, detail="Inquiry already converted")

    # Prepare project data
    project_data = ProjectCreate(
        inquiry_id=inquiry.id,
        name=f"{inquiry.vehicle_brand} {inquiry.vehicle_model} - {inquiry.customer_name}",
        customer_name=inquiry.customer_name,
        vehicle_brand=inquiry.vehicle_brand,
        vehicle_model=inquiry.vehicle_model,
        estimated_cost=Decimal(inquiry.estimated_budget or 0),
        estimated_revenue=Decimal(0),
        project_start_date=payload.project_start_date,   # tambahkan
        project_target_delivery=payload.project_target_delivery,  # tambahkan
    )
    project_service = ProjectService()
    project = await project_service.create(db, project_data.model_dump())

    inquiry.status = InquiryStatus.CONVERTED
    await service.repo.add_activity(inquiry_id, f"Converted to project: {project.name}")
    await db.commit()

    return BaseResponse(data={"project_id": str(project.id), "inquiry_id": str(inquiry_id)})


@customer_inquiry.post("/{inquiry_id}/photos", response_class=JSONResponse)
async def upload_inquiry_photos(
    inquiry_id: UUID,
    photos: List[UploadFile] = File(..., max_length=10_000_000),
    db: SessionDep = None,
):
    # Check if inquiry exists
    service = get_inquiry_service(db)
    inquiry = await service.get_inquiry(inquiry_id)
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")

    # Use photo service to upload
    photo_service = get_photo_service(db)
    photo_models = await photo_service.upload_photos(inquiry_id, photos)

    # Commit to save photo records (if any)
    await db.commit()

    saved_files = [str(p.file_path) for p in photo_models]
    return BaseResponse(data={"uploaded": saved_files})