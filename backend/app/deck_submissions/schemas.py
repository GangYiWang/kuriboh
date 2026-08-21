from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.deck_submissions.models import DeckSubmissionStatus


class DeckSubmissionResponse(BaseModel):
    id: UUID
    tournament_id: UUID
    participant_id: UUID
    user_id: UUID
    nickname: str
    placement: int
    image_url: str | None
    status: DeckSubmissionStatus
    review_note: str | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DeckSubmissionListResponse(BaseModel):
    items: list[DeckSubmissionResponse]
    approved_count: int
    required_count: int = 4


class DeckReturnRequest(BaseModel):
    reason: str = Field(default="", max_length=500)
