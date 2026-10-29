"""Admin settings page — tabbed workspace contract.

The page is now a tabbed workspace (rail + one visible panel + client-side
search). Everything still posts through ONE form, so the tests below pin
that contract: every known key stays in the DOM, booleans post
"true"/"false" through a hidden input, secrets stay masked, and the
active tab survives the redirect after a save.
"""

import re

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.modules.auth.models import User
from app.modules.settings.constants import KNOWN_SETTINGS
from app.modules.settings.models import AppSetting
from scripts.seed_settings import DEFAULTS

LEGACY_SECRET = "legacy-smtp-secret"

CATEGORIES = sorted({spec.category for spec in KNOWN_SETTINGS.values()})


async def _login(client: AsyncClient, db) -> None:
    user = User(
        username="settings_web_admin",
        email="settings_web_admin@example.com",
        full_name="Settings Web Admin",
        hashed_password=hash_password("password123"),
        is_superuser=True,
    )
    db.add(user)
    await db.commit()

    r = await client.post(
        "/api/v1/auth/login",
        json={"username": "settings_web_admin", "password": "password123"},
    )
    assert r.status_code == 200, r.text


async def _seed_settings(db) -> None:
    for key, spec in KNOWN_SETTINGS.items():
        value = DEFAULTS.get(key, "")
        if spec.is_secret and key == "email.smtp_password":
            value = LEGACY_SECRET
        db.add(
            AppSetting(
                key=key,
                value=value,
                category=spec.category,
                description=spec.description,
                is_secret=spec.is_secret,
            )
        )
    await db.commit()


async def _csrf(client: AsyncClient, path: str) -> str:
    page = await client.get(path)
    assert page.status_code == 200, page.text
    token = client.cookies.get(settings.CSRF_COOKIE_NAME)
    assert token
    return token


def _tag(body: str, attr: str) -> str:
    """Return the full opening tag that owns `id="<attr>"`."""
    match = re.search(rf'<[^>]*\bid="{re.escape(attr)}"[^>]*>', body)
    assert match, f"tag with id={attr!r} not found"
    return match.group(0)


@pytest.mark.asyncio
async def test_settings_page_renders_tabbed_workspace(client: AsyncClient, db):
    await _login(client, db)
    await _seed_settings(db)

    page = await client.get("/admin/settings")
    assert page.status_code == 200, page.text
    body = page.text

    # Shell: one guarded form, CSRF, search, rail, save bar.
    assert 'data-guard' in body
    assert 'data-settings' in body
    assert 'name="_csrf"' in body
    assert 'name="_tab"' in body
    assert 'data-settings-search' in body
    assert 'role="tablist"' in body
    assert 'data-settings-savebar' in body
    assert 'data-settings-submit' in body
    assert body.count('data-settings-tab="') == len(CATEGORIES)
    assert body.count('data-settings-panel="') == len(CATEGORIES)

    # Every known key must still be posted by the single form — exactly
    # once, no matter which tab is visible.
    for key in KNOWN_SETTINGS:
        assert body.count(f'name="{key}"') == 1, key

    # Boolean settings are toggle switches backed by a hidden input that
    # always carries "true"/"false".
    bool_hidden = re.search(
        r'<input type="hidden"\s+name="crm\.inquiry_auto_assign"\s+value="(true|false)"',
        body,
    )
    assert bool_hidden, "boolean hidden input missing"
    assert "data-bool" in body

    # Secrets never reach the HTML; the field is a masked password input.
    assert LEGACY_SECRET not in body
    assert re.search(
        r'<input[^>]*id="setting-email\.smtp_password"[^>]*type="password"', body
    )
    assert "Configured" in body


@pytest.mark.asyncio
async def test_tab_query_opens_matching_panel(client: AsyncClient, db):
    await _login(client, db)
    await _seed_settings(db)

    page = await client.get("/admin/settings?tab=email")
    assert page.status_code == 200
    body = page.text

    assert "is-active" in _tag(body, "tab-email")
    assert "is-hidden" not in _tag(body, "panel-email")
    assert "is-hidden" in _tag(body, "panel-business")
    assert 'aria-selected="false"' in _tag(body, "tab-business")
    assert 'tabindex="-1"' in _tag(body, "tab-business")


@pytest.mark.asyncio
async def test_save_keeps_tab_and_blank_secret(client: AsyncClient, db):
    await _login(client, db)
    await _seed_settings(db)
    csrf = await _csrf(client, "/admin/settings?tab=email")

    r = await client.post(
        "/admin/settings",
        data={
            "_csrf": csrf,
            "_tab": "email",
            "business.name": "NOCTRA Renamed",
            "email.smtp_password": "",
            "crm.inquiry_auto_assign": "true",
        },
        follow_redirects=False,
    )

    assert r.status_code == 303, r.text
    assert r.headers["location"] == "/admin/settings?saved=1&tab=email"

    rows = {
        row.key: row
        for row in (await db.execute(select(AppSetting))).scalars().all()
    }
    assert rows["business.name"].value == "NOCTRA Renamed"
    assert rows["crm.inquiry_auto_assign"].value == "true"
    # A blank secret submission must never wipe the stored value.
    assert rows["email.smtp_password"].value == LEGACY_SECRET

    page = await client.get(r.headers["location"])
    assert page.status_code == 200
    assert "Settings saved" in page.text
    assert "is-active" in _tag(page.text, "tab-email")


@pytest.mark.asyncio
async def test_invalid_tab_is_not_echoed_into_redirect(client: AsyncClient, db):
    await _login(client, db)
    await _seed_settings(db)
    csrf = await _csrf(client, "/admin/settings")

    r = await client.post(
        "/admin/settings",
        data={
            "_csrf": csrf,
            "_tab": '"><script>alert(1)</script>',
            "business.name": "NOCTRA",
        },
        follow_redirects=False,
    )

    assert r.status_code == 303, r.text
    assert "tab=" not in r.headers["location"]
    assert "script" not in r.headers["location"]
