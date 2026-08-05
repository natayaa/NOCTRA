# modules/settings/repository.py
"""
Settings Repository - REFACTORED

✅ Multi-model repository (tidak inherit BaseRepository)
✅ Soft delete support (is_deleted filter)
✅ Transaction handling di service layer
✅ Complete CRUD operations untuk semua models
"""

from uuid import UUID
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy import select, and_, desc, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import (
    WorkshopSettings,
    PricingSettings,
    SecuritySettings,
    WhatsAppTemplate,
    ProjectType,
    PaymentMethod,
    InquiryStatusWorkflow,
)


class SettingsRepository:
    """
    Repository untuk Settings module (multi-model).
    
    ✅ TANPA FLUSH/REFRESH/COMMIT - handled oleh service
    ✅ Soft delete support di semua query
    ✅ Single record pattern untuk Workshop, Pricing, Security
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ============================================================
    # WORKSHOP SETTINGS
    # ============================================================

    async def get_workshop_settings(self) -> Optional[WorkshopSettings]:
        """Get workshop settings (single record)."""
        stmt = select(WorkshopSettings).where(
            WorkshopSettings.is_deleted == False
        ).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_workshop_settings(
        self,
        data: Dict[str, Any]
    ) -> WorkshopSettings:
        """Update workshop settings - TANPA flush."""
        settings = await self.get_workshop_settings()
        if not settings:
            settings = WorkshopSettings()
            self.db.add(settings)

        for key, value in data.items():
            if hasattr(settings, key) and value is not None:
                setattr(settings, key, value)

        settings.updated_at = datetime.now()
        return settings

    # ============================================================
    # PRICING SETTINGS
    # ============================================================

    async def get_pricing_settings(self) -> Optional[PricingSettings]:
        """Get pricing settings (single record)."""
        stmt = select(PricingSettings).where(
            PricingSettings.is_deleted == False
        ).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_pricing_settings(
        self,
        data: Dict[str, Any]
    ) -> PricingSettings:
        """Update pricing settings - TANPA flush."""
        settings = await self.get_pricing_settings()
        if not settings:
            settings = PricingSettings()
            self.db.add(settings)

        for key, value in data.items():
            if hasattr(settings, key) and value is not None:
                setattr(settings, key, value)

        settings.updated_at = datetime.now()
        return settings

    # ============================================================
    # SECURITY SETTINGS
    # ============================================================

    async def get_security_settings(self) -> Optional[SecuritySettings]:
        """Get security settings (single record)."""
        stmt = select(SecuritySettings).where(
            SecuritySettings.is_deleted == False
        ).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_security_settings(
        self,
        data: Dict[str, Any]
    ) -> SecuritySettings:
        """Update security settings - TANPA flush."""
        settings = await self.get_security_settings()
        if not settings:
            settings = SecuritySettings()
            self.db.add(settings)

        for key, value in data.items():
            if hasattr(settings, key) and value is not None:
                setattr(settings, key, value)

        settings.updated_at = datetime.now()
        return settings

    # ============================================================
    # WHATSAPP TEMPLATES
    # ============================================================

    async def list_whatsapp_templates(
        self,
        include_deleted: bool = False
    ) -> List[WhatsAppTemplate]:
        """List all WhatsApp templates."""
        stmt = select(WhatsAppTemplate)
        if not include_deleted:
            stmt = stmt.where(WhatsAppTemplate.is_deleted == False)
        stmt = stmt.order_by(
            WhatsAppTemplate.is_default.desc(),
            WhatsAppTemplate.created_at
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_whatsapp_template(
        self,
        template_id: UUID,
        include_deleted: bool = False
    ) -> Optional[WhatsAppTemplate]:
        """Get WhatsApp template by ID."""
        stmt = select(WhatsAppTemplate).where(
            WhatsAppTemplate.id == template_id
        )
        if not include_deleted:
            stmt = stmt.where(WhatsAppTemplate.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_default_whatsapp_template(
        self,
        include_deleted: bool = False
    ) -> Optional[WhatsAppTemplate]:
        """Get default WhatsApp template."""
        stmt = select(WhatsAppTemplate).where(
            WhatsAppTemplate.is_default == True
        )
        if not include_deleted:
            stmt = stmt.where(WhatsAppTemplate.is_deleted == False)
        stmt = stmt.limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_whatsapp_template(
        self,
        data: Dict[str, Any]
    ) -> WhatsAppTemplate:
        """Create WhatsApp template - TANPA flush."""
        # If this template is default, unset other defaults
        if data.get('is_default'):
            await self.db.execute(
                update(WhatsAppTemplate)
                .where(
                    WhatsAppTemplate.is_default == True,
                    WhatsAppTemplate.is_deleted == False
                )
                .values(is_default=False)
            )

        template = WhatsAppTemplate(**data)
        self.db.add(template)
        return template

    async def update_whatsapp_template(
        self,
        template_id: UUID,
        data: Dict[str, Any]
    ) -> Optional[WhatsAppTemplate]:
        """Update WhatsApp template - TANPA flush."""
        template = await self.get_whatsapp_template(template_id)
        if not template or template.is_deleted:
            return None

        # If setting as default, unset others
        if data.get('is_default'):
            await self.db.execute(
                update(WhatsAppTemplate)
                .where(
                    WhatsAppTemplate.is_default == True,
                    WhatsAppTemplate.id != template_id,
                    WhatsAppTemplate.is_deleted == False
                )
                .values(is_default=False)
            )

        for key, value in data.items():
            if hasattr(template, key) and value is not None:
                setattr(template, key, value)

        template.updated_at = datetime.now()
        return template

    async def delete_whatsapp_template(self, template_id: UUID) -> bool:
        """Soft delete WhatsApp template - TANPA flush."""
        template = await self.get_whatsapp_template(template_id)
        if not template:
            return False

        template.is_deleted = True
        template.deleted_at = datetime.now()
        template.is_default = False

        # If deleting default, set another as default
        if template.is_default:
            stmt = select(WhatsAppTemplate).where(
                WhatsAppTemplate.id != template_id,
                WhatsAppTemplate.is_deleted == False
            ).limit(1)
            result = await self.db.execute(stmt)
            another = result.scalar_one_or_none()
            if another:
                another.is_default = True

        return True

    async def hard_delete_whatsapp_template(self, template_id: UUID) -> bool:
        """Hard delete WhatsApp template (permanent) - TANPA flush."""
        template = await self.get_whatsapp_template(template_id, include_deleted=True)
        if not template:
            return False

        await self.db.delete(template)
        return True

    async def set_default_template(self, template_id: UUID) -> bool:
        """Set a template as default - TANPA flush."""
        template = await self.get_whatsapp_template(template_id)
        if not template or template.is_deleted:
            return False

        # Unset all defaults
        await self.db.execute(
            update(WhatsAppTemplate)
            .where(
                WhatsAppTemplate.is_default == True,
                WhatsAppTemplate.is_deleted == False
            )
            .values(is_default=False)
        )

        template.is_default = True
        template.updated_at = datetime.now()
        return True

    # ============================================================
    # PROJECT TYPES
    # ============================================================

    async def list_project_types(
        self,
        include_inactive: bool = False,
        include_deleted: bool = False
    ) -> List[ProjectType]:
        """List all project types."""
        stmt = select(ProjectType)
        if not include_inactive:
            stmt = stmt.where(ProjectType.is_active == True)
        if not include_deleted:
            stmt = stmt.where(ProjectType.is_deleted == False)
        stmt = stmt.order_by(ProjectType.sort_order, ProjectType.name)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_project_type(
        self,
        type_id: UUID,
        include_deleted: bool = False
    ) -> Optional[ProjectType]:
        """Get project type by ID."""
        stmt = select(ProjectType).where(ProjectType.id == type_id)
        if not include_deleted:
            stmt = stmt.where(ProjectType.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_project_type_by_name(
        self,
        name: str,
        include_deleted: bool = False
    ) -> Optional[ProjectType]:
        """Get project type by name."""
        stmt = select(ProjectType).where(ProjectType.name == name)
        if not include_deleted:
            stmt = stmt.where(ProjectType.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_project_type(
        self,
        data: Dict[str, Any]
    ) -> ProjectType:
        """Create project type - TANPA flush."""
        project_type = ProjectType(**data)
        self.db.add(project_type)
        return project_type

    async def update_project_type(
        self,
        type_id: UUID,
        data: Dict[str, Any]
    ) -> Optional[ProjectType]:
        """Update project type - TANPA flush."""
        project_type = await self.get_project_type(type_id)
        if not project_type or project_type.is_deleted:
            return None

        for key, value in data.items():
            if hasattr(project_type, key) and value is not None:
                setattr(project_type, key, value)

        project_type.updated_at = datetime.now()
        return project_type

    async def delete_project_type(self, type_id: UUID) -> bool:
        """Soft delete project type - TANPA flush."""
        project_type = await self.get_project_type(type_id)
        if not project_type:
            return False

        project_type.is_deleted = True
        project_type.deleted_at = datetime.now()
        project_type.is_active = False
        return True

    async def hard_delete_project_type(self, type_id: UUID) -> bool:
        """Hard delete project type (permanent) - TANPA flush."""
        project_type = await self.get_project_type(type_id, include_deleted=True)
        if not project_type:
            return False

        await self.db.delete(project_type)
        return True

    # ============================================================
    # PAYMENT METHODS
    # ============================================================

    async def list_payment_methods(
        self,
        include_inactive: bool = False,
        include_deleted: bool = False
    ) -> List[PaymentMethod]:
        """List all payment methods."""
        stmt = select(PaymentMethod)
        if not include_inactive:
            stmt = stmt.where(PaymentMethod.is_active == True)
        if not include_deleted:
            stmt = stmt.where(PaymentMethod.is_deleted == False)
        stmt = stmt.order_by(PaymentMethod.sort_order, PaymentMethod.name)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_payment_method(
        self,
        method_id: UUID,
        include_deleted: bool = False
    ) -> Optional[PaymentMethod]:
        """Get payment method by ID."""
        stmt = select(PaymentMethod).where(PaymentMethod.id == method_id)
        if not include_deleted:
            stmt = stmt.where(PaymentMethod.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_payment_method_by_code(
        self,
        code: str,
        include_deleted: bool = False
    ) -> Optional[PaymentMethod]:
        """Get payment method by code."""
        stmt = select(PaymentMethod).where(PaymentMethod.code == code)
        if not include_deleted:
            stmt = stmt.where(PaymentMethod.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_payment_method(
        self,
        data: Dict[str, Any]
    ) -> PaymentMethod:
        """Create payment method - TANPA flush."""
        method = PaymentMethod(**data)
        self.db.add(method)
        return method

    async def update_payment_method(
        self,
        method_id: UUID,
        data: Dict[str, Any]
    ) -> Optional[PaymentMethod]:
        """Update payment method - TANPA flush."""
        method = await self.get_payment_method(method_id)
        if not method or method.is_deleted:
            return None

        for key, value in data.items():
            if hasattr(method, key) and value is not None:
                setattr(method, key, value)

        method.updated_at = datetime.now()
        return method

    async def delete_payment_method(self, method_id: UUID) -> bool:
        """Soft delete payment method - TANPA flush."""
        method = await self.get_payment_method(method_id)
        if not method:
            return False

        method.is_deleted = True
        method.deleted_at = datetime.now()
        method.is_active = False
        return True

    async def hard_delete_payment_method(self, method_id: UUID) -> bool:
        """Hard delete payment method (permanent) - TANPA flush."""
        method = await self.get_payment_method(method_id, include_deleted=True)
        if not method:
            return False

        await self.db.delete(method)
        return True

    # ============================================================
    # INQUIRY STATUS WORKFLOW
    # ============================================================

    async def list_status_workflows(
        self,
        include_inactive: bool = False,
        include_deleted: bool = False
    ) -> List[InquiryStatusWorkflow]:
        """List all status workflows."""
        stmt = select(InquiryStatusWorkflow)
        if not include_inactive:
            stmt = stmt.where(InquiryStatusWorkflow.is_active == True)
        if not include_deleted:
            stmt = stmt.where(InquiryStatusWorkflow.is_deleted == False)
        stmt = stmt.order_by(
            InquiryStatusWorkflow.sort_order,
            InquiryStatusWorkflow.from_status
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_status_workflow(
        self,
        workflow_id: UUID,
        include_deleted: bool = False
    ) -> Optional[InquiryStatusWorkflow]:
        """Get status workflow by ID."""
        stmt = select(InquiryStatusWorkflow).where(
            InquiryStatusWorkflow.id == workflow_id
        )
        if not include_deleted:
            stmt = stmt.where(InquiryStatusWorkflow.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_allowed_transitions(
        self,
        from_status: str
    ) -> List[str]:
        """Get allowed transitions from a status."""
        stmt = select(InquiryStatusWorkflow).where(
            InquiryStatusWorkflow.from_status == from_status,
            InquiryStatusWorkflow.is_active == True,
            InquiryStatusWorkflow.is_deleted == False
        ).order_by(InquiryStatusWorkflow.sort_order)
        result = await self.db.execute(stmt)
        workflows = result.scalars().all()
        return [w.to_status for w in workflows]

    async def create_status_workflow(
        self,
        data: Dict[str, Any]
    ) -> InquiryStatusWorkflow:
        """Create status workflow - TANPA flush."""
        workflow = InquiryStatusWorkflow(**data)
        self.db.add(workflow)
        return workflow

    async def update_status_workflow(
        self,
        workflow_id: UUID,
        data: Dict[str, Any]
    ) -> Optional[InquiryStatusWorkflow]:
        """Update status workflow - TANPA flush."""
        workflow = await self.get_status_workflow(workflow_id)
        if not workflow or workflow.is_deleted:
            return None

        for key, value in data.items():
            if hasattr(workflow, key) and value is not None:
                setattr(workflow, key, value)

        workflow.updated_at = datetime.now()
        return workflow

    async def delete_status_workflow(self, workflow_id: UUID) -> bool:
        """Soft delete status workflow - TANPA flush."""
        workflow = await self.get_status_workflow(workflow_id)
        if not workflow:
            return False

        workflow.is_deleted = True
        workflow.deleted_at = datetime.now()
        workflow.is_active = False
        return True

    async def hard_delete_status_workflow(self, workflow_id: UUID) -> bool:
        """Hard delete status workflow (permanent) - TANPA flush."""
        workflow = await self.get_status_workflow(workflow_id, include_deleted=True)
        if not workflow:
            return False

        await self.db.delete(workflow)
        return True

    async def get_status_workflow_map(self) -> Dict[str, List[str]]:
        """Get complete status workflow map."""
        workflows = await self.list_status_workflows(
            include_inactive=False,
            include_deleted=False
        )
        result = {}
        for w in workflows:
            if w.from_status not in result:
                result[w.from_status] = []
            result[w.from_status].append(w.to_status)
        return result

    # ============================================================
    # BULK OPERATIONS
    # ============================================================

    async def bulk_update_project_types(
        self,
        type_ids: List[UUID],
        data: Dict[str, Any]
    ) -> int:
        """Bulk update project types - TANPA flush."""
        updated = 0
        for type_id in type_ids:
            result = await self.update_project_type(type_id, data)
            if result:
                updated += 1
        return updated

    async def bulk_update_payment_methods(
        self,
        method_ids: List[UUID],
        data: Dict[str, Any]
    ) -> int:
        """Bulk update payment methods - TANPA flush."""
        updated = 0
        for method_id in method_ids:
            result = await self.update_payment_method(method_id, data)
            if result:
                updated += 1
        return updated

    async def bulk_delete_status_workflows(
        self,
        workflow_ids: List[UUID]
    ) -> int:
        """Bulk soft delete status workflows - TANPA flush."""
        deleted = 0
        for workflow_id in workflow_ids:
            result = await self.delete_status_workflow(workflow_id)
            if result:
                deleted += 1
        return deleted