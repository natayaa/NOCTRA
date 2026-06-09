from fastapi import APIRouter, status, Depends, Request, Query
from fastapi.responses import JSONResponse, Response
from fastapi.encoders import jsonable_encoder
from typing_extensions import Optional

customer_inquiry = APIRouter(
    tags=["Customer Inquiry"],
    prefix=["/api/customer/inquiry"],
    dependencies=[Depends()]
)

@customer_inquiry.post("/", response_class=JSONResponse)
async def post_customer_inquiry(request: Request):
    pass