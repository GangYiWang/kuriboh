from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentPrincipal, get_current_principal, require_roles
from app.auth.roles import Role
from app.db.session import get_db
from app.messages.schemas import (
    MessageListResponse,
    MessageResponse,
    MessageSendRequest,
    MessageSendResponse,
    UnreadCountResponse,
)
from app.messages.service import MessageService
from app.tournaments.ownership import require_tournament_owner


router = APIRouter(tags=["messages"])
admin_router = APIRouter(prefix="/admin", tags=["admin-messages"])
Authenticated = Annotated[CurrentPrincipal, Depends(get_current_principal)]
Admin = Annotated[CurrentPrincipal, Depends(require_roles(Role.TOURNAMENT_ADMIN))]


@router.get("/messages", response_model=MessageListResponse)
def list_messages(
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
):
    return MessageService(db).list_for_user(principal.user_id, offset=offset, limit=limit)


@router.get("/messages/unread-count", response_model=UnreadCountResponse)
def unread_count(principal: Authenticated, db: Annotated[Session, Depends(get_db)]):
    return UnreadCountResponse(unread_count=MessageService(db).repository.unread_count(principal.user_id))


@router.post("/messages/{message_id}/read", response_model=MessageResponse)
def read_message(message_id: UUID, principal: Authenticated, db: Annotated[Session, Depends(get_db)]):
    return MessageResponse.model_validate(MessageService(db).mark_read(message_id, principal.user_id))


@router.post("/messages/read-all", response_model=UnreadCountResponse)
def read_all_messages(principal: Authenticated, db: Annotated[Session, Depends(get_db)]):
    MessageService(db).mark_all_read(principal.user_id)
    return UnreadCountResponse(unread_count=0)


@admin_router.post("/tournaments/{tournament_id}/messages", response_model=MessageSendResponse)
def send_tournament_notice(
    tournament_id: UUID,
    request: MessageSendRequest,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
):
    require_tournament_owner(db, tournament_id, principal.user_id)
    return MessageService(db).send_tournament_notice(
        tournament_id,
        title=request.title,
        body=request.body,
        request_id=request.request_id,
        operator_id=principal.user_id,
    )


@admin_router.post("/messages/platform", response_model=MessageSendResponse)
def send_platform_notice(
    request: MessageSendRequest,
    principal: Admin,
    db: Annotated[Session, Depends(get_db)],
):
    return MessageService(db).send_platform_notice(
        title=request.title,
        body=request.body,
        request_id=request.request_id,
        operator_id=principal.user_id,
    )
