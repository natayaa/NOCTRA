# modules/settings/router.py
from uuid import UUID
from typing_extensions import Optional, Dict, List

from fastapi import APIRouter, HTTPException, status, Query, Depends
from fastapi import Body
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.base import BaseResponse
from core.dependencies import success_response
from core.dependencies import get_service
from core.exceptions import NotFoundError, ValidationError
from .schemas import (
    WorkshopSettingsUpdate,
    WorkshopSettingsResponse,
    PricingSettingsUpdate,
    PricingSettingsResponse,
    SecuritySettingsUpdate,
    SecuritySettingsResponse,
    WhatsAppTemplateCreate,
    WhatsAppTemplateUpdate,
    WhatsAppTemplateResponse,
    ProjectTypeCreate,
    ProjectTypeUpdate,
    ProjectTypeResponse,
    PaymentMethodCreate,
    PaymentMethodUpdate,
    PaymentMethodResponse,
    StatusWorkflowCreate,
    StatusWorkflowUpdate,
    StatusWorkflowResponse,
    AllSettingsResponse,
)
from .services import SettingsService


settings_router = APIRouter(
    prefix="/api/settings",
    tags=["Settings"]
)


# ============================================================
# WORKSHOP SETTINGS
# ============================================================
@settings_router.get("/workshop", response_model=BaseResponse)
async def get_workshop_settings(
    service: SettingsService = Depends(get_service(SettingsService))
):
    """Get workshop settings."""
    settings = await service.get_workshop_settings()
    return success_response(
        WorkshopSettingsResponse.model_validate(
            settings).model_dump() if settings else None,
        message="Workshop settings retrieved"
    )


@settings_router.patch("/workshop", response_model=BaseResponse)
async def update_workshop_settings(
    data: WorkshopSettingsUpdate,
    service: SettingsService = Depends(get_service(SettingsService))
):
    """Update workshop settings."""
    settings = await service.update_workshop_settings(data)
    return success_response(
        WorkshopSettingsResponse.model_validate(settings).model_dump(),
        message="Workshop settings updated"
    )


# ============================================================
# PRICING SETTINGS
# ============================================================
@settings_router.get("/pricing", response_model=BaseResponse)
async def get_pricing_settings(
    service: SettingsService = Depends(get_service(SettingsService))
):
    """Get pricing settings."""
    settings = await service.get_pricing_settings()
    return success_response(
        PricingSettingsResponse.model_validate(
            settings).model_dump() if settings else None,
        message="Pricing settings retrieved"
    )


@settings_router.patch("/pricing", response_model=BaseResponse)
async def update_pricing_settings(
    data: PricingSettingsUpdate,
    service: SettingsService = Depends(get_service(SettingsService))
):
    """Update pricing settings."""
    settings = await service.update_pricing_settings(data)
    return success_response(
        PricingSettingsResponse.model_validate(settings).model_dump(),
        message="Pricing settings updated"
    )


# ============================================================
# SECURITY SETTINGS
# ============================================================
@settings_router.get("/security", response_model=BaseResponse)
async def get_security_settings(
    service: SettingsService = Depends(get_service(SettingsService))
):
    """Get security settings."""
    settings = await service.get_security_settings()
    return success_response(
        SecuritySettingsResponse.model_validate(
            settings).model_dump() if settings else None,
        message="Security settings retrieved"
    )


@settings_router.patch("/security", response_model=BaseResponse)
async def update_security_settings(
    data: SecuritySettingsUpdate,
    service: SettingsService = Depends(get_service(SettingsService))
):
    """Update security settings."""
    settings = await service.update_security_settings(data)
    return success_response(
        SecuritySettingsResponse.model_validate(settings).model_dump(),
        message="Security settings updated"
    )


