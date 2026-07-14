# tests/conftest.py
from factory.alchemy import SQLAlchemyModelFactory
from factory import Faker, SubFactory
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from core.database import get_db
from core.base import Base
from main import app


# ============================================================
# DATABASE FIXTURES
# ============================================================

# Test database URL (gunakan database terpisah untuk testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_noctra.db"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with async_session() as session:
        yield session
        await session.rollback()
        await session.close()


@pytest.fixture
async def db_override(db_session):
    """Override database dependency for testing."""
    async def _get_db():
        yield db_session
    app.dependency_overrides[get_db] = _get_db
    yield db_session
    app.dependency_overrides.pop(get_db, None)


# ============================================================
# FACTORY FIXTURES (menggunakan factory-boy)
# ============================================================


class WorkshopSettingsFactory(SQLAlchemyModelFactory):
    """Factory untuk WorkshopSettings."""
    class Meta:
        model = None  # Set di fixture

    id = Faker("uuid4")
    name = Faker("company")
    address = Faker("address")
    phone = Faker("phone_number")
    email = Faker("email")
    website = Faker("url")
    primary_color = "#ff6b00"


class PricingSettingsFactory(SQLAlchemyModelFactory):
    """Factory untuk PricingSettings."""
    class Meta:
        model = None

    id = Faker("uuid4")
    paint_base_price = 2500000
    restoration_base_price = 5000000
    detailing_base_price = 500000
    custom_color_surcharge = 500000
    labor_painter_per_day = 200000
    labor_body_per_day = 250000
    labor_assembly_per_day = 150000
    labor_supervisor_per_day = 300000
    tax_percent = 11.0
    default_margin_percent = 40.0
    default_duration_days = 14
    deposit_percent = 30.0
    currency = "IDR"


class WhatsAppTemplateFactory(SQLAlchemyModelFactory):
    """Factory untuk WhatsAppTemplate."""
    class Meta:
        model = None

    id = Faker("uuid4")
    name = Faker("sentence", nb_words=3)
    template = "Halo {{customer_name}}, kendaraan {{vehicle}}"
    description = Faker("sentence")
    is_default = False
    variables = {"customer_name": "Customer Name", "vehicle": "Vehicle"}


class CustomerInquiryFactory(SQLAlchemyModelFactory):
    """Factory untuk CustomerInquiry."""
    class Meta:
        model = None

    id = Faker("uuid4")
    customer_name = Faker("name")
    customer_phone_number = Faker("phone_number")
    customer_email = Faker("email")
    vehicle_brand = Faker("word")
    vehicle_model = Faker("word")
    project_type = "Paint Job"
    project_description = Faker("paragraph")
    status = "new"
    created_at = Faker("date_time_this_year")


# ============================================================
# MOCK FIXTURES
# ============================================================

@pytest.fixture
def mock_repository():
    """Create mock repository."""
    return MagicMock()


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.add = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock()
    session.scalars = AsyncMock()
    return session


@pytest.fixture
def mock_settings_service(mock_db_session):
    """Create mock settings service."""
    from modules.settings.services import SettingsService
    service = SettingsService(mock_db_session)
    service.repo = MagicMock()
    return service


@pytest.fixture
def mock_inquiry_service(mock_db_session):
    """Create mock inquiry service."""
    from modules.inquiry.services import InquiryService
    service = InquiryService(mock_db_session)
    service.repo = MagicMock()
    return service


# ============================================================
# TEST DATA FIXTURES
# ============================================================

@pytest.fixture
def sample_workshop_data():
    """Sample workshop data for testing."""
    return {
        "name": "NOCTRA Test Workshop",
        "address": "Jl. Testing No. 1, Jakarta",
        "phone": "021-555-1234",
        "email": "test@noctra.com",
        "website": "https://test.noctra.com",
    }


@pytest.fixture
def sample_pricing_data():
    """Sample pricing data for testing."""
    return {
        "paint_base_price": 3000000,
        "restoration_base_price": 6000000,
        "detailing_base_price": 600000,
        "custom_color_surcharge": 600000,
        "labor_painter_per_day": 250000,
        "labor_body_per_day": 300000,
        "labor_assembly_per_day": 200000,
        "labor_supervisor_per_day": 350000,
        "tax_percent": 11.0,
        "default_margin_percent": 45.0,
        "default_duration_days": 21,
        "deposit_percent": 30.0,
        "currency": "IDR",
    }


@pytest.fixture
def sample_whatsapp_template():
    """Sample WhatsApp template for testing."""
    return {
        "name": "Test Template",
        "template": "Halo {{customer_name}}, kendaraan {{vehicle}}",
        "description": "Template for testing",
        "is_default": True,
        "variables": {
            "customer_name": "Customer Name",
            "vehicle": "Vehicle",
        },
    }


@pytest.fixture
def sample_inquiry_data():
    """Sample inquiry data for testing."""
    return {
        "customer_name": "John Doe",
        "customer_phone_number": "08123456789",
        "customer_email": "john@example.com",
        "vehicle_brand": "Honda",
        "vehicle_model": "CBR",
        "vehicle_year": 2020,
        "project_type": "Paint Job",
        "project_description": "Full paint job with custom color",
        "estimated_budget": 5000000,
    }


# ============================================================
# CLIENT FIXTURE
# ============================================================

@pytest.fixture
async def async_client(db_override):
    """Async test client for API testing."""
    from httpx import AsyncClient, ASGITransport

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client


@pytest.fixture
def client():
    """Sync test client for API testing."""
    from fastapi.testclient import TestClient
    return TestClient(app)
