from fastapi import APIRouter, status, Depends, Request, Query
from fastapi.responses import JSONResponse, Response
from fastapi.encoders import jsonable_encoder
from typing_extensions import Optional

from schemas.base_response import BaseResponse, ErrorResponse
from schemas.customer_inquiry import CustomerInquiryRequest


customer_inquiry = APIRouter(
    tags=["Customer Inquiry"],
    prefix="/api/customer/inquiry",
    #dependencies=[Depends()]
)

@customer_inquiry.post("/", response_class=JSONResponse, response_model=BaseResponse)
async def post_customer_inquiry(request: Request, repsonse: Response, payload: CustomerInquiryRequest):
    return JSONResponse(content={"message": "OK"})