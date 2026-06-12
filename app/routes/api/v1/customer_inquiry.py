
from uuid import UUID, uuid4
from pathlib import Path
from fastapi import APIRouter, status, Depends, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse, Response
from fastapi.encoders import jsonable_encoder
from typing_extensions import Optional

from schemas.base_response import BaseResponse, ErrorResponse
from schemas.customer_inquiry import CustomerInquiryRequest
from models.customer_inquiry import CustomerInquiryPhoto

# db 
from database.session import SessionDep
# Repo
from repositories.customer_inquiry import InquiryRepo
# Service
from services.customer_inquiry import InquiryService

customer_inquiry = APIRouter(
    tags=["Customer Inquiry"],
    prefix="/api/customer/inquiry",
    #dependencies=[Depends()]
)

@customer_inquiry.post("/", response_class=JSONResponse, response_model=BaseResponse)
async def post_customer_inquiry(request: CustomerInquiryRequest, db: SessionDep):
    repo = InquiryRepo(db=db)
    service = InquiryService(repo)
    #print(request)
    inquiry = await service.create_inquiry(request)
    response = {
        "customer_name": inquiry.customer_name, "customer_phone_number": inquiry.customer_phone_number,
        "requested_at": inquiry.created_at, "id": str(inquiry.id)
    }
    return BaseResponse(data=response)


@customer_inquiry.post("/{inquiry_id}/photos")
async def upload_photos(
    inquiry_id: UUID,
    photos: list[UploadFile] = File(default=[]),
    db: SessionDep = None
):
    repo = InquiryRepo(db)
    service = InquiryService(repo)

    result = await service.add_photos(inquiry_id, photos)

    return BaseResponse(
        data={
            "uploaded": result,
            "inquiry_id": str(inquiry_id)
        }
    )