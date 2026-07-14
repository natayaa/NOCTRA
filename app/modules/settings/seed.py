# modules/settings/seed.py
from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    WorkshopSettings,
    PricingSettings,
    SecuritySettings,
    WhatsAppTemplate,
    ProjectType,
    PaymentMethod,
    InquiryStatusWorkflow,
)


async def seed_settings(db: AsyncSession):
    """Seed default settings data."""

    # ==================== WORKSHOP SETTINGS ====================
    workshop = await db.execute(
        select(WorkshopSettings).limit(1)
    )
    if not workshop.scalar_one_or_none():
        workshop = WorkshopSettings(
            name="NOCTRA Autoworks",
            address="Jl. Workshop No. 1, Jakarta",
            phone="021-555-1234",
            email="info@noctra.com",
            website="https://noctra.com",
            primary_color="#ff6b00"
        )
        db.add(workshop)

    # ==================== PRICING SETTINGS ====================
    pricing = await db.execute(
        select(PricingSettings).limit(1)
    )
    if not pricing.scalar_one_or_none():
        pricing = PricingSettings(
            paint_base_price=2500000,
            restoration_base_price=5000000,
            detailing_base_price=500000,
            custom_color_surcharge=500000,
            labor_painter_per_day=200000,
            labor_body_per_day=250000,
            labor_assembly_per_day=150000,
            labor_supervisor_per_day=300000,
            tax_percent=11.0,
            default_margin_percent=40.0,
            default_duration_days=14,
            deposit_percent=30.0,
            currency="IDR",
            auto_generate_invoice=True,
            email_notifications_enabled=True,
            whatsapp_notifications_enabled=True
        )
        db.add(pricing)

    # ==================== SECURITY SETTINGS ====================
    security = await db.execute(
        select(SecuritySettings).limit(1)
    )
    if not security.scalar_one_or_none():
        security = SecuritySettings(
            require_mfa=False,
            allow_remember_me=True,
            force_password_change_days=90,
            session_timeout_minutes=60,
            max_login_attempts=5,
            lockout_duration_minutes=30
        )
        db.add(security)

    # ==================== WHATSAPP TEMPLATES ====================
    default_template = await db.execute(
        select(WhatsAppTemplate).where(
            WhatsAppTemplate.is_default == True).limit(1)
    )
    if not default_template.scalar_one_or_none():
        template = WhatsAppTemplate(
            name="Initial Contact",
            template="Halo {{customer_name}},\n\nKami dari NOCTRA ingin menindaklanjuti inquiry Anda mengenai:\n• Kendaraan: {{vehicle}}\n• Tipe Proyek: {{project_type}}\n\nAda yang bisa kami bantu? 😊",
            description="Template untuk menghubungi customer pertama kali",
            is_default=True,
            variables={
                "customer_name": "Customer Name",
                "vehicle": "Vehicle Information",
                "project_type": "Project Type",
                "phone": "Phone Number",
                "inquiry_id": "Inquiry ID"
            }
        )
        db.add(template)

    # ==================== PROJECT TYPES ====================
    project_types = ["Paint Job", "Restoration",
                     "Detailing", "Full Custom", "Touch Up"]
    for idx, name in enumerate(project_types):
        existing = await db.execute(
            select(ProjectType).where(ProjectType.name == name).limit(1)
        )
        if not existing.scalar_one_or_none():
            db.add(ProjectType(
                name=name,
                is_active=True,
                sort_order=idx
            ))

    # ==================== PAYMENT METHODS ====================
    payment_methods = [
        {"name": "Bank Transfer", "code": "bank_transfer", "icon": "🏦"},
        {"name": "Cash", "code": "cash", "icon": "💵"},
        {"name": "Credit Card", "code": "credit_card", "icon": "💳"},
        {"name": "E-Wallet", "code": "e_wallet", "icon": "📱"},
    ]
    for idx, method in enumerate(payment_methods):
        existing = await db.execute(
            select(PaymentMethod).where(
                PaymentMethod.code == method["code"]).limit(1)
        )
        if not existing.scalar_one_or_none():
            db.add(PaymentMethod(
                **method,
                is_active=True,
                sort_order=idx
            ))

    # ==================== STATUS WORKFLOW ====================
    workflows = [
        {"from_status": "new", "to_status": "under_review"},
        {"from_status": "new", "to_status": "contacted"},
        {"from_status": "new", "to_status": "rejected"},
        {"from_status": "under_review", "to_status": "contacted"},
        {"from_status": "under_review", "to_status": "quoted"},
        {"from_status": "under_review", "to_status": "rejected"},
        {"from_status": "contacted", "to_status": "quoted"},
        {"from_status": "contacted", "to_status": "rejected"},
        {"from_status": "quoted", "to_status": "approved"},
        {"from_status": "quoted", "to_status": "rejected"},
        {"from_status": "approved", "to_status": "converted"},
        {"from_status": "approved", "to_status": "rejected"},
        {"from_status": "converted", "to_status": "completed"},
        {"from_status": "converted", "to_status": "rejected"},
        {"from_status": "rejected", "to_status": "closed"},
    ]
    for idx, wf in enumerate(workflows):
        existing = await db.execute(
            select(InquiryStatusWorkflow).where(
                InquiryStatusWorkflow.from_status == wf["from_status"],
                InquiryStatusWorkflow.to_status == wf["to_status"]
            ).limit(1)
        )
        if not existing.scalar_one_or_none():
            db.add(InquiryStatusWorkflow(
                **wf,
                is_active=True,
                sort_order=idx
            ))

    await db.commit()
