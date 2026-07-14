# tests/test_settings/test_models.py
import pytest
from decimal import Decimal
from uuid import uuid4

from modules.settings.models import (
    WorkshopSettings,
    PricingSettings,
    SecuritySettings,
    WhatsAppTemplate,
    ProjectType,
    PaymentMethod,
    InquiryStatusWorkflow,
)


class TestWorkshopSettings:
    """Test WorkshopSettings model."""

    def test_create_workshop_settings(self):
        """Test creating workshop settings."""
        settings = WorkshopSettings(
            name="NOCTRA Test",
            address="Jl. Test No. 1",
            phone="021-555-1234",
            email="test@noctra.com",
            primary_color="#ff6b00",
        )

        assert settings.name == "NOCTRA Test"
        assert settings.phone == "021-555-1234"
        assert settings.primary_color == "#ff6b00"
        assert settings.id is not None

    def test_workshop_settings_defaults(self):
        """Test workshop settings defaults."""
        settings = WorkshopSettings()

        assert settings.name == "NOCTRA Autoworks"
        assert settings.primary_color == "#ff6b00"
        assert settings.address is None


class TestPricingSettings:
    """Test PricingSettings model."""

    def test_create_pricing_settings(self):
        """Test creating pricing settings."""
        pricing = PricingSettings(
            paint_base_price=3000000,
            tax_percent=Decimal("11.0"),
            default_margin_percent=Decimal("40.0"),
            default_duration_days=14,
            deposit_percent=Decimal("30.0"),
            currency="IDR",
        )

        assert pricing.paint_base_price == 3000000
        assert float(pricing.tax_percent) == 11.0
        assert pricing.currency == "IDR"

    def test_pricing_settings_defaults(self):
        """Test pricing settings defaults."""
        pricing = PricingSettings()

        assert pricing.paint_base_price == 2500000
        assert float(pricing.tax_percent) == 11.0
        assert pricing.currency == "IDR"
        assert pricing.auto_generate_invoice is True


class TestWhatsAppTemplate:
    """Test WhatsAppTemplate model."""

    def test_create_template(self):
        """Test creating WhatsApp template."""
        template = WhatsAppTemplate(
            name="Initial Contact",
            template="Halo {{customer_name}}, kendaraan {{vehicle}}",
            description="Template for first contact",
            is_default=True,
            variables={
                "customer_name": "Customer Name",
                "vehicle": "Vehicle",
                "project_type": "Project Type",
            },
        )

        assert template.name == "Initial Contact"
        assert template.is_default is True
        assert "customer_name" in template.variables

    def test_template_render(self):
        """Test template rendering."""
        template = WhatsAppTemplate(
            name="Test",
            template="Halo {{customer_name}}, kendaraan {{vehicle}}",
        )

        data = {
            "customer_name": "John Doe",
            "vehicle": "Honda CBR",
        }

        result = template.render(data)
        assert result == "Halo John Doe, kendaraan Honda CBR"

    def test_template_render_missing_variable(self):
        """Test template rendering with missing variable."""
        template = WhatsAppTemplate(
            name="Test",
            template="Halo {{customer_name}}, kendaraan {{vehicle}}",
        )

        data = {
            "customer_name": "John Doe",
            # missing vehicle
        }

        result = template.render(data)
        assert result == "Halo John Doe, kendaraan "


class TestProjectType:
    """Test ProjectType model."""

    def test_create_project_type(self):
        """Test creating project type."""
        pt = ProjectType(
            name="Full Custom",
            description="Full custom paint job",
            base_price=10000000,
            is_active=True,
            sort_order=1,
        )

        assert pt.name == "Full Custom"
        assert pt.base_price == 10000000
        assert pt.is_active is True


class TestInquiryStatusWorkflow:
    """Test InquiryStatusWorkflow model."""

    def test_create_workflow(self):
        """Test creating status workflow."""
        workflow = InquiryStatusWorkflow(
            from_status="new",
            to_status="under_review",
            sort_order=1,
            is_active=True,
        )

        assert workflow.from_status == "new"
        assert workflow.to_status == "under_review"
        assert workflow.is_active is True
