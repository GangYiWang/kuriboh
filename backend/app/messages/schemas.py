from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.messages.models import MessageType


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: MessageType
    title: str
    body: str
    action_url: str | None
    read_at: datetime | None
    created_at: datetime


class MessageListResponse(BaseModel):
    items: list[MessageResponse]
    total: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    unread_count: int


class MessageSendRequest(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    body: str = Field(min_length=2, max_length=5000)
    request_id: UUID


class MessageSendResponse(BaseModel):
    sent_count: int
    duplicated: bool = False
