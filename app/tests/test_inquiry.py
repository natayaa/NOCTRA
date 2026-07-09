# tests/test_inquiry.py
import pytest
from datetime import datetime
from uuid import uuid4

from modules.inquiry.models import CustomerInquiry


@pytest.mark.asyncio
async def test_create_inquiry(client):
    """Test creating inquiry."""
    data = {
        "customer_name": "John Doe",
        "customer_phone_number": "08123456789",
        "vehicle_brand": "Honda",
        "vehicle_model": "CBR",
        "project_type": "repaint",
        "project_description": "Full body repaint"
    }

    response = await client.post("/api/inquiries/", json=data)
    assert response.status_code == 201
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_list_inquiries(client):
    """Test listing inquiries."""
    response = await client.get("/api/inquiries/")
    assert response.status_code == 200
    assert response.json()["success"] is True
