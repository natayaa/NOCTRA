# modules/settings/seed.py
"""
Settings Seed Data - REFACTORED

✅ Default data untuk semua settings
✅ Error handling dengan try-except
✅ Idempotent (bisa dijalankan multiple times)
✅ Logging untuk tracking
"""

import logging
from datetime import datetime

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

logger = logging.getLogger(__name__)


async def seed_settings(db: AsyncSession):
    """
    Seed default settings data.
    
    Idempotent - aman dijalankan berulang kali.
    """
    try:
        logger.info("Starting settings seed...")
        
        # ============================================================
        # WORKSHOP SETTINGS
        # ============================================================
        workshop = await db.execute(
            select(WorkshopSettings).where(
                WorkshopSettings.is_deleted == False
            ).limit(1)
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
            logger.info("Workshop settings seeded")
        else:
            logger.info("Workshop settings already exist, skipping...")

        # ============================================================
        # PRICING SETTINGS
        # ============================================================
        pricing = await db.execute(
            select(PricingSettings).where(
                PricingSettings.is_deleted == False
            ).limit(1)
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
            logger.info("Pricing settings seeded")
        else:
            logger.info("Pricing settings already exist, skipping...")

        # ============================================================
        # SECURITY SETTINGS
        # ============================================================
        security = await db.execute(
            select(SecuritySettings).where(
                SecuritySettings.is_deleted == False
            ).limit(1)
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
            logger.info("Security settings seeded")
        else:
            logger.info("Security settings already exist, skipping...")

        # ============================================================
        # WHATSAPP TEMPLATES
        # ============================================================
        default_template = await db.execute(
            select(WhatsAppTemplate).where(
                WhatsAppTemplate.is_default == True,
                WhatsAppTemplate.is_deleted == False
            ).limit(1)
        )
        if not default_template.scalar_one_or_none():
            template = WhatsAppTemplate(
                name="Initial Contact",
                template=(
                    "Halo {{customer_name}},\n\n"
                    "Kami dari NOCTRA ingin menindaklanjuti inquiry Anda mengenai:\n"
                    "• Kendaraan: {{vehicle}}\n"
                    "• Tipe Proyek: {{project_type}}\n\n"
                    "Ada yang bisa kami bantu? 😊"
                ),
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
            logger.info("WhatsApp template seeded")
        else:
            logger.info("WhatsApp template already exists, skipping...")

        # ============================================================
        # PROJECT TYPES
        # ============================================================
        project_types = [
            {"name": "warna baru", "sort_order": 0},
            {"name": "mengembalikan ke warna original", "sort_order": 1},
            {"name": "perbaikan panel yang rusak", "sort_order": 2},
            {"name": "restorasi total", "sort_order": 3},
            {"name": "butuh konsultasi", "sort_order": 4},
        ]
        for pt in project_types:
            existing = await db.execute(
                select(ProjectType).where(
                    ProjectType.name == pt["name"],
                    ProjectType.is_deleted == False
                ).limit(1)
            )
            if not existing.scalar_one_or_none():
                db.add(ProjectType(
                    name=pt["name"],
                    description=f"Project type: {pt['name']}",
                    is_active=True,
                    sort_order=pt["sort_order"]
                ))
                logger.info(f"Project type '{pt['name']}' seeded")
            else:
                logger.debug(f"Project type '{pt['name']}' already exists, skipping...")

        # ============================================================
        # PAYMENT METHODS
        # ============================================================
        payment_methods = [
            {"name": "Bank Transfer", "code": "bank_transfer", "icon": "🏦", "sort_order": 0},
            {"name": "Cash", "code": "cash", "icon": "💵", "sort_order": 1},
            {"name": "Credit Card", "code": "credit_card", "icon": "💳", "sort_order": 2},
            {"name": "E-Wallet", "code": "e_wallet", "icon": "📱", "sort_order": 3},
            {"name": "QRIS", "code": "qris", "icon": "📱", "sort_order": 4},
        ]
        for method in payment_methods:
            existing = await db.execute(
                select(PaymentMethod).where(
                    PaymentMethod.code == method["code"],
                    PaymentMethod.is_deleted == False
                ).limit(1)
            )
            if not existing.scalar_one_or_none():
                db.add(PaymentMethod(
                    name=method["name"],
                    code=method["code"],
                    icon=method["icon"],
                    is_active=True,
                    sort_order=method["sort_order"],
                    description=f"Payment via {method['name']}"
                ))
                logger.info(f"Payment method '{method['name']}' seeded")
            else:
                logger.debug(f"Payment method '{method['name']}' already exists, skipping...")

        # ============================================================
        # INQUIRY STATUS WORKFLOW
        # ============================================================
        workflows = [
            # From NEW
            {"from_status": "new", "to_status": "under_review", "sort_order": 0},
            {"from_status": "new", "to_status": "contacted", "sort_order": 1},
            {"from_status": "new", "to_status": "rejected", "sort_order": 2},
            # From UNDER_REVIEW
            {"from_status": "under_review", "to_status": "contacted", "sort_order": 3},
            {"from_status": "under_review", "to_status": "quoted", "sort_order": 4},
            {"from_status": "under_review", "to_status": "rejected", "sort_order": 5},
            # From CONTACTED
            {"from_status": "contacted", "to_status": "quoted", "sort_order": 6},
            {"from_status": "contacted", "to_status": "rejected", "sort_order": 7},
            # From QUOTED
            {"from_status": "quoted", "to_status": "approved", "sort_order": 8},
            {"from_status": "quoted", "to_status": "rejected", "sort_order": 9},
            # From APPROVED
            {"from_status": "approved", "to_status": "converted", "sort_order": 10},
            {"from_status": "approved", "to_status": "rejected", "sort_order": 11},
            # From CONVERTED
            {"from_status": "converted", "to_status": "completed", "sort_order": 12},
            {"from_status": "converted", "to_status": "rejected", "sort_order": 13},
            # From REJECTED
            {"from_status": "rejected", "to_status": "closed", "sort_order": 14},
        ]
        for wf in workflows:
            existing = await db.execute(
                select(InquiryStatusWorkflow).where(
                    InquiryStatusWorkflow.from_status == wf["from_status"],
                    InquiryStatusWorkflow.to_status == wf["to_status"],
                    InquiryStatusWorkflow.is_deleted == False
                ).limit(1)
            )
            if not existing.scalar_one_or_none():
                db.add(InquiryStatusWorkflow(
                    from_status=wf["from_status"],
                    to_status=wf["to_status"],
                    sort_order=wf["sort_order"],
                    is_active=True
                ))
                logger.info(f"Workflow {wf['from_status']} → {wf['to_status']} seeded")
            else:
                logger.debug(f"Workflow {wf['from_status']} → {wf['to_status']} already exists, skipping...")

        # ============================================================
        # COMMIT
        # ============================================================
        await db.commit()
        logger.info("✅ All settings seeded successfully!")

    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to seed settings: {str(e)}")
        raise RuntimeError(f"Failed to seed settings: {str(e)}")