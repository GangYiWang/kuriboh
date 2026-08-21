from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentPrincipal, get_current_principal
from app.db.session import get_db
from app.swiss.schemas import (
    GenerateRoundRequest,
    MatchResponse,
    MyMatchResponse,
    ResolveMatchRequest,
    RoundResponse,
    SubmitResultRequest,
    SwapPlayersRequest,
    SwissOverviewResponse,
    WithdrawResponse,
)
from app.swiss.service import SwissService
from app.tournaments.ownership import require_match_owner, require_tournament_owner

router = APIRouter(tags=["swiss"])
admin_router = APIRouter(prefix="/admin", tags=["admin-swiss"])
Authenticated = Annotated[CurrentPrincipal, Depends(get_current_principal)]


@router.get("/tournaments/{tournament_id}/swiss", response_model=SwissOverviewResponse)
def swiss_overview(
    tournament_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> SwissOverviewResponse:
    return SwissService(db).overview(tournament_id)


@router.get("/tournaments/{tournament_id}/swiss/rounds", response_model=list[RoundResponse])
def published_rounds(
    tournament_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> list[RoundResponse]:
    return SwissService(db).published_rounds(tournament_id)


@router.get("/tournaments/{tournament_id}/matches/me", response_model=list[MyMatchResponse])
def my_matches(
    tournament_id: UUID,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> list[MyMatchResponse]:
    return SwissService(db).my_matches(tournament_id, principal.user_id)


@router.post("/matches/{match_id}/submissions", response_model=MyMatchResponse)
def submit_match_result(
    match_id: UUID,
    request: SubmitResultRequest,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> MyMatchResponse:
    return SwissService(db).submit_result(match_id, principal.user_id, request.result)


@admin_router.get("/tournaments/{tournament_id}/swiss/rounds", response_model=list[RoundResponse])
def admin_rounds(
    tournament_id: UUID,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> list[RoundResponse]:
    require_tournament_owner(db, tournament_id, principal.user_id)
    return SwissService(db).admin_rounds(tournament_id)


@admin_router.post("/tournaments/{tournament_id}/swiss/rounds/generate", response_model=RoundResponse)
def generate_round(
    tournament_id: UUID,
    request: GenerateRoundRequest,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> RoundResponse:
    require_tournament_owner(db, tournament_id, principal.user_id)
    return SwissService(db).generate_preview(
        tournament_id,
        principal.user_id,
        seed=request.seed,
        regenerate=False,
    )


@admin_router.post("/tournaments/{tournament_id}/swiss/rounds/regenerate", response_model=RoundResponse)
def regenerate_round(
    tournament_id: UUID,
    request: GenerateRoundRequest,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> RoundResponse:
    require_tournament_owner(db, tournament_id, principal.user_id)
    return SwissService(db).generate_preview(
        tournament_id,
        principal.user_id,
        seed=request.seed,
        regenerate=True,
    )


@admin_router.post(
    "/tournaments/{tournament_id}/swiss/rounds/{round_id}/swap",
    response_model=RoundResponse,
)
def swap_round_players(
    tournament_id: UUID,
    round_id: UUID,
    request: SwapPlayersRequest,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> RoundResponse:
    require_tournament_owner(db, tournament_id, principal.user_id)
    return SwissService(db).swap_players(
        tournament_id,
        round_id,
        request.first_participant_id,
        request.second_participant_id,
        principal.user_id,
    )


@admin_router.post(
    "/tournaments/{tournament_id}/swiss/rounds/{round_id}/publish",
    response_model=RoundResponse,
)
def publish_round(
    tournament_id: UUID,
    round_id: UUID,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> RoundResponse:
    require_tournament_owner(db, tournament_id, principal.user_id)
    return SwissService(db).publish_round(tournament_id, round_id, principal.user_id)


@admin_router.post("/matches/{match_id}/resolve", response_model=MatchResponse)
def resolve_match(
    match_id: UUID,
    request: ResolveMatchRequest,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> MatchResponse:
    require_match_owner(db, match_id, principal.user_id)
    return SwissService(db).resolve_match(match_id, request.winner_id, request.reason, principal.user_id)


@admin_router.post(
    "/tournaments/{tournament_id}/participants/{participant_id}/withdraw",
    response_model=WithdrawResponse,
)
def withdraw_participant(
    tournament_id: UUID,
    participant_id: UUID,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> WithdrawResponse:
    require_tournament_owner(db, tournament_id, principal.user_id)
    return SwissService(db).withdraw(tournament_id, participant_id, principal.user_id)
