from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentPrincipal, get_current_principal
from app.db.session import get_db
from app.playoffs.schemas import (
    ForfeitRequest,
    MyPlayoffMatchResponse,
    PlayoffMatchResponse,
    PlayoffOverviewResponse,
    PlayoffRoundResponse,
    PlayoffSubmitResultRequest,
)
from app.playoffs.service import PlayoffService
from app.tournaments.ownership import require_match_owner, require_tournament_owner

router = APIRouter(tags=["playoffs"])
admin_router = APIRouter(prefix="/admin", tags=["admin-playoffs"])
Authenticated = Annotated[CurrentPrincipal, Depends(get_current_principal)]


@router.get("/tournaments/{tournament_id}/playoffs", response_model=PlayoffOverviewResponse)
def playoff_overview(
    tournament_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> PlayoffOverviewResponse:
    return PlayoffService(db).overview(tournament_id)


@router.get("/tournaments/{tournament_id}/playoffs/matches/me", response_model=list[MyPlayoffMatchResponse])
def my_playoff_matches(
    tournament_id: UUID,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> list[MyPlayoffMatchResponse]:
    return PlayoffService(db).my_matches(tournament_id, principal.user_id)


@router.post("/playoffs/matches/{match_id}/submissions", response_model=MyPlayoffMatchResponse)
def submit_playoff_result(
    match_id: UUID,
    request: PlayoffSubmitResultRequest,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> MyPlayoffMatchResponse:
    return PlayoffService(db).submit_result(match_id, principal.user_id, request.result)


@admin_router.get("/tournaments/{tournament_id}/playoffs", response_model=PlayoffOverviewResponse)
def admin_playoff_overview(
    tournament_id: UUID,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> PlayoffOverviewResponse:
    require_tournament_owner(db, tournament_id, principal.user_id)
    return PlayoffService(db).overview(tournament_id, admin=True)


@admin_router.post("/tournaments/{tournament_id}/playoffs/generate", response_model=PlayoffRoundResponse)
def generate_playoff_stage(
    tournament_id: UUID,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> PlayoffRoundResponse:
    require_tournament_owner(db, tournament_id, principal.user_id)
    return PlayoffService(db).generate_preview(tournament_id, principal.user_id)


@admin_router.post(
    "/tournaments/{tournament_id}/playoffs/rounds/{round_id}/publish",
    response_model=PlayoffRoundResponse,
)
def publish_playoff_stage(
    tournament_id: UUID,
    round_id: UUID,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> PlayoffRoundResponse:
    require_tournament_owner(db, tournament_id, principal.user_id)
    return PlayoffService(db).publish_round(tournament_id, round_id, principal.user_id)


@admin_router.post("/playoffs/matches/{match_id}/forfeit", response_model=PlayoffMatchResponse)
def forfeit_playoff_match(
    match_id: UUID,
    request: ForfeitRequest,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> PlayoffMatchResponse:
    require_match_owner(db, match_id, principal.user_id)
    return PlayoffService(db).forfeit(match_id, request.loser_id, request.reason, principal.user_id)
