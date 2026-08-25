from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentPrincipal, require_roles
from app.auth.roles import Role
from app.content.repository import AnnouncementRepository, BanlistRepository
from app.content.schemas import (
    AnnouncementCreateRequest,
    AnnouncementListResponse,
    AnnouncementResponse,
    AnnouncementUpdateRequest,
    BanlistCreateRequest,
    BanlistListResponse,
    BanlistResponse,
    ImageUploadResponse,
)
from app.content.service import AnnouncementService, BanlistService
from app.content.storage import LocalImageStorage
from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import get_db

router = APIRouter(tags=["content"])
admin_router = APIRouter(prefix="/admin", tags=["admin-content"])
PlatformAdmin = Annotated[CurrentPrincipal, Depends(require_roles(Role.PLATFORM_ADMIN))]


@router.get("/banlists", response_model=BanlistListResponse)
def list_banlists(
    db: Annotated[Session, Depends(get_db)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> BanlistListResponse:
    items, total = BanlistRepository(db).list(offset, limit)
    return BanlistListResponse(items=[BanlistResponse.model_validate(item) for item in items], total=total)


@router.get("/banlists/current", response_model=BanlistResponse)
def current_banlist(db: Annotated[Session, Depends(get_db)]) -> BanlistResponse:
    item = BanlistRepository(db).latest()
    if item is None:
        raise AppError("BANLIST_NOT_FOUND", "暂无已发布禁卡表", status_code=404)
    return BanlistResponse.model_validate(item)


@router.get("/banlists/{item_id}", response_model=BanlistResponse)
def get_banlist(item_id: UUID, db: Annotated[Session, Depends(get_db)]) -> BanlistResponse:
    item = BanlistRepository(db).get(item_id)
    if item is None:
        raise AppError("BANLIST_NOT_FOUND", "禁卡表版本不存在", status_code=404)
    return BanlistResponse.model_validate(item)


@router.get("/announcements", response_model=AnnouncementListResponse)
def list_announcements(
    db: Annotated[Session, Depends(get_db)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AnnouncementListResponse:
    items, total = AnnouncementRepository(db).list(offset, limit)
    return AnnouncementListResponse(items=items, total=total)


@router.get("/announcements/{item_id}", response_model=AnnouncementResponse)
def get_announcement(item_id: UUID, db: Annotated[Session, Depends(get_db)]) -> AnnouncementResponse:
    item = AnnouncementRepository(db).get(item_id)
    if item is None:
        raise AppError("ANNOUNCEMENT_NOT_FOUND", "公告不存在", status_code=404)
    return AnnouncementResponse.model_validate(item)


@admin_router.post("/banlists", response_model=BanlistResponse, status_code=status.HTTP_201_CREATED)
def publish_banlist(
    request: BanlistCreateRequest,
    principal: PlatformAdmin,
    db: Annotated[Session, Depends(get_db)],
) -> BanlistResponse:
    return BanlistResponse.model_validate(BanlistService(db).publish(
        title=request.title,
        content_html=request.content_html,
        user_id=principal.user_id,
    ))


@admin_router.post("/announcements", response_model=AnnouncementResponse, status_code=status.HTTP_201_CREATED)
def publish_announcement(
    request: AnnouncementCreateRequest,
    principal: PlatformAdmin,
    db: Annotated[Session, Depends(get_db)],
) -> AnnouncementResponse:
    return AnnouncementResponse.model_validate(AnnouncementService(db).publish(
        title=request.title,
        content_html=request.content_html,
        is_pinned=request.is_pinned,
        user_id=principal.user_id,
    ))


@admin_router.patch("/announcements/{item_id}", response_model=AnnouncementResponse)
def update_announcement(
    item_id: UUID,
    request: AnnouncementUpdateRequest,
    principal: PlatformAdmin,
    db: Annotated[Session, Depends(get_db)],
) -> AnnouncementResponse:
    service = AnnouncementService(db)
    item = service.repository.get(item_id)
    if item is None:
        raise AppError("ANNOUNCEMENT_NOT_FOUND", "公告不存在", status_code=404)
    return AnnouncementResponse.model_validate(service.update(
        item,
        title=request.title,
        content_html=request.content_html,
        is_pinned=request.is_pinned,
        operator_id=principal.user_id,
    ))


@admin_router.post("/uploads/images", response_model=ImageUploadResponse)
async def upload_image(
    _: PlatformAdmin,
    image: Annotated[UploadFile, File()],
) -> ImageUploadResponse:
    content = await image.read(get_settings().upload_max_bytes + 1)
    url, width, height, content_type = LocalImageStorage().save(content)
    return ImageUploadResponse(url=url, width=width, height=height, content_type=content_type)
