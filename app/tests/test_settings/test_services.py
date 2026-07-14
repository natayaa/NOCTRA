# tests/test_settings/test_services.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from decimal import Decimal

from modules.settings.services import SettingsService
from modules.settings.models import (
    WorkshopSettings,
    PricingSettings,
    WhatsAppTemplate,
)
from core.exceptions import NotFoundError, ValidationError


class TestSettingsService:
    """Test SettingsService."""

    @pytest.mark.asyncio
    async def test_get_workshop_settings(self, mock_settings_service):
        """Test getting workshop settings."""
        mock_settings = WorkshopSettings(name="Test Workshop")
        mock_settings_service.repo.get_workshop_settings = AsyncMock(
            return_value=mock_settings)

        result = await mock_settings_service.get_workshop_settings()

        assert result.name == "Test Workshop"
        mock_settings_service.repo.get_workshop_settings.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_workshop_settings(self, mock_settings_service):
        """Test updating workshop settings."""
        updated = WorkshopSettings(
            name="Updated Workshop", phone="021-555-9999")
        mock_settings_service.repo.update_workshop_settings = AsyncMock(
            return_value=updated)

        data = {"name": "Updated Workshop", "phone": "021-555-9999"}
        result = await mock_settings_service.update_workshop_settings(data)

        assert result.name == "Updated Workshop"
        assert result.phone == "021-555-9999"

    @pytest.mark.asyncio
    async def test_get_whatsapp_template_not_found(self, mock_settings_service):
        """Test getting non-existent WhatsApp template."""
        mock_settings_service.repo.get_whatsapp_template = AsyncMock(
            return_value=None)

        with pytest.raises(NotFoundError):
            await mock_settings_service.get_whatsapp_template(uuid4())

    @pytest.mark.asyncio
    async def test_create_whatsapp_template(self, mock_settings_service):
        """Test creating WhatsApp template."""
        template_data = {
            "name": "Test Template",
            "template": "Halo {{customer_name}}",
            "is_default": True,
        }

        mock_template = WhatsAppTemplate(
            id=uuid4(),
            **template_data,
        )
        mock_settings_service.repo.create_whatsapp_template = AsyncMock(
            return_value=mock_template)

        result = await mock_settings_service.create_whatsapp_template(template_data)

        assert result.name == "Test Template"
        assert result.is_default is True

    @pytest.mark.asyncio
    async def test_get_status_workflow_map(self, mock_settings_service):
        """Test getting status workflow map."""
        # Setup mock
        from modules.settings.models import InquiryStatusWorkflow

        workflows = [
            InquiryStatusWorkflow(from_status="new", to_status="under_review"),
            InquiryStatusWorkflow(from_status="new", to_status="rejected"),
            InquiryStatusWorkflow(
                from_status="under_review", to_status="contacted"),
        ]
        mock_settings_service.repo.list_status_workflows = AsyncMock(
            return_value=workflows)

        result = await mock_settings_service.get_status_workflow_map()

        assert "new" in result
        assert "under_review" in result["new"]
        assert "rejected" in result["new"]
        assert "contacted" in result["under_review"]


t
