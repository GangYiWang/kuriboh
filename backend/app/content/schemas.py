from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BanlistCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    content_html: str = Field(min_length=1, max_length=100_000)


class BanlistResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    version: str
    major_version: int
    minor_version: int
    title: str
    content_html: str
    published_at: datetime


class BanlistListResponse(BaseModel):
    items: list[BanlistResponse]
    total: int


class AnnouncementCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    content_html: str = Field(min_length=1, max_length=100_000)
    is_pinned: bool = False


class AnnouncementUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=160)
    content_html: str | None = Field(default=None, min_length=1, max_length=100_000)
    is_pinned: bool | None = None


class AnnouncementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    content_html: str
    is_pinned: bool
    published_at: datetime
    updated_at: datetime


class AnnouncementListResponse(BaseModel):
    items: list[AnnouncementResponse]
    total: int


class ImageUploadResponse(BaseModel):
    url: str
    width: int
    height: int
    content_type: str
