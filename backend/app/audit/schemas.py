from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: UUID
    operator_id: UUID
    operator_nickname: str
    tournament_id: UUID | None
    action_type: str
    target_type: str
    target_id: str
    before_json: dict[str, Any] | None
    after_json: dict[str, Any] | None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
