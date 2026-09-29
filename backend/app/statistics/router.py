from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentPrincipal, require_roles
from app.auth.roles import Role
from app.db.session import get_db
from app.statistics.schemas import AdminPlayerRankingListResponse
from app.statistics.service import TournamentStatisticsService


router = APIRouter(prefix="/admin", tags=["admin-statistics"])
PlatformAdmin = Annotated[CurrentPrincipal, Depends(require_roles(Role.PLATFORM_ADMIN))]


@router.get("/player-rankings", response_model=AdminPlayerRankingListResponse)
def list_player_rankings(
    _: PlatformAdmin,
    db: Annotated[Session, Depends(get_db)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=50)] = None,
) -> AdminPlayerRankingListResponse:
    return TournamentStatisticsService(db).player_rankings(
        offset=offset,
        limit=limit,
        search=search,
    )