# ============================================================
# WHATSAPP TEMPLATES
# ============================================================
@settings_router.get("/whatsapp-templates", response_model=BaseResponse)
async def list_whatsapp_templates(
    service: SettingsService = Depends(get_service(SettingsService))
):
    """List all WhatsApp templates."""
    templates = await service.list_whatsapp_templates()
    return success_response(
        [WhatsAppTemplateResponse.model_validate(
            t).model_dump() for t in templates],
        message="WhatsApp templates retrieved"
    )


@settings_router.get("/whatsapp-templates/default", response_model=BaseResponse)
async def get_default_whatsapp_template(
    service: SettingsService = Depends(get_service(SettingsService))
):
    """Get default WhatsApp template."""
    template = await service.get_default_whatsapp_template()
    if not template:
        raise HTTPException(404, "No default WhatsApp template found")
    return success_response(
        WhatsAppTemplateResponse.model_validate(template).model_dump(),
        message="Default template retrieved"
    )


@settings_router.get("/whatsapp-templates/{template_id}", response_model=BaseResponse)
async def get_whatsapp_template(
    template_id: UUID,
    service: SettingsService = Depends(get_service(SettingsService))
):
    """Get WhatsApp template by ID."""
    try:
        template = await service.get_whatsapp_template(template_id)
        return success_response(
            WhatsAppTemplateResponse.model_validate(template).model_dump(),
            message="Template retrieved"
        )
    except NotFoundError as e:
        raise HTTPException(404, str(e))


