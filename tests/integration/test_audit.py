"""Audit log tests."""

import pytest
from sqlalchemy import select

from app.core.constants import AuditAction
from app.modules.audit.models import AuditLog
from app.modules.audit.service import AuditService


@pytest.mark.asyncio
async def test_audit_log_writes_row(db):
    service = AuditService(db)
    await service.log(
        action=AuditAction.CREATE,
        table_name="test_table",
        record_id="abc-123",
        new_data={"foo": "bar"},
    )
    await db.commit()

    row = (
        await db.execute(
            select(AuditLog).where(AuditLog.record_id == "abc-123")
        )
    ).scalar_one()
    assert row.action == AuditAction.CREATE.value
    assert row.table_name == "test_table"
    assert row.new_data == {"foo": "bar"}


def test_audit_service_is_append_only():
    assert not hasattr(AuditService, "update")
    assert not hasattr(AuditService, "delete")