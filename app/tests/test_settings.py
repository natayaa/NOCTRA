# tests/test_settings.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from decimal import Decimal
from uuid import uuid4

from modules.settings.services import SettingsService
from modules.settings.models import (
    WorkshopSettings,
    PricingSettings,
    SecuritySettings,
    WhatsAppTemplate,
    ProjectType,
    PaymentMethod,
    InquiryStatusWorkflow,
)


@pytest.mark.asyncio
async def test_workshop_settings_crud():
    """Test workshop settings CRUD operations."""
    db = AsyncMock()
    repo = MagicMock()
    service = SettingsService(db)
    service.repo = repo

    # Test get
    mock_settings = WorkshopSettings(name="Test Workshop")
    repo.get_workshop_settings = AsyncMock(return_value=mock_settings)

    result = await service.get_workshop_settings()
    assert result.name == "Test Workshop"
    repo.get_workshop_settings.assert_called_once()

    # Test update
    update_data = {"name": "Updated Workshop"}
    repo.update_workshop_settings = AsyncMock(
        return_value=WorkshopSettings(name="Updated Workshop"))

    result = await service.update_workshop_settings(update_data)
    assert result.name == "Updated Workshop"


@pytest.mark.asyncio
async def test_pricing_settings():
    """Test pricing settings."""
    db = AsyncMock()
    repo = MagicMock()
    service = SettingsService(db)
    service.repo = repo

    mock_pricing = PricingSettings(
        paint_base_price=3000000,
        tax_percent=Decimal("11.0"),
        default_duration_days=14,
    )
    repo.get_pricing_settings = AsyncMock(return_value=mock_pricing)

    result = await service.get_pricing_settings()
    assert result.paint_base_price == 3000000
    assert float(result.tax_percent) == 11.0


@pytest.mark.asyncio
async def test_whatsapp_template_render():
    """Test WhatsApp template rendering."""
    template = WhatsAppTemplate(
        name="Test Template",
        template="Halo {{customer_name}}, kendaraan {{vehicle}}",
        variables={"customer_name": "Customer Name", "vehicle": "Vehicle"},
    )

    data = {
        "customer_name": "John Doe",
        "vehicle": "Honda CBR",
    }

    result = template.render(data)
    assert result == "Halo John Doe, kendaraan Honda CBR"


@pytest.mark.asyncio
async def test_status_workflow_map():
    """Test status workflow map generation."""
    db = AsyncMock()
    repo = MagicMock()
    service = SettingsService(db)
    service.repo = repo

    workflows = [
        InquiryStatusWorkflow(from_status="new", to_status="under_review"),
        InquiryStatusWorkflow(from_status="new", to_status="rejected"),
        InquiryStatusWorkflow(from_status="under_review",
                              to_status="contacted"),
    ]
    repo.list_status_workflows = AsyncMock(return_value=workflows)

    result = await service.get_status_workflow_map()
    assert "new" in result
    assert "under_review" in result["new"]
    assert "rejected" in result["new"]
