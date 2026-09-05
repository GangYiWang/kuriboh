from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentPrincipal, get_current_principal
from app.core.errors import AppError
from app.db.session import get_db
from app.registrations.repository import RegistrationRepository
from app.registrations.schemas import (
    RegistrationApplyRequest,
    RegistrationBulkApproveResponse,
    RegistrationListResponse,
    RegistrationResponse,
)
from app.registrations.service import RegistrationService, registration_response
from app.tournaments.models import TournamentStatus
from app.tournaments.repository import TournamentRepository
from app.tournaments.schemas import (
    ParticipantResponse,
    TournamentCreateRequest,
    TournamentCancelRequest,
    TournamentListResponse,
    MyTournamentListResponse,
    TournamentResponse,
    TournamentUpdateRequest,
)
from app.tournaments.service import TournamentService, tournament_response
from app.statistics.schemas import PlayerStatisticsResponse
from app.statistics.service import TournamentStatisticsService

router = APIRouter(tags=["tournaments"])
admin_router = APIRouter(prefix="/admin", tags=["admin-tournaments"])
Authenticated = Annotated[CurrentPrincipal, Depends(get_current_principal)]


def serialize_tournament(repository: TournamentRepository, item) -> TournamentResponse:
    approved, pending = repository.registration_counts(item.id)
    return tournament_response(item, approved, pending)


