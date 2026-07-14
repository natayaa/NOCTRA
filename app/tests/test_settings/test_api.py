# tests/test_settings/test_api.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestSettingsAPI:
    """Test Settings API endpoints."""

    def test_get_workshop_settings(self):
        """Test GET /api/settings/workshop."""
        response = client.get("/api/settings/workshop")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_update_workshop_settings(self):
        """Test PATCH /api/settings/workshop."""
        data = {
            "name": "NOCTRA Test Workshop",
            "phone": "021-555-9999",
        }
        response = client.patch("/api/settings/workshop", json=data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_pricing_settings(self):
        """Test GET /api/settings/pricing."""
        response = client.get("/api/settings/pricing")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_whatsapp_template_crud(self):
        """Test WhatsApp template CRUD operations."""
        # 1. Create template
        template_data = {
            "name": "Test Template API",
            "template": "Halo {{customer_name}}, kendaraan {{vehicle}}",
            "description": "Template for API testing",
            "is_default": True,
        }
        response = client.post(
            "/api/settings/whatsapp-templates", json=template_data)
        assert response.status_code == 201
        template_id = response.json()["data"]["id"]
        assert template_id is not None

        # 2. Get all templates
        response = client.get("/api/settings/whatsapp-templates")
        assert response.status_code == 200
        templates = response.json()["data"]
        assert len(templates) > 0

        # 3. Get specific template
        response = client.get(
            f"/api/settings/whatsapp-templates/{template_id}")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["name"] == "Test Template API"

        # 4. Update template
        update_data = {"name": "Updated Template API"}
        response = client.patch(
            f"/api/settings/whatsapp-templates/{template_id}", json=update_data)
        assert response.status_code == 200

        # 5. Set as default
        response = client.post(
            f"/api/settings/whatsapp-templates/{template_id}/set-default")
        assert response.status_code == 200

        # 6. Delete template
        response = client.delete(
            f"/api/settings/whatsapp-templates/{template_id}")
        assert response.status_code == 200

    def test_project_types_crud(self):
        """Test project types CRUD operations."""
        # 1. Create
        data = {"name": "Test Project Type", "base_price": 5000000}
        response = client.post("/api/settings/project-types", json=data)
        assert response.status_code == 201
        type_id = response.json()["data"]["id"]

        # 2. List
        response = client.get("/api/settings/project-types")
        assert response.status_code == 200
        types = response.json()["data"]
        assert any(t["name"] == "Test Project Type" for t in types)

        # 3. Delete
        response = client.delete(f"/api/settings/project-types/{type_id}")
        assert response.status_code == 200

    def test_payment_methods_crud(self):
        """Test payment methods CRUD operations."""
        # 1. Create
        data = {"name": "Test Payment", "code": "test_payment", "icon": "🧪"}
        response = client.post("/api/settings/payment-methods", json=data)
        assert response.status_code == 201
        method_id = response.json()["data"]["id"]

        # 2. List
        response = client.get("/api/settings/payment-methods")
        assert response.status_code == 200

        # 3. Delete
        response = client.delete(f"/api/settings/payment-methods/{method_id}")
        assert response.status_code == 200

    def test_get_all_settings(self):
        """Test GET /api/settings/all."""
        response = client.get("/api/settings/all")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "workshop" in data["data"]
        assert "pricing" in data["data"]
        assert "whatsapp_templates" in data["data"]
