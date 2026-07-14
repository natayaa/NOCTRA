# modules/settings/repository.py
from uuid import UUID
from typing import Optional, List, Dict, Any

from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.base import BaseRepository
from .models import (
    WorkshopSettings,
    PricingSettings,
    SecuritySettings,
    WhatsAppTemplate,
    ProjectType,
    PaymentMethod,
    InquiryStatusWorkflow,
)


class SettingsRepository(BaseRepository):
    """Repository untuk Settings module."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.model = None  # Multi-model repository

    # ==================== WORKSHOP SETTINGS ====================

    async def get_workshop_settings(self) -> Optional[WorkshopSettings]:
        """Get workshop settings (single record)."""
        stmt = select(WorkshopSettings).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_workshop_settings(
        self,
        data: Dict[str, Any]
    ) -> WorkshopSettings:
        """Update workshop settings."""
        settings = await self.get_workshop_settings()
        if not settings:
            settings = WorkshopSettings()
            self.db.add(settings)
            await self.db.flush()

        for key, value in data.items():
            if hasattr(settings, key) and value is not None:
                setattr(settings, key, value)

        await self.db.flush()
        await self.db.refresh(settings)
        return settings

    # ==================== PRICING SETTINGS ====================

    async def get_pricing_settings(self) -> Optional[PricingSettings]:
        """Get pricing settings (single record)."""
        stmt = select(PricingSettings).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_pricing_settings(
        self,
        data: Dict[str, Any]
    ) -> PricingSettings:
        """Update pricing settings."""
        settings = await self.get_pricing_settings()
        if not settings:
            settings = PricingSettings()
            self.db.add(settings)
            await self.db.flush()

        for key, value in data.items():
            if hasattr(settings, key) and value is not None:
                setattr(settings, key, value)

        await self.db.flush()
        await self.db.refresh(settings)
        return settings

    # ==================== SECURITY SETTINGS ====================

    async def get_security_settings(self) -> Optional[SecuritySettings]:
        """Get security settings (single record)."""
        stmt = select(SecuritySettings).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_security_settings(
        self,
        data: Dict[str, Any]
    ) -> SecuritySettings:
        """Update security settings."""
        settings = await self.get_security_settings()
        if not settings:
            settings = SecuritySettings()
            self.db.add(settings)
            await self.db.flush()

        for key, value in data.items():
            if hasattr(settings, key) and value is not None:
                setattr(settings, key, value)

        await self.db.flush()
        await self.db.refresh(settings)
        return settings

    # ==================== WHATSAPP TEMPLATES ====================

    async def list_whatsapp_templates(self) -> List[WhatsAppTemplate]:
        """List all WhatsApp templates."""
        stmt = select(WhatsAppTemplate).order_by(
            WhatsAppTemplate.is_default.desc(),
            WhatsAppTemplate.created_at
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_whatsapp_template(
        self,
        template_id: UUID
    ) -> Optional[WhatsAppTemplate]:
        """Get WhatsApp template by ID."""
        stmt = select(WhatsAppTemplate).where(
            WhatsAppTemplate.id == template_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_default_whatsapp_template(self) -> Optional[WhatsAppTemplate]:
        """Get default WhatsApp template."""
        stmt = select(WhatsAppTemplate).where(
            WhatsAppTemplate.is_default == True
        ).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_whatsapp_template(
        self,
        data: Dict[str, Any]
    ) -> WhatsAppTemplate:
        """Create WhatsApp template."""
        # If this template is default, unset other defaults
        if data.get('is_default'):
            await self.db.execute(
                WhatsAppTemplate.update().where(
                    WhatsAppTemplate.is_default == True
                ).values(is_default=False)
            )

        template = WhatsAppTemplate(**data)
        self.db.add(template)
        await self.db.flush()
        await self.db.refresh(template)
        return template

    async def update_whatsapp_template(
        self,
        template_id: UUID,
        data: Dict[str, Any]
    ) -> Optional[WhatsAppTemplate]:
        """Update WhatsApp template."""
        template = await self.get_whatsapp_template(template_id)
        if not template:
            return None

        # If setting as default, unset others
        if data.get('is_default'):
            await self.db.execute(
                WhatsAppTemplate.update().where(
                    WhatsAppTemplate.is_default == True,
                    WhatsAppTemplate.id != template_id
                ).values(is_default=False)
            )

        for key, value in data.items():
            if hasattr(template, key) and value is not None:
                setattr(template, key, value)

        await self.db.flush()
        await self.db.refresh(template)
        return template

    async def delete_whatsapp_template(self, template_id: UUID) -> bool:
        """Delete WhatsApp template."""
        template = await self.get_whatsapp_template(template_id)
        if not template:
            return False

        # If deleting default, set another as default
        if template.is_default:
            another = await self.db.execute(
                select(WhatsAppTemplate).where(
                    WhatsAppTemplate.id != template_id
                ).limit(1)
            )
            another = another.scalar_one_or_none()
            if another:
                another.is_default = True

        await self.db.delete(template)
        await self.db.flush()
        return True

    async def set_default_template(self, template_id: UUID) -> bool:
        """Set a template as default."""
        template = await self.get_whatsapp_template(template_id)
        if not template:
            return False

        await self.db.execute(
            WhatsAppTemplate.update().where(
                WhatsAppTemplate.is_default == True
            ).values(is_default=False)
        )

        template.is_default = True
        await self.db.flush()
        return True

    # ==================== PROJECT TYPES ====================

    async def list_project_types(
        self,
        include_inactive: bool = False
    ) -> List[ProjectType]:
        """List all project types."""
        stmt = select(ProjectType)
        if not include_inactive:
            stmt = stmt.where(ProjectType.is_active == True)
        stmt = stmt.order_by(ProjectType.sort_order, ProjectType.name)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_project_type(self, type_id: UUID) -> Optional[ProjectType]:
        """Get project type by ID."""
        stmt = select(ProjectType).where(ProjectType.id == type_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_project_type_by_name(self, name: str) -> Optional[ProjectType]:
        """Get project type by name."""
        stmt = select(ProjectType).where(ProjectType.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_project_type(self, data: Dict[str, Any]) -> ProjectType:
        """Create project type."""
        project_type = ProjectType(**data)
        self.db.add(project_type)
        await self.db.flush()
        await self.db.refresh(project_type)
        return project_type

    async def update_project_type(
        self,
        type_id: UUID,
        data: Dict[str, Any]
    ) -> Optional[ProjectType]:
        """Update project type."""
        project_type = await self.get_project_type(type_id)
        if not project_type:
            return None

        for key, value in data.items():
            if hasattr(project_type, key) and value is not None:
                setattr(project_type, key, value)

        await self.db.flush()
        await self.db.refresh(project_type)
        return project_type

    async def delete_project_type(self, type_id: UUID) -> bool:
        """Delete project type."""
        project_type = await self.get_project_type(type_id)
        if not project_type:
            return False

        await self.db.delete(project_type)
        await self.db.flush()
        return True

    # ==================== PAYMENT METHODS ====================

    async def list_payment_methods(
        self,
        include_inactive: bool = False
    ) -> List[PaymentMethod]:
        """List all payment methods."""
        stmt = select(PaymentMethod)
        if not include_inactive:
            stmt = stmt.where(PaymentMethod.is_active == True)
        stmt = stmt.order_by(PaymentMethod.sort_order, PaymentMethod.name)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_payment_method(self, method_id: UUID) -> Optional[PaymentMethod]:
        """Get payment method by ID."""
        stmt = select(PaymentMethod).where(PaymentMethod.id == method_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_payment_method_by_code(self, code: str) -> Optional[PaymentMethod]:
        """Get payment method by code."""
        stmt = select(PaymentMethod).where(PaymentMethod.code == code)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_payment_method(self, data: Dict[str, Any]) -> PaymentMethod:
        """Create payment method."""
        method = PaymentMethod(**data)
        self.db.add(method)
        await self.db.flush()
        await self.db.refresh(method)
        return method

    async def update_payment_method(
        self,
        method_id: UUID,
        data: Dict[str, Any]
    ) -> Optional[PaymentMethod]:
        """Update payment method."""
        method = await self.get_payment_method(method_id)
        if not method:
            return None

        for key, value in data.items():
            if hasattr(method, key) and value is not None:
                setattr(method, key, value)

        await self.db.flush()
        await self.db.refresh(method)
        return method

    async def delete_payment_method(self, method_id: UUID) -> bool:
        """Delete payment method."""
        method = await self.get_payment_method(method_id)
        if not method:
            return False

        await self.db.delete(method)
        await self.db.flush()
        return True

    # ==================== STATUS WORKFLOW ====================

    async def list_status_workflows(
        self,
        include_inactive: bool = False
    ) -> List[InquiryStatusWorkflow]:
        """List all status workflows."""
        stmt = select(InquiryStatusWorkflow)
        if not include_inactive:
            stmt = stmt.where(InquiryStatusWorkflow.is_active == True)
        stmt = stmt.order_by(
            InquiryStatusWorkflow.sort_order,
            InquiryStatusWorkflow.from_status
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_status_workflow(
        self,
        workflow_id: UUID
    ) -> Optional[InquiryStatusWorkflow]:
        """Get status workflow by ID."""
        stmt = select(InquiryStatusWorkflow).where(
            InquiryStatusWorkflow.id == workflow_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_allowed_transitions(
        self,
        from_status: str
    ) -> List[str]:
        """Get allowed transitions from a status."""
        stmt = select(InquiryStatusWorkflow).where(
            InquiryStatusWorkflow.from_status == from_status,
            InquiryStatusWorkflow.is_active == True
        ).order_by(InquiryStatusWorkflow.sort_order)
        result = await self.db.execute(stmt)
        workflows = result.scalars().all()
        return [w.to_status for w in workflows]

    async def create_status_workflow(
        self,
        data: Dict[str, Any]
    ) -> InquiryStatusWorkflow:
        """Create status workflow."""
        workflow = InquiryStatusWorkflow(**data)
        self.db.add(workflow)
        await self.db.flush()
        await self.db.refresh(workflow)
        return workflow

    async def update_status_workflow(
        self,
        workflow_id: UUID,
        data: Dict[str, Any]
    ) -> Optional[InquiryStatusWorkflow]:
        """Update status workflow."""
        workflow = await self.get_status_workflow(workflow_id)
        if not workflow:
            return None

        for key, value in data.items():
            if hasattr(workflow, key) and value is not None:
                setattr(workflow, key, value)

        await self.db.flush()
        await self.db.refresh(workflow)
        return workflow

    async def delete_status_workflow(self, workflow_id: UUID) -> bool:
        """Delete status workflow."""
        workflow = await self.get_status_workflow(workflow_id)
        if not workflow:
            return False

        await self.db.delete(workflow)
        await self.db.flush()
        return True

    async def get_status_workflow_map(self) -> Dict[str, List[str]]:
        """Get complete status workflow map."""
        workflows = await self.list_status_workflows(include_inactive=False)
        result = {}
        for w in workflows:
            if w.from_status not in result:
                result[w.from_status] = []
            result[w.from_status].append(w.to_status)
        return result
