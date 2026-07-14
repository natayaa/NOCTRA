# modules/settings/services.py
from uuid import UUID
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import NotFoundError, ValidationError
from .repository import SettingsRepository
from .models import (
    WorkshopSettings,
    PricingSettings,
    SecuritySettings,
    WhatsAppTemplate,
    ProjectType,
    PaymentMethod,
    InquiryStatusWorkflow,
)
from .schemas import (
    WorkshopSettingsUpdate,
    PricingSettingsUpdate,
    SecuritySettingsUpdate,
    WhatsAppTemplateCreate,
    WhatsAppTemplateUpdate,
    ProjectTypeCreate,
    ProjectTypeUpdate,
    PaymentMethodCreate,
    PaymentMethodUpdate,
    StatusWorkflowCreate,
    StatusWorkflowUpdate,
)


class SettingsService:
    """Service untuk Settings module."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SettingsRepository(db)

    # ==================== WORKSHOP SETTINGS ====================

    async def get_workshop_settings(self) -> Optional[WorkshopSettings]:
        """Get workshop settings."""
        return await self.repo.get_workshop_settings()

    async def update_workshop_settings(
        self,
        data: WorkshopSettingsUpdate
    ) -> WorkshopSettings:
        """Update workshop settings."""
        return await self.repo.update_workshop_settings(
            data.model_dump(exclude_unset=True)
        )

    # ==================== PRICING SETTINGS ====================

    async def get_pricing_settings(self) -> Optional[PricingSettings]:
        """Get pricing settings."""
        return await self.repo.get_pricing_settings()

    async def update_pricing_settings(
        self,
        data: PricingSettingsUpdate
    ) -> PricingSettings:
        """Update pricing settings."""
        return await self.repo.update_pricing_settings(
            data.model_dump(exclude_unset=True)
        )

    # ==================== SECURITY SETTINGS ====================

    async def get_security_settings(self) -> Optional[SecuritySettings]:
        """Get security settings."""
        return await self.repo.get_security_settings()

    async def update_security_settings(
        self,
        data: SecuritySettingsUpdate
    ) -> SecuritySettings:
        """Update security settings."""
        return await self.repo.update_security_settings(
            data.model_dump(exclude_unset=True)
        )

    # ==================== WHATSAPP TEMPLATES ====================

    async def list_whatsapp_templates(self) -> List[WhatsAppTemplate]:
        """List all WhatsApp templates."""
        return await self.repo.list_whatsapp_templates()

    async def get_whatsapp_template(
        self,
        template_id: UUID
    ) -> Optional[WhatsAppTemplate]:
        """Get WhatsApp template by ID."""
        template = await self.repo.get_whatsapp_template(template_id)
        if not template:
            raise NotFoundError(f"WhatsApp template {template_id} not found")
        return template

    async def get_default_whatsapp_template(self) -> Optional[WhatsAppTemplate]:
        """Get default WhatsApp template."""
        return await self.repo.get_default_whatsapp_template()

    async def create_whatsapp_template(
        self,
        data: WhatsAppTemplateCreate
    ) -> WhatsAppTemplate:
        """Create WhatsApp template."""
        return await self.repo.create_whatsapp_template(data.model_dump())

    async def update_whatsapp_template(
        self,
        template_id: UUID,
        data: WhatsAppTemplateUpdate
    ) -> WhatsAppTemplate:
        """Update WhatsApp template."""
        template = await self.repo.update_whatsapp_template(
            template_id,
            data.model_dump(exclude_unset=True)
        )
        if not template:
            raise NotFoundError(f"WhatsApp template {template_id} not found")
        return template

    async def delete_whatsapp_template(self, template_id: UUID) -> bool:
        """Delete WhatsApp template."""
        deleted = await self.repo.delete_whatsapp_template(template_id)
        if not deleted:
            raise NotFoundError(f"WhatsApp template {template_id} not found")
        return deleted

    async def set_default_template(self, template_id: UUID) -> bool:
        """Set template as default."""
        return await self.repo.set_default_template(template_id)

    async def render_whatsapp_message(
        self,
        template_id: Optional[UUID],
        data: Dict[str, str]
    ) -> str:
        """Render WhatsApp message with data."""
        if template_id:
            template = await self.repo.get_whatsapp_template(template_id)
        else:
            template = await self.repo.get_default_whatsapp_template()

        if not template:
            raise NotFoundError("No WhatsApp template found")

        return template.render(data)

    # ==================== PROJECT TYPES ====================

    async def list_project_types(
        self,
        include_inactive: bool = False
    ) -> List[ProjectType]:
        """List project types."""
        return await self.repo.list_project_types(include_inactive)

    async def get_project_type(self, type_id: UUID) -> ProjectType:
        """Get project type by ID."""
        project_type = await self.repo.get_project_type(type_id)
        if not project_type:
            raise NotFoundError(f"Project type {type_id} not found")
        return project_type

    async def create_project_type(
        self,
        data: ProjectTypeCreate
    ) -> ProjectType:
        """Create project type."""
        # Check duplicate name
        existing = await self.repo.get_project_type_by_name(data.name)
        if existing:
            raise ValidationError(f"Project type '{data.name}' already exists")
        return await self.repo.create_project_type(data.model_dump())

    async def update_project_type(
        self,
        type_id: UUID,
        data: ProjectTypeUpdate
    ) -> ProjectType:
        """Update project type."""
        project_type = await self.repo.update_project_type(
            type_id,
            data.model_dump(exclude_unset=True)
        )
        if not project_type:
            raise NotFoundError(f"Project type {type_id} not found")
        return project_type

    async def delete_project_type(self, type_id: UUID) -> bool:
        """Delete project type."""
        deleted = await self.repo.delete_project_type(type_id)
        if not deleted:
            raise NotFoundError(f"Project type {type_id} not found")
        return deleted

    # ==================== PAYMENT METHODS ====================

    async def list_payment_methods(
        self,
        include_inactive: bool = False
    ) -> List[PaymentMethod]:
        """List payment methods."""
        return await self.repo.list_payment_methods(include_inactive)

    async def get_payment_method(self, method_id: UUID) -> PaymentMethod:
        """Get payment method by ID."""
        method = await self.repo.get_payment_method(method_id)
        if not method:
            raise NotFoundError(f"Payment method {method_id} not found")
        return method

    async def create_payment_method(
        self,
        data: PaymentMethodCreate
    ) -> PaymentMethod:
        """Create payment method."""
        # Check duplicate code
        existing = await self.repo.get_payment_method_by_code(data.code)
        if existing:
            raise ValidationError(
                f"Payment method code '{data.code}' already exists")
        return await self.repo.create_payment_method(data.model_dump())

    async def update_payment_method(
        self,
        method_id: UUID,
        data: PaymentMethodUpdate
    ) -> PaymentMethod:
        """Update payment method."""
        method = await self.repo.update_payment_method(
            method_id,
            data.model_dump(exclude_unset=True)
        )
        if not method:
            raise NotFoundError(f"Payment method {method_id} not found")
        return method

    async def delete_payment_method(self, method_id: UUID) -> bool:
        """Delete payment method."""
        deleted = await self.repo.delete_payment_method(method_id)
        if not deleted:
            raise NotFoundError(f"Payment method {method_id} not found")
        return deleted

    # ==================== STATUS WORKFLOW ====================

    async def list_status_workflows(
        self,
        include_inactive: bool = False
    ) -> List[InquiryStatusWorkflow]:
        """List status workflows."""
        return await self.repo.list_status_workflows(include_inactive)

    async def get_status_workflow(self, workflow_id: UUID) -> InquiryStatusWorkflow:
        """Get status workflow by ID."""
        workflow = await self.repo.get_status_workflow(workflow_id)
        if not workflow:
            raise NotFoundError(f"Status workflow {workflow_id} not found")
        return workflow

    async def create_status_workflow(
        self,
        data: StatusWorkflowCreate
    ) -> InquiryStatusWorkflow:
        """Create status workflow."""
        return await self.repo.create_status_workflow(data.model_dump())

    async def update_status_workflow(
        self,
        workflow_id: UUID,
        data: StatusWorkflowUpdate
    ) -> InquiryStatusWorkflow:
        """Update status workflow."""
        workflow = await self.repo.update_status_workflow(
            workflow_id,
            data.model_dump(exclude_unset=True)
        )
        if not workflow:
            raise NotFoundError(f"Status workflow {workflow_id} not found")
        return workflow

    async def delete_status_workflow(self, workflow_id: UUID) -> bool:
        """Delete status workflow."""
        deleted = await self.repo.delete_status_workflow(workflow_id)
        if not deleted:
            raise NotFoundError(f"Status workflow {workflow_id} not found")
        return deleted

    async def get_status_workflow_map(self) -> Dict[str, List[str]]:
        """Get complete status workflow map."""
        return await self.repo.get_status_workflow_map()

    # ==================== GET ALL SETTINGS ====================

    async def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings in one call."""
        return {
            "workshop": await self.repo.get_workshop_settings(),
            "pricing": await self.repo.get_pricing_settings(),
            "security": await self.repo.get_security_settings(),
            "whatsapp_templates": await self.repo.list_whatsapp_templates(),
            "project_types": await self.repo.list_project_types(include_inactive=True),
            "payment_methods": await self.repo.list_payment_methods(include_inactive=True),
            "status_workflows": await self.repo.list_status_workflows(include_inactive=True),
        }
