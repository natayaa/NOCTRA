# modules/settings/services.py
"""
Settings Service - REFACTORED

✅ Complete business logic untuk Settings module
✅ Validasi input (email, website, phone, dll)
✅ Soft delete support
✅ Transaction handling
✅ Cache untuk status workflow map
"""

from uuid import UUID
from typing import Optional, List, Dict, Any
import re
from datetime import datetime, timedelta

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
    """
    Service untuk Settings module.
    
    ✅ Handle transaction di setiap method
    ✅ Validasi input
    ✅ Cache untuk data yang sering diakses
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SettingsRepository(db)
        
        # Cache untuk status workflow map
        self._workflow_cache = None
        self._workflow_cache_time = None
        self._cache_ttl = 300  # 5 minutes

    # ============================================================
    # HELPER METHODS
    # ============================================================

    def _invalidate_cache(self):
        """Invalidate workflow cache."""
        self._workflow_cache = None
        self._workflow_cache_time = None

    async def _get_cached_workflow_map(self) -> Dict[str, List[str]]:
        """Get workflow map with caching."""
        now = datetime.now()
        
        if self._workflow_cache and self._workflow_cache_time:
            if (now - self._workflow_cache_time).seconds < self._cache_ttl:
                return self._workflow_cache
        
        workflow_map = await self.repo.get_status_workflow_map()
        self._workflow_cache = workflow_map
        self._workflow_cache_time = now
        return workflow_map

    # ============================================================
    # WORKSHOP SETTINGS
    # ============================================================

    async def get_workshop_settings(self) -> Optional[WorkshopSettings]:
        """Get workshop settings."""
        return await self.repo.get_workshop_settings()

    async def update_workshop_settings(
        self,
        data: WorkshopSettingsUpdate
    ) -> WorkshopSettings:
        """
        Update workshop settings with validation.
        
        Validates:
        - Email format
        - Website URL
        - Phone number format
        - Primary color format
        """
        update_data = data.model_dump(exclude_unset=True)
        
        # Validate email if provided
        if 'email' in update_data and update_data['email']:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, update_data['email']):
                raise ValidationError("Invalid email format")
        
        # Validate website if provided
        if 'website' in update_data and update_data['website']:
            if not update_data['website'].startswith(('http://', 'https://')):
                update_data['website'] = f"https://{update_data['website']}"
        
        # Validate phone if provided
        if 'phone' in update_data and update_data['phone']:
            phone_clean = re.sub(r'[\s\-\(\)]', '', update_data['phone'])
            if not re.match(r'^\+?[0-9]{8,15}$', phone_clean):
                raise ValidationError("Invalid phone number format")
        
        # Validate primary color if provided
        if 'primary_color' in update_data and update_data['primary_color']:
            if not re.match(r'^#[0-9a-fA-F]{6}$', update_data['primary_color']):
                raise ValidationError("Primary color must be in hex format: #RRGGBB")
        
        result = await self.repo.update_workshop_settings(update_data)
        await self.db.flush()
        await self.db.refresh(result)
        return result

    # ============================================================
    # PRICING SETTINGS
    # ============================================================

    async def get_pricing_settings(self) -> Optional[PricingSettings]:
        """Get pricing settings."""
        return await self.repo.get_pricing_settings()

    async def update_pricing_settings(
        self,
        data: PricingSettingsUpdate
    ) -> PricingSettings:
        """Update pricing settings."""
        update_data = data.model_dump(exclude_unset=True)
        
        # Validate tax percent
        if 'tax_percent' in update_data:
            if update_data['tax_percent'] < 0 or update_data['tax_percent'] > 100:
                raise ValidationError("Tax percent must be between 0 and 100")
        
        # Validate margin percent
        if 'default_margin_percent' in update_data:
            if update_data['default_margin_percent'] < 0 or update_data['default_margin_percent'] > 100:
                raise ValidationError("Margin percent must be between 0 and 100")
        
        # Validate deposit percent
        if 'deposit_percent' in update_data:
            if update_data['deposit_percent'] < 0 or update_data['deposit_percent'] > 100:
                raise ValidationError("Deposit percent must be between 0 and 100")
        
        # Validate duration days
        if 'default_duration_days' in update_data:
            if update_data['default_duration_days'] < 1:
                raise ValidationError("Duration days must be at least 1")
        
        result = await self.repo.update_pricing_settings(update_data)
        await self.db.flush()
        await self.db.refresh(result)
        return result

    # ============================================================
    # SECURITY SETTINGS
    # ============================================================

    async def get_security_settings(self) -> Optional[SecuritySettings]:
        """Get security settings."""
        return await self.repo.get_security_settings()

    async def update_security_settings(
        self,
        data: SecuritySettingsUpdate
    ) -> SecuritySettings:
        """Update security settings."""
        update_data = data.model_dump(exclude_unset=True)
        
        # Validate force password change days
        if 'force_password_change_days' in update_data:
            if update_data['force_password_change_days'] < 0:
                raise ValidationError("Force password change days cannot be negative")
        
        # Validate session timeout
        if 'session_timeout_minutes' in update_data:
            if update_data['session_timeout_minutes'] < 5:
                raise ValidationError("Session timeout must be at least 5 minutes")
        
        # Validate max login attempts
        if 'max_login_attempts' in update_data:
            if update_data['max_login_attempts'] < 3:
                raise ValidationError("Max login attempts must be at least 3")
        
        # Validate lockout duration
        if 'lockout_duration_minutes' in update_data:
            if update_data['lockout_duration_minutes'] < 5:
                raise ValidationError("Lockout duration must be at least 5 minutes")
        
        result = await self.repo.update_security_settings(update_data)
        await self.db.flush()
        await self.db.refresh(result)
        return result

    # ============================================================
    # WHATSAPP TEMPLATES
    # ============================================================

    async def list_whatsapp_templates(self) -> List[WhatsAppTemplate]:
        """List all WhatsApp templates."""
        return await self.repo.list_whatsapp_templates()

    async def get_whatsapp_template(
        self,
        template_id: UUID
    ) -> WhatsAppTemplate:
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
        template_data = data.model_dump()
        
        # Validate template has valid placeholders
        placeholders = re.findall(r'\{\{(.*?)\}\}', template_data['template'])
        if placeholders and not template_data.get('variables'):
            # Auto-generate variables if not provided
            template_data['variables'] = {p: p.replace('_', ' ').title() for p in set(placeholders)}
        
        # If setting as default, invalidate cache
        if template_data.get('is_default'):
            self._invalidate_cache()
        
        result = await self.repo.create_whatsapp_template(template_data)
        await self.db.flush()
        await self.db.refresh(result)
        return result

    async def update_whatsapp_template(
        self,
        template_id: UUID,
        data: WhatsAppTemplateUpdate
    ) -> WhatsAppTemplate:
        """Update WhatsApp template."""
        update_data = data.model_dump(exclude_unset=True)
        
        # Validate template has valid placeholders
        if 'template' in update_data:
            placeholders = re.findall(r'\{\{(.*?)\}\}', update_data['template'])
            if placeholders and not update_data.get('variables'):
                # Auto-generate variables if not provided
                update_data['variables'] = {p: p.replace('_', ' ').title() for p in set(placeholders)}
        
        result = await self.repo.update_whatsapp_template(template_id, update_data)
        if not result:
            raise NotFoundError(f"WhatsApp template {template_id} not found")
        
        # If setting as default, invalidate cache
        if update_data.get('is_default'):
            self._invalidate_cache()
        
        await self.db.flush()
        await self.db.refresh(result)
        return result

    async def delete_whatsapp_template(self, template_id: UUID) -> bool:
        """Soft delete WhatsApp template."""
        result = await self.repo.delete_whatsapp_template(template_id)
        if not result:
            raise NotFoundError(f"WhatsApp template {template_id} not found")
        
        # Invalidate cache
        self._invalidate_cache()
        await self.db.flush()
        return result

    async def set_default_template(self, template_id: UUID) -> bool:
        """Set template as default."""
        result = await self.repo.set_default_template(template_id)
        if not result:
            raise NotFoundError(f"WhatsApp template {template_id} not found")
        
        self._invalidate_cache()
        await self.db.flush()
        return result

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

    # ============================================================
    # PROJECT TYPES
    # ============================================================

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
        
        result = await self.repo.create_project_type(data.model_dump())
        await self.db.flush()
        await self.db.refresh(result)
        return result

    async def update_project_type(
        self,
        type_id: UUID,
        data: ProjectTypeUpdate
    ) -> ProjectType:
        """Update project type."""
        # Check duplicate name if changing name
        if data.name is not None:
            existing = await self.repo.get_project_type_by_name(data.name)
            if existing and existing.id != type_id:
                raise ValidationError(f"Project type '{data.name}' already exists")
        
        result = await self.repo.update_project_type(type_id, data.model_dump(exclude_unset=True))
        if not result:
            raise NotFoundError(f"Project type {type_id} not found")
        
        await self.db.flush()
        await self.db.refresh(result)
        return result

    async def delete_project_type(self, type_id: UUID) -> bool:
        """Soft delete project type."""
        result = await self.repo.delete_project_type(type_id)
        if not result:
            raise NotFoundError(f"Project type {type_id} not found")
        
        await self.db.flush()
        return result

    # ============================================================
    # PAYMENT METHODS
    # ============================================================

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
            raise ValidationError(f"Payment method code '{data.code}' already exists")
        
        # Check duplicate name
        methods = await self.repo.list_payment_methods(include_inactive=True)
        for m in methods:
            if m.name.lower() == data.name.lower():
                raise ValidationError(f"Payment method name '{data.name}' already exists")
        
        result = await self.repo.create_payment_method(data.model_dump())
        await self.db.flush()
        await self.db.refresh(result)
        return result

    async def update_payment_method(
        self,
        method_id: UUID,
        data: PaymentMethodUpdate
    ) -> PaymentMethod:
        """Update payment method."""
        # Check duplicate code if changing code
        if data.code is not None:
            existing = await self.repo.get_payment_method_by_code(data.code)
            if existing and existing.id != method_id:
                raise ValidationError(f"Payment method code '{data.code}' already exists")
        
        # Check duplicate name if changing name
        if data.name is not None:
            methods = await self.repo.list_payment_methods(include_inactive=True)
            for m in methods:
                if m.name.lower() == data.name.lower() and m.id != method_id:
                    raise ValidationError(f"Payment method name '{data.name}' already exists")
        
        result = await self.repo.update_payment_method(method_id, data.model_dump(exclude_unset=True))
        if not result:
            raise NotFoundError(f"Payment method {method_id} not found")
        
        await self.db.flush()
        await self.db.refresh(result)
        return result

    async def delete_payment_method(self, method_id: UUID) -> bool:
        """Soft delete payment method."""
        result = await self.repo.delete_payment_method(method_id)
        if not result:
            raise NotFoundError(f"Payment method {method_id} not found")
        
        await self.db.flush()
        return result

    # ============================================================
    # INQUIRY STATUS WORKFLOW
    # ============================================================

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
        # Check if workflow already exists
        existing_workflows = await self.repo.list_status_workflows(include_inactive=True)
        for w in existing_workflows:
            if w.from_status == data.from_status and w.to_status == data.to_status:
                raise ValidationError(
                    f"Workflow from '{data.from_status}' to '{data.to_status}' already exists"
                )
        
        result = await self.repo.create_status_workflow(data.model_dump())
        self._invalidate_cache()
        await self.db.flush()
        await self.db.refresh(result)
        return result

    async def update_status_workflow(
        self,
        workflow_id: UUID,
        data: StatusWorkflowUpdate
    ) -> InquiryStatusWorkflow:
        """Update status workflow."""
        # Check duplicate if changing from/to
        update_data = data.model_dump(exclude_unset=True)
        if 'from_status' in update_data and 'to_status' in update_data:
            existing_workflows = await self.repo.list_status_workflows(include_inactive=True)
            for w in existing_workflows:
                if (w.from_status == update_data['from_status'] and 
                    w.to_status == update_data['to_status'] and 
                    w.id != workflow_id):
                    raise ValidationError(
                        f"Workflow from '{update_data['from_status']}' to '{update_data['to_status']}' already exists"
                    )
        
        result = await self.repo.update_status_workflow(workflow_id, update_data)
        if not result:
            raise NotFoundError(f"Status workflow {workflow_id} not found")
        
        self._invalidate_cache()
        await self.db.flush()
        await self.db.refresh(result)
        return result

    async def delete_status_workflow(self, workflow_id: UUID) -> bool:
        """Soft delete status workflow."""
        result = await self.repo.delete_status_workflow(workflow_id)
        if not result:
            raise NotFoundError(f"Status workflow {workflow_id} not found")
        
        self._invalidate_cache()
        await self.db.flush()
        return result

    async def get_status_workflow_map(self) -> Dict[str, List[str]]:
        """Get complete status workflow map with caching."""
        return await self._get_cached_workflow_map()

    # ============================================================
    # GET ALL SETTINGS
    # ============================================================

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