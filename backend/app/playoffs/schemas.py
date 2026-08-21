from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.matches.models import MatchStatus, SubmittedResult
from app.playoffs.models import PlayoffRoundStatus


class PlayoffMatchResponse(BaseModel):
    id: UUID
    stage_no: int
    table_no: int
    seed_a: int
    seed_b: int
    player_a_id: UUID
    player_a_nickname: str
    player_b_id: UUID
    player_b_nickname: str
    winner_id: UUID | None
    status: MatchStatus
    result_source: str | None
    result_locked: bool
    player_a_result: SubmittedResult | None = None
    player_b_result: SubmittedResult | None = None


class MyPlayoffMatchResponse(PlayoffMatchResponse):
    my_participant_id: UUID
    my_submission: SubmittedResult | None
    opponent_submission: SubmittedResult | None
    opponent_submitted: bool


class PlayoffRoundResponse(BaseModel):
    id: UUID
    stage_no: int
    bracket_size: int
    name: str
    status: PlayoffRoundStatus
    published_at: datetime | None
    completed_at: datetime | None
    matches: list[PlayoffMatchResponse]


class PlayoffOverviewResponse(BaseModel):
    playoff_size: int
    rounds: list[PlayoffRoundResponse]
    champion_id: UUID | None
    champion_nickname: str | None
    awaiting_tournament_end: bool


class PlayoffSubmitResultRequest(BaseModel):
    result: SubmittedResult


class ForfeitRequest(BaseModel):
    loser_id: UUID
    reason: str | None = Field(default=None, max_length=500)
