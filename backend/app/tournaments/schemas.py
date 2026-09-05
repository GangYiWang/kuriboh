from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.tournaments.models import TournamentStatus


def validate_power_of_two(value: int | None) -> int | None:
    if value is not None and (value < 2 or value & (value - 1)):
        raise ValueError("淘汰赛晋级人数必须是 2 的幂")
    return value


class TournamentCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=10_000)
    planned_start_at: datetime | None = None
    max_players: int | None = Field(default=None, ge=2, le=1024)
    swiss_rounds: int | None = Field(default=None, ge=1, le=20)
    playoff_size: int | None = Field(default=None, ge=2, le=1024)
    banlist_version_id: UUID | None = None

    _validate_playoff_size = field_validator("playoff_size")(validate_power_of_two)


class TournamentUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=10_000)
    planned_start_at: datetime | None = None
    max_players: int | None = Field(default=None, ge=2, le=1024)
    swiss_rounds: int | None = Field(default=None, ge=1, le=20)
    playoff_size: int | None = Field(default=None, ge=2, le=1024)
    banlist_version_id: UUID | None = None

    _validate_playoff_size = field_validator("playoff_size")(validate_power_of_two)


class TournamentCancelRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class TournamentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str | None
    created_by_id: UUID
    name: str
    description: str
    planned_start_at: datetime | None
    max_players: int | None
    swiss_rounds: int | None
    playoff_size: int | None
    banlist_version_id: UUID | None
    banlist_version: str | None
    status: TournamentStatus
    published_at: datetime | None
    started_at: datetime | None
    ended_at: datetime | None
    canceled_at: datetime | None
    cancellation_reason: str | None
    approved_count: int
    pending_count: int
    created_at: datetime
    updated_at: datetime


class TournamentListResponse(BaseModel):
    items: list[TournamentResponse]
    total: int


class ParticipantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    nickname_snapshot: str
    status: str
    bye_count: int


class MyTournamentMatchSummary(BaseModel):
    id: UUID
    stage: str
    round_no: int
    table_no: int
    opponent_nickname: str | None
    status: str


class MyTournamentRankingSummary(BaseModel):
    rank: int
    wins: int
    losses: int


class MyTournamentResponse(BaseModel):
    id: UUID
    name: str
    status: TournamentStatus
    planned_start_at: datetime | None
    registration_status: str
    participant_status: str | None
    current_match: MyTournamentMatchSummary | None
    ranking: MyTournamentRankingSummary | None
    report_id: UUID | None


class MyTournamentListResponse(BaseModel):
    items: list[MyTournamentResponse]
    total: int
