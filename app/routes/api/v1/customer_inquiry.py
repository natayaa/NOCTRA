import os, shutil

from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, Query, status, HTTPException, File, UploadFile
from fastapi.responses import JSONResponse
from typing_extensions import List
from decimal import Decimal 

from database.session import SessionDep
from repositories.customer_inquiry import InquiryRepo
from services.customer_inquiry import InquiryService
from schemas.base_response import BaseResponse
from schemas.customer_inquiry import (
    CustomerInquiryRequest,
    CustomerInquiryResponse,
    InquiryStatusUpdate,
    InquiryReject,
    InquirySendQuotation,
    NoteUpdate, CustomerInquirySummary, InquiryStatus
)

customer_inquiry = APIRouter(prefix="/api/customer/inquiry", tags=["Customer Inquiry"])

@customer_inquiry.get("/", response_class=JSONResponse)
async def list_inquiries(
    status: str | None = Query(None),
    search: str | None = Query(None),
    db: SessionDep = None
):
    repo = InquiryRepo(db)
    service = InquiryService(repo)
    inquiries = await service.list_inquiries(status, search)
    return BaseResponse(data=[CustomerInquirySummary.model_validate(i) for i in inquiries])

@customer_inquiry.get("/{inquiry_id}", response_class=JSONResponse)
async def get_inquiry(inquiry_id: UUID, db: SessionDep):
    repo = InquiryRepo(db)
    service = InquiryService(repo)   # or bypass service and call repo directly
    inquiry = await repo.get_inquiry_with_details(inquiry_id)  # <-- use new method
    if not inquiry:
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    return BaseResponse(data=CustomerInquiryResponse.model_validate(inquiry))

@customer_inquiry.post("/", response_class=JSONResponse)
async def create_inquiry(request: CustomerInquiryRequest, db: SessionDep):
    repo = InquiryRepo(db)
    service = InquiryService(repo)
    inquiry = await service.create_inquiry(request)
    return BaseResponse(data={"id": str(inquiry.id)})

@customer_inquiry.patch("/{inquiry_id}/status", response_class=JSONResponse)
async def update_inquiry_status(inquiry_id: UUID, req: InquiryStatusUpdate, db: SessionDep):
    repo = InquiryRepo(db)
    service = InquiryService(repo)
    success = await service.update_status(inquiry_id, req.status)
    if not success:
        return JSONResponse(status_code=404, content={"detail": "Inquiry not found"})
    await db.commit()
    return BaseResponse(data={"id": str(inquiry_id), "status": req.status})

@customer_inquiry.post("/{inquiry_id}/reject", response_class=JSONResponse)
async def reject_inquiry(inquiry_id: UUID, req: InquiryReject, db: SessionDep):
    repo = InquiryRepo(db)
    service = InquiryService(repo)
    success = await service.reject_inquiry(inquiry_id, req.reason)
    if not success:
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    await db.commit()
    return BaseResponse(data={"id": str(inquiry_id), "status": "rejected"})

@customer_inquiry.post("/{inquiry_id}/quote", response_class=JSONResponse)
async def send_quote(inquiry_id: UUID, req: InquirySendQuotation, db: SessionDep):
    repo = InquiryRepo(db)
    service = InquiryService(repo)
    success = await service.send_quote(inquiry_id, req.estimated_cost)
    if not success:
        return JSONResponse(status_code=404, content={"detail": "Inquiry not found"})
    await db.commit()
    return BaseResponse(data={"id": str(inquiry_id), "status": "quoted"})

@customer_inquiry.patch("/{inquiry_id}/notes", response_class=JSONResponse)
async def update_notes(inquiry_id: UUID, req: NoteUpdate, db: SessionDep):
    repo = InquiryRepo(db)
    service = InquiryService(repo)
    success = await service.update_notes(inquiry_id, req.note)
    if not success:
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    await db.commit()
    return BaseResponse(data={"id": str(inquiry_id)})

@customer_inquiry.post("/{inquiry_id}/convert", response_class=JSONResponse)
async def convert_to_project(inquiry_id: UUID, db: SessionDep):
    from services.projects import ProjectService
    from schemas.projects import ProjectCreate

    repo = InquiryRepo(db)
    inquiry = await repo.get_with_details(inquiry_id)
    if not inquiry:
        raise HTTPException(404, "Inquiry not found")

    # Check if already converted
    if inquiry.status == InquiryStatus.CONVERTED:
        raise HTTPException(400, "Inquiry already converted to a project")

    # 1) Create project using the inquiry data
    project_data = ProjectCreate(
        inquiry_id=inquiry.id,
        name=f"{inquiry.vehicle_brand} {inquiry.vehicle_model} - {inquiry.customer_name}",
        customer_name=inquiry.customer_name,
        vehicle_brand=inquiry.vehicle_brand,
        vehicle_model=inquiry.vehicle_model,
        estimated_cost=Decimal(inquiry.estimated_budget or 0),  # if you have a budget field
        estimated_revenue=0,  # can be set later
    )
    project_service = ProjectService()
    project = await project_service.create(db, project_data.model_dump())
    await db.flush()

    # 2) Update inquiry status and link to project (already set via inquiry_id)
    inquiry.status = InquiryStatus.CONVERTED
    await repo.add_activity(inquiry_id, f"Converted to project: {project.name}")
    await db.commit()

    return BaseResponse(data={"project_id": str(project.id), "inquiry_id": str(inquiry_id)})


@customer_inquiry.post("/{inquiry_id}/photos", response_class=JSONResponse)
async def upload_inquiry_photos(
    inquiry_id: UUID,
    photos: List[UploadFile] = File(..., max_length=10_000_000),  # field name must match frontend: "photos"
    db: SessionDep = None,
):
    # 1. Check if inquiry exists
    repo = InquiryRepo(db)
    inquiry = await repo.get_inquiry_with_details(inquiry_id)
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")

    # 2. Save each file (example: store in local folder)
    #    You'll probably want to store paths in a database table.
    saved_files = []
    for photo in photos:
        # Validate file type (optional)
        if not photo.content_type.startswith("image/"):
            raise HTTPException(400, f"File {photo.filename} is not an image")

        # Generate a unique filename
        file_extension = os.path.splitext(photo.filename)[1]
        safe_filename = f"{inquiry_id}_{uuid4().hex}{file_extension}"
        file_path = f"uploads/inquiries/{safe_filename}"

        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)

        # (Optional) Save record in a Photo table linked to inquiry_id
        # await repo.add_photo(inquiry_id, file_path)

        saved_files.append(safe_filename)

    await db.commit()  # if you store records

    return BaseResponse(data={"uploaded": saved_files})


