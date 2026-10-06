"""Settings / configuration tests."""

import pytest

from app.core.config import Settings, settings


def test_settings_loads():
    assert settings.APP_NAME == "NOCTRA Autoworks"
    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert settings.sync_database_url.startswith("postgresql://")


def test_weak_secret_rejected():
    with pytest.raises(ValueError):
        Settings(APP_SECRET_KEY="secret")
    with pytest.raises(ValueError):
        Settings(APP_SECRET_KEY="changeme")


def test_short_secret_rejected():
    with pytest.raises(ValueError):
        Settings(APP_SECRET_KEY="tooshort")


def test_valid_secret_accepted():
    s = Settings(APP_SECRET_KEY="a" * 64)
    assert len(s.APP_SECRET_KEY) == 64


def test_database_url_composition():
    s = Settings(
        APP_SECRET_KEY="a" * 64,
        POSTGRES_USER="foo",
        POSTGRES_PASSWORD="bar",
        POSTGRES_HOST="db.example",
        POSTGRES_PORT=5433,
        POSTGRES_DB="mydb",
    )
    assert s.database_url == "postgresql+asyncpg://foo:bar@db.example:5433/mydb"
    assert s.sync_database_url == "postgresql://foo:bar@db.example:5433/mydb"