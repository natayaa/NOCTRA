"""Settings presentation tests — masking must never mutate ORM rows."""

from types import SimpleNamespace

import pytest

import app.web.admin.settings as settings_routes
from app.web.admin.settings import to_setting_view


def _row(**overrides):
    data = {
        "key": "email.smtp_password",
        "value": "s3cret",
        "category": "email",
        "description": "SMTP password",
        "is_secret": True,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_secret_is_masked_and_source_row_is_untouched():
    row = _row()

    view = to_setting_view(row)

    assert view.value == "***"
    # Regression: the settings GET used to assign "***" to the ORM row,
    # which the request-scoped session then committed.
    assert row.value == "s3cret"


def test_unset_secret_stays_unset():
    view = to_setting_view(_row(value=None))

    assert view.value is None


def test_plain_setting_value_is_preserved():
    view = to_setting_view(
        _row(key="business.name", value="NOCTRA", is_secret=False)
    )

    assert view.value == "NOCTRA"
    assert view.is_secret is False


def test_missing_category_falls_back_to_general():
    view = to_setting_view(_row(category=None))

    assert view.category == "general"


def test_view_is_detached_from_the_row():
    row = _row()
    view = to_setting_view(row)

    row.value = "changed-after-view"

    assert view.value == "***"


@pytest.mark.asyncio
async def test_list_view_does_not_mutate_rows(monkeypatch):
    row = _row()

    class _Scalars:
        def all(self):
            return [row]

    class _Result:
        def scalars(self):
            return _Scalars()

    class _DB:
        async def execute(self, _stmt):
            return _Result()

    captured = {}

    def _render(_request, _template, context):
        captured.update(context)
        return "rendered"

    monkeypatch.setattr(
        settings_routes, "templates", SimpleNamespace(render=_render)
    )

    result = await settings_routes.list_view(
        request=SimpleNamespace(query_params={}),
        db=_DB(),
        _=None,
        current=None,
    )

    assert result == "rendered"
    assert row.value == "s3cret"
    assert captured["settings_groups"]["email"][0].value == "***"
