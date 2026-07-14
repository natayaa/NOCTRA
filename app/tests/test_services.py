# tests/test_inquiry/test_services.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from decimal import Decimal

from modules.inquiry.services import InquiryService
from modules.inquiry.models import CustomerInquiry
from core.constants import InquiryStatus
from core.exceptions import ValidationError


class TestInquiryService:
    """Test InquiryService."""

    @pytest.mark.asyncio
    async def test_create_inquiry(self, mock_inquiry_service, sample_inquiry_data):
        """Test creating inquiry."""
        mock_inquiry = CustomerInquiry(**sample_inquiry_data)
        mock_inquiry.id = uuid4()
        mock_inquiry.status = InquiryStatus.NEW

        mock_inquiry_service.repo.add = AsyncMock()
        mock_inquiry_service.repo.flush = AsyncMock()
        mock_inquiry_service.repo.refresh = AsyncMock(
            return_value=mock_inquiry)
        mock_inquiry_service.repo.add_activity = AsyncMock()

        # Mock db.add, flush, refresh
        mock_inquiry_service.db.add = AsyncMock()
        mock_inquiry_service.db.flush = AsyncMock()
        mock_inquiry_service.db.refresh = AsyncMock(return_value=mock_inquiry)

        # Create request object
        from modules.inquiry.schemas import CustomerInquiryCreate
        request = CustomerInquiryCreate(**sample_inquiry_data)

        result = await mock_inquiry_service.create_inquiry(request)

        assert result.customer_name == "John Doe"
        assert result.status == InquiryStatus.NEW

    @pytest.mark.asyncio
    async def test_update_status_with_valid_transition(self, mock_inquiry_service):
        """Test updating status with valid transition."""
        inquiry_id = uuid4()
        mock_inquiry = CustomerInquiry(id=inquiry_id, status="new")

        mock_inquiry_service.repo.get = AsyncMock(return_value=mock_inquiry)
        mock_inquiry_service.repo.update_status = AsyncMock(return_value=True)

        # Mock get_status_workflow_map from settings
        workflow_map = {
            "new": ["under_review", "contacted", "rejected"],
        }

        # Patch the settings service call
        mock_settings = AsyncMock()
        mock_settings.get_status_workflow_map = AsyncMock(
            return_value=workflow_map)
        mock_inquiry_service._get_settings_service = MagicMock(
            return_value=mock_settings)

        result = await mock_inquiry_service.update_status(inquiry_id, "under_review")

        assert result is True

    @pytest.mark.asyncio
    async def test_update_status_with_invalid_transition(self, mock_inquiry_service):
        """Test updating status with invalid transition."""
        inquiry_id = uuid4()
        mock_inquiry = CustomerInquiry(id=inquiry_id, status="new")

        mock_inquiry_service.repo.get = AsyncMock(return_value=mock_inquiry)

        workflow_map = {"new": ["under_review", "contacted"]}
        mock_settings = AsyncMock()
        mock_settings.get_status_workflow_map = AsyncMock(
            return_value=workflow_map)
        mock_inquiry_service._get_settings_service = MagicMock(
            return_value=mock_settings)

        with pytest.raises(ValidationError):
            await mock_inquiry_service.update_status(inquiry_id, "approved")
