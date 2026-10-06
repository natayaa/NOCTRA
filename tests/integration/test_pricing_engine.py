"""Pricing engine recommendation + evaluation tests."""

import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.modules.auth.models import User
from app.modules.pricing.service import PricingService


@pytest.fixture
async def admin_headers(client: AsyncClient, db):
    user = User(
        username="pricing_admin",
        email="pricing_admin@noctra.local",
        full_name="Pricing Admin",
        hashed_password=hash_password("password123"),
        is_superuser=True,
    )
    db.add(user)
    await db.commit()
    r = await client.post(
        "/api/v1/auth/login",
        json={"username": "pricing_admin", "password": "password123"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.asyncio
async def test_recommend_without_rule_uses_defaults(db):
    """With no rules configured, engine falls back to settings defaults."""
    svc = PricingService(db)
    rec = await svc.recommend(hpp=500_000)
    # With defaults (target 50%, min 30%):
    assert rec.recommended_price == 1_000_000
    assert rec.minimum_price == pytest.approx(714_285.71, rel=1e-3)
    assert rec.rule_id is None


@pytest.mark.asyncio
async def test_evaluate_classifies_below_minimum(db):
    svc = PricingService(db)
    ev = await svc.evaluate(hpp=500_000, selling_price=600_000)
    # margin = (600k - 500k) / 600k = 16.67%
    assert ev.margin_pct == pytest.approx(16.67, rel=1e-2)
    assert ev.health == "below_minimum"
    assert ev.meets_minimum is False
    assert ev.meets_target is False


@pytest.mark.asyncio
async def test_evaluate_classifies_excellent(db):
    svc = PricingService(db)
    ev = await svc.evaluate(hpp=500_000, selling_price=1_500_000)
    # margin = (1500 - 500) / 1500 = 66.67%
    assert ev.margin_pct == pytest.approx(66.67, rel=1e-2)
    assert ev.health == "excellent"
    assert ev.meets_minimum is True
    assert ev.meets_target is True