# tests/test_settings_api.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_get_workshop_settings():
    """Test GET /api/settings/workshop."""
    response = client.get("/api/settings/workshop")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_update_workshop_settings():
    """Test PATCH /api/settings/workshop."""
    data = {
        "name": "NOCTRA Autoworks Test",
        "phone": "021-555-9999",
    }
    response = client.patch("/api/settings/workshop", json=data)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_whatsapp_template_crud():
    """Test WhatsApp template CRUD."""
    # Create
    template_data = {
        "name": "Test Template",
        "template": "Halo {{customer_name}}",
        "is_default": True,
    }
    response = client.post(
        "/api/settings/whatsapp-templates", json=template_data)
    assert response.status_code == 201
    template_id = response.json()["data"]["id"]

    # Get
    response = client.get(f"/api/settings/whatsapp-templates/{template_id}")
    assert response.status_code == 200

    # Update
    update_data = {"name": "Updated Template"}
    response = client.patch(
        f"/api/settings/whatsapp-templates/{template_id}", json=update_data)
    assert response.status_code == 200

    # Delete
    response = client.delete(f"/api/settings/whatsapp-templates/{template_id}")
    assert response.status_code == 200


def test_project_types():
    """Test project types CRUD."""
    # Create
    data = {"name": "Full Custom", "base_price": 10000000}
    response = client.post("/api/settings/project-types", json=data)
    assert response.status_code == 201

    # List
    response = client.get("/api/settings/project-types")
    assert response.status_code == 200
    types = response.json()["data"]
    assert any(t["name"] == "Full Custom" for t in types)
