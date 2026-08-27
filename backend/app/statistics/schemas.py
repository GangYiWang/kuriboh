from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.registrations.models import ParticipantStatus
from app.statistics.models import TournamentFinishLevel


class TournamentResultHistoryItem(BaseModel):
    tournament_id: UUID
    tournament_name: str
    ended_at: datetime
    participant_status: ParticipantStatus
    finish_level: TournamentFinishLevel
    placement: int | None
    swiss_rank: int | None
    wins: int
    losses: int
    bye_count: int
    points_awarded: int


class PlayerStatisticsResponse(BaseModel):
    tournament_count: int
    total_points: int
    champion_count: int
    runner_up_count: int
    top_4_count: int
    top_8_count: int
    total_wins: int
    total_losses: int
    total_byes: int
    win_rate: float
    results: list[TournamentResultHistoryItem]