@router.get("/tournaments", response_model=TournamentListResponse)
def list_tournaments(
    db: Annotated[Session, Depends(get_db)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    tournament_status: Annotated[TournamentStatus | None, Query(alias="status")] = None,
    search: Annotated[str | None, Query(max_length=120)] = None,
) -> TournamentListResponse:
    repository = TournamentRepository(db)
    items, total = repository.list_public(
        offset=offset,
        limit=limit,
        status=tournament_status,
        search=search,
    )
    return TournamentListResponse(items=[serialize_tournament(repository, item) for item in items], total=total)


@router.post("/tournaments", response_model=TournamentResponse, status_code=status.HTTP_201_CREATED)
def publish_new_tournament(
    request: TournamentCreateRequest,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> TournamentResponse:
    service = TournamentService(db)
    item = service.create_and_publish(request, principal.user_id)
    return serialize_tournament(service.repository, item)


@router.get("/tournaments/code/{code}", response_model=TournamentResponse)
def get_tournament_by_code(code: str, db: Annotated[Session, Depends(get_db)]) -> TournamentResponse:
    service = TournamentService(db)
    item = service.get_by_code(code)
    return serialize_tournament(service.repository, item)


@router.get("/tournaments/{tournament_id}", response_model=TournamentResponse)
def get_tournament(tournament_id: UUID, db: Annotated[Session, Depends(get_db)]) -> TournamentResponse:
    service = TournamentService(db)
    item = service.require(tournament_id)
    if item.status == TournamentStatus.DRAFT.value:
        raise AppError("TOURNAMENT_NOT_FOUND", "赛事不存在", status_code=404)
    return serialize_tournament(service.repository, item)


@router.get("/me/tournaments", response_model=MyTournamentListResponse)
def my_tournaments(
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> MyTournamentListResponse:
    return TournamentService(db).my_tournaments(principal.user_id)


@router.get("/me/tournament-statistics", response_model=PlayerStatisticsResponse)
def my_tournament_statistics(
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> PlayerStatisticsResponse:
    return TournamentStatisticsService(db).for_user(principal.user_id)


@router.get("/me/created-tournaments", response_model=TournamentListResponse)
def my_created_tournaments(
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> TournamentListResponse:
    service = TournamentService(db)
    items, total = service.created_tournaments(principal.user_id, offset=offset, limit=limit)
    return TournamentListResponse(
        items=[serialize_tournament(service.repository, item) for item in items],
        total=total,
    )


@router.post(
    "/tournaments/{tournament_id}/registrations",
    response_model=RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
def apply_registration(
    tournament_id: UUID,
    _: RegistrationApplyRequest,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> RegistrationResponse:
    return registration_response(RegistrationService(db).apply(tournament_id, principal.user_id))


@router.get("/tournaments/{tournament_id}/registrations/me", response_model=RegistrationResponse)
def my_registration(
    tournament_id: UUID,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> RegistrationResponse:
    TournamentService(db).require(tournament_id)
    item = RegistrationRepository(db).for_user(tournament_id, principal.user_id)
    if item is None:
        raise AppError("REGISTRATION_NOT_FOUND", "尚未报名该赛事", status_code=404)
    return registration_response(item)


@router.post("/tournaments/{tournament_id}/registrations/cancel", response_model=RegistrationResponse)
def cancel_my_registration(
    tournament_id: UUID,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> RegistrationResponse:
    return registration_response(RegistrationService(db).cancel_by_player(tournament_id, principal.user_id))


@admin_router.get("/tournaments", response_model=TournamentListResponse)
def admin_list_tournaments(
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> TournamentListResponse:
    repository = TournamentRepository(db)
    items, total = repository.list_created_by(principal.user_id, offset=offset, limit=limit)
    return TournamentListResponse(items=[serialize_tournament(repository, item) for item in items], total=total)


@admin_router.post("/tournaments", response_model=TournamentResponse, status_code=status.HTTP_201_CREATED)
def create_tournament(
    request: TournamentCreateRequest,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> TournamentResponse:
    service = TournamentService(db)
    item = service.create_draft(request, principal.user_id)
    return serialize_tournament(service.repository, item)


@admin_router.get("/tournaments/{tournament_id}", response_model=TournamentResponse)
def admin_get_tournament(
    tournament_id: UUID,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> TournamentResponse:
    service = TournamentService(db)
    return serialize_tournament(service.repository, service.require_owner(tournament_id, principal.user_id))


@admin_router.patch("/tournaments/{tournament_id}", response_model=TournamentResponse)
def update_tournament(
    tournament_id: UUID,
    request: TournamentUpdateRequest,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> TournamentResponse:
    service = TournamentService(db)
    item = service.update(service.require_owner(tournament_id, principal.user_id, for_update=True), request)
    return serialize_tournament(service.repository, item)


@admin_router.post("/tournaments/{tournament_id}/publish", response_model=TournamentResponse)
def publish_tournament(
    tournament_id: UUID,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> TournamentResponse:
    service = TournamentService(db)
    service.require_owner(tournament_id, principal.user_id)
    return serialize_tournament(service.repository, service.publish(tournament_id, principal.user_id))


@admin_router.post("/tournaments/{tournament_id}/start", response_model=TournamentResponse)
def start_tournament(
    tournament_id: UUID,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> TournamentResponse:
    service = TournamentService(db)
    service.require_owner(tournament_id, principal.user_id)
    return serialize_tournament(service.repository, service.start(tournament_id, principal.user_id))


@admin_router.post("/tournaments/{tournament_id}/end", response_model=TournamentResponse)
def end_tournament(
    tournament_id: UUID,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> TournamentResponse:
    service = TournamentService(db)
    service.require_owner(tournament_id, principal.user_id)
    return serialize_tournament(service.repository, service.end(tournament_id, principal.user_id))


@admin_router.post("/tournaments/{tournament_id}/cancel", response_model=TournamentResponse)
def cancel_tournament(
    tournament_id: UUID,
    request: TournamentCancelRequest,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> TournamentResponse:
    service = TournamentService(db)
    item = service.cancel(tournament_id, principal.user_id, request.reason)
    return serialize_tournament(service.repository, item)


@admin_router.delete("/tournaments/{tournament_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tournament(
    tournament_id: UUID,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    TournamentService(db).soft_delete(tournament_id, principal.user_id)


@admin_router.get(
    "/tournaments/{tournament_id}/registrations",
    response_model=RegistrationListResponse,
)
def admin_list_registrations(
    tournament_id: UUID,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> RegistrationListResponse:
    TournamentService(db).require_owner(tournament_id, principal.user_id)
    items, total = RegistrationRepository(db).list_for_tournament(tournament_id)
    return RegistrationListResponse(items=[registration_response(item) for item in items], total=total)


@admin_router.post(
    "/tournaments/{tournament_id}/registrations/approve-pending",
    response_model=RegistrationBulkApproveResponse,
)
def approve_pending_registrations(
    tournament_id: UUID,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> RegistrationBulkApproveResponse:
    TournamentService(db).require_owner(tournament_id, principal.user_id)
    approved_count = RegistrationService(db).approve_pending(tournament_id, principal.user_id)
    return RegistrationBulkApproveResponse(approved_count=approved_count)


@admin_router.post(
    "/tournaments/{tournament_id}/registrations/{registration_id}/{action}",
    response_model=RegistrationResponse,
)
def review_registration(
    tournament_id: UUID,
    registration_id: UUID,
    action: str,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> RegistrationResponse:
    if action not in {"approve", "reject", "cancel", "restore"}:
        raise AppError("INVALID_REVIEW_ACTION", "不支持的审核操作", status_code=404)
    TournamentService(db).require_owner(tournament_id, principal.user_id)
    item = RegistrationService(db).review(tournament_id, registration_id, action, principal.user_id)
    return registration_response(item)


@admin_router.get(
    "/tournaments/{tournament_id}/participants",
    response_model=list[ParticipantResponse],
)
def admin_list_participants(
    tournament_id: UUID,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> list[ParticipantResponse]:
    service = TournamentService(db)
    service.require_owner(tournament_id, principal.user_id)
    return [ParticipantResponse.model_validate(item) for item in service.repository.participants(tournament_id)]
