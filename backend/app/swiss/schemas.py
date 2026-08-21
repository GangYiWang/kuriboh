from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.matches.models import MatchStatus, SubmittedResult
from app.swiss.models import SwissRoundStatus


class GenerateRoundRequest(BaseModel):
    seed: int | None = None


class SwapPlayersRequest(BaseModel):
    first_participant_id: UUID
    second_participant_id: UUID


class SubmitResultRequest(BaseModel):
    result: SubmittedResult


class ResolveMatchRequest(BaseModel):
    winner_id: UUID
    reason: str | None = Field(default=None, max_length=500)


class MatchResponse(BaseModel):
    id: UUID
    round_no: int
    table_no: int
    player_a_id: UUID
    player_a_nickname: str
    player_b_id: UUID | None
    player_b_nickname: str | None
    winner_id: UUID | None
    status: MatchStatus
    result_source: str | None
    result_locked: bool
    warnings: list[str] = Field(default_factory=list)
    player_a_result: SubmittedResult | None = None
    player_b_result: SubmittedResult | None = None


class MyMatchResponse(MatchResponse):
    my_participant_id: UUID
    my_submission: SubmittedResult | None
    opponent_submission: SubmittedResult | None
    opponent_submitted: bool


class RoundResponse(BaseModel):
    id: UUID
    round_no: int
    status: SwissRoundStatus
    published_at: datetime | None
    completed_at: datetime | None
    matches: list[MatchResponse]


class RankingResponse(BaseModel):
    participant_id: UUID
    nickname: str
    participant_status: str
    rank: int
    wins: int
    losses: int
    omw: float
    loss_round_score: int


class SwissOverviewResponse(BaseModel):
    current_round_no: int
    current_round_status: SwissRoundStatus | None
    completed_rounds: int
    total_rounds: int
    ranking_round_no: int
    rankings: list[RankingResponse]


class WithdrawResponse(BaseModel):
    participant_id: UUID
    status: str
    after_round_no: int
