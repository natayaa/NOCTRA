from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID | None
    action: str
    table_name: str
    record_id: str
    created_at: datetime
    ip_address: str | None


class AuditLogDetail(AuditLogItem):
    old_data: dict | None
    new_data: dict | None
    user_agent: str | None