@settings_router.post("/whatsapp-templates", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_whatsapp_template(
    data: WhatsAppTemplateCreate,
    service: SettingsService = Depends(get_service(SettingsService))
):
    """Create WhatsApp template."""
    template = await service.create_whatsapp_template(data)
    return success_response(
        WhatsAppTemplateResponse.model_validate(template).model_dump(),
        message="WhatsApp template created"
    )


@settings_router.patch("/whatsapp-templates/{template_id}", response_model=BaseResponse)
async def update_whatsapp_template(
    template_id: UUID,
    data: WhatsAppTemplateUpdate,
    service: SettingsService = Depends(get_service(SettingsService))
):
    """Update WhatsApp template."""
    try:
        template = await service.update_whatsapp_template(template_id, data)
        return success_response(
            WhatsAppTemplateResponse.model_validate(template).model_dump(),
            message="WhatsApp template updated"
        )
    except NotFoundError as e:
        raise HTTPException(404, str(e))


@settings_router.delete("/whatsapp-templates/{template_id}", response_model=BaseResponse)
async def delete_whatsapp_template(
    template_id: UUID,
    service: SettingsService = Depends(get_service(SettingsService))
):
    """Delete WhatsApp template."""
    try:
        await service.delete_whatsapp_template(template_id)
        return success_response(message="WhatsApp template deleted")
    except NotFoundError as e:
        raise HTTPException(404, str(e))


@settings_router.post("/whatsapp-templates/{template_id}/set-default", response_model=BaseResponse)
async def set_default_template(
    template_id: UUID,
    service: SettingsService = Depends(get_service(SettingsService))
):
    """Set template as default."""
    try:
        await service.set_default_template(template_id)
        return success_response(message="Default template updated")
    except NotFoundError as e:
        raise HTTPException(404, str(e))


@settings_router.post("/whatsapp-templates/render", response_model=BaseResponse)
async def render_whatsapp_template(
    template_id: Optional[UUID] = Query(None),
    data: Dict[str, str] = Body(...),
    service: SettingsService = Depends(get_service(SettingsService))
):
    """Render WhatsApp template with data."""
    try:
        message = await service.render_whatsapp_message(template_id, data)
        return success_response({"message": message}, message="Template rendered")
    except NotFoundError as e:
        raise HTTPException(404, str(e))


# ============================================================
# PROJECT TYPES
# ============================================================
@settings_router.get("/project-types", response_model=BaseResponse)
async def list_project_types(
    include_inactive: bool = Query(
        False, description="Include inactive types"),
    service: SettingsService = Depends(get_service(SettingsService))
):
    """List project types."""
    types = await service.list_project_types(include_inactive)
    return success_response(
        [ProjectTypeResponse.model_validate(t).model_dump() for t in types],
        message="Project types retrieved"
    )


@settings_router.get("/project-types/{type_id}", response_model=BaseResponse)
async def get_project_type(
    type_id: UUID,
    service: SettingsService = Depends(get_service(SettingsService))
):
    """Get project type by ID."""
    try:
        project_type = await service.get_project_type(type_id)
        return success_response(
            ProjectTypeResponse.model_validate(project_type).model_dump(),
            message="Project type retrieved"
        )
    except NotFoundError as e:
        raise HTTPException(404, str(e))


@settings_router.post("/project-types", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_project_type(
    data: ProjectTypeCreate,
    service: SettingsService = Depends(get_service(SettingsService))
):
    """Create project type."""
    try:
        project_type = await service.create_project_type(data)
        return success_response(
            ProjectTypeResponse.model_validate(project_type).model_dump(),
            message="Project type created"
        )
    except ValidationError as e:
        raise HTTPException(400, str(e))


@settings_router.patch("/project-types/{type_id}", response_model=BaseResponse)
async def update_project_type(
    type_id: UUID,
    data: ProjectTypeUpdate,
    service: SettingsService = Depends(get_service(SettingsService))
):
    """Update project type."""
    try:
        project_type = await service.update_project_type(type_id, data)
        return success_response(
            ProjectTypeResponse.model_validate(project_type).model_dump(),
            message="Project type updated"
        )
    except NotFoundError as e:
        raise HTTPException(404, str(e))


@settings_router.delete("/project-types/{type_id}", response_model=BaseResponse)
async def delete_project_type(
    type_id: UUID,
    service: SettingsService = Depends(get_service(SettingsService))
):
    """Delete project type."""
    try:
        await service.delete_project_type(type_id)
        return success_response(message="Project type deleted")
    except NotFoundError as e:
        raise HTTPException(404, str(e))


# ============================================================
# PAYMENT METHODS
# ============================================================
@settings_router.get("/payment-methods", response_model=BaseResponse)
async def list_payment_methods(
    include_inactive: bool = Query(
        False, description="Include inactive methods"),
    service: SettingsService = Depends(get_service(SettingsService))
):
    """List payment methods."""
    methods = await service.list_payment_methods(include_inactive)
    return success_response(
        [PaymentMethodResponse.model_validate(
            m).model_dump() for m in methods],
        message="Payment methods retrieved"
    )


@settings_router.get("/payment-methods/{method_id}", response_model=BaseResponse)
async def get_payment_method(
    method_id: UUID,
    service: SettingsService = Depends(get_service(SettingsService))
):
    """Get payment method by ID."""
    try:
        method = await service.get_payment_method(method_id)
        return success_response(
            PaymentMethodResponse.model_validate(method).model_dump(),
            message="Payment method retrieved"
        )
    except NotFoundError as e:
        raise HTTPException(404, str(e))


@settings_router.post("/payment-methods", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_payment_method(
    data: PaymentMethodCreate,
    service: SettingsService = Depends(get_service(SettingsService))
):
    """Create payment method."""
    try:
        method = await service.create_payment_method(data)
        return success_response(
            PaymentMethodResponse.model_validate(method).model_dump(),
            message="Payment method created"
        )
    except ValidationError as e:
        raise HTTPException(400, str(e))


@settings_router.patch("/payment-methods/{method_id}", response_model=BaseResponse)
async def update_payment_method(
    method_id: UUID,
    data: PaymentMethodUpdate,
    service: SettingsService = Depends(get_service(SettingsService))
):
    """Update payment method."""
    try:
        method = await service.update_payment_method(method_id, data)
        return success_response(
            PaymentMethodResponse.model_validate(method).model_dump(),
            message="Payment method updated"
        )
    except NotFoundError as e:
        raise HTTPException(404, str(e))


@settings_router.delete("/payment-methods/{method_id}", response_model=BaseResponse)
async def delete_payment_method(
    method_id: UUID,
    service: SettingsService = Depends(get_service(SettingsService))
):
    """Delete payment method."""
    try:
        await service.delete_payment_method(method_id)
        return success_response(message="Payment method deleted")
    except NotFoundError as e:
        raise HTTPException(404, str(e))


# ============================================================
# STATUS WORKFLOW
# ============================================================
@settings_router.get("/status-workflows", response_model=BaseResponse)
async def list_status_workflows(
    include_inactive: bool = Query(
        False, description="Include inactive workflows"),
    service: SettingsService = Depends(get_service(SettingsService))
):
    """List status workflows."""
    workflows = await service.list_status_workflows(include_inactive)
    return success_response(
        [StatusWorkflowResponse.model_validate(
            w).model_dump() for w in workflows],
        message="Status workflows retrieved"
    )


@settings_router.get("/status-workflows/map", response_model=BaseResponse)
async def get_status_workflow_map(
    service: SettingsService = Depends(get_service(SettingsService))
):
    """Get status workflow map."""
    workflow_map = await service.get_status_workflow_map()
    return success_response(
        workflow_map,
        message="Status workflow map retrieved"
    )


@settings_router.post("/status-workflows", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_status_workflow(
    data: StatusWorkflowCreate,
    service: SettingsService = Depends(get_service(SettingsService))
):
    """Create status workflow."""
    workflow = await service.create_status_workflow(data)
    return success_response(
        StatusWorkflowResponse.model_validate(workflow).model_dump(),
        message="Status workflow created"
    )


@settings_router.patch("/status-workflows/{workflow_id}", response_model=BaseResponse)
async def update_status_workflow(
    workflow_id: UUID,
    data: StatusWorkflowUpdate,
    service: SettingsService = Depends(get_service(SettingsService))
):
    """Update status workflow."""
    try:
        workflow = await service.update_status_workflow(workflow_id, data)
        return success_response(
            StatusWorkflowResponse.model_validate(workflow).model_dump(),
            message="Status workflow updated"
        )
    except NotFoundError as e:
        raise HTTPException(404, str(e))


@settings_router.delete("/status-workflows/{workflow_id}", response_model=BaseResponse)
async def delete_status_workflow(
    workflow_id: UUID,
    service: SettingsService = Depends(get_service(SettingsService))
):
    """Delete status workflow."""
    try:
        await service.delete_status_workflow(workflow_id)
        return success_response(message="Status workflow deleted")
    except NotFoundError as e:
        raise HTTPException(404, str(e))


# ============================================================
# ALL SETTINGS (BULK)
# ============================================================
@settings_router.get("/all", response_model=BaseResponse)
async def get_all_settings(
    service: SettingsService = Depends(get_service(SettingsService))
):
    """Get all settings in one request."""
    settings = await service.get_all_settings()

    return success_response({
        "workshop": WorkshopSettingsResponse.model_validate(settings["workshop"]).model_dump() if settings["workshop"] else None,
        "pricing": PricingSettingsResponse.model_validate(settings["pricing"]).model_dump() if settings["pricing"] else None,
        "security": SecuritySettingsResponse.model_validate(settings["security"]).model_dump() if settings["security"] else None,
        "whatsapp_templates": [WhatsAppTemplateResponse.model_validate(t).model_dump() for t in settings["whatsapp_templates"]],
        "project_types": [ProjectTypeResponse.model_validate(t).model_dump() for t in settings["project_types"]],
        "payment_methods": [PaymentMethodResponse.model_validate(m).model_dump() for m in settings["payment_methods"]],
        "status_workflows": [StatusWorkflowResponse.model_validate(w).model_dump() for w in settings["status_workflows"]],
    }, message="All settings retrieved")
