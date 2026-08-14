from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from app.registrations.models import RegistrationStatus


class RegistrationApplyRequest(BaseModel):
    nickname_matches_game: bool
    accepts_rules: bool

    @model_validator(mode="after")
    def confirmations_required(self) -> "RegistrationApplyRequest":
        if not self.nickname_matches_game or not self.accepts_rules:
            raise ValueError("请确认游戏内昵称一致并同意赛事规则")
        return self


class RegistrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tournament_id: UUID
    user_id: UUID
    nickname: str
    status: RegistrationStatus
    reviewed_by_id: UUID | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RegistrationListResponse(BaseModel):
    items: list[RegistrationResponse]
    total: int


class RegistrationBulkApproveResponse(BaseModel):
    approved_count: int
