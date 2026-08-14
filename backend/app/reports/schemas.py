from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.reports.models import WeeklyReportStatus


class WeeklyReportResponse(BaseModel):
    id: UUID
    tournament_id: UUID
    tournament_name: str
    status: WeeklyReportStatus
    snapshot_content: dict[str, Any]
    published_at: datetime | None
    created_at: datetime


class WeeklyReportListResponse(BaseModel):
    items: list[WeeklyReportResponse]
    total: int
