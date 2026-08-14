from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentPrincipal, get_current_principal
from app.core.errors import AppError
from app.db.session import get_db
from app.reports.repository import WeeklyReportRepository
from app.reports.schemas import WeeklyReportListResponse, WeeklyReportResponse
from app.reports.service import WeeklyReportService, report_response
from app.tournaments.ownership import require_report_owner, require_tournament_owner


router = APIRouter(tags=["reports"])
admin_router = APIRouter(prefix="/admin", tags=["admin-reports"])
Authenticated = Annotated[CurrentPrincipal, Depends(get_current_principal)]


@router.get("/reports", response_model=WeeklyReportListResponse)
def list_reports(
    db: Annotated[Session, Depends(get_db)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    items, total = WeeklyReportRepository(db).list_published(offset, limit)
    return WeeklyReportListResponse(items=[report_response(item) for item in items], total=total)


@router.get("/reports/{report_id}", response_model=WeeklyReportResponse)
def get_report(report_id: UUID, db: Annotated[Session, Depends(get_db)]):
    item = WeeklyReportRepository(db).get(report_id, published_only=True)
    if item is None:
        raise AppError("REPORT_NOT_FOUND", "周报不存在", status_code=404)
    return report_response(item)


@admin_router.get("/tournaments/{tournament_id}/report", response_model=WeeklyReportResponse)
def admin_tournament_report(tournament_id: UUID, principal: Authenticated, db: Annotated[Session, Depends(get_db)]):
    require_tournament_owner(db, tournament_id, principal.user_id)
    item = WeeklyReportRepository(db).for_tournament(tournament_id)
    if item is None:
        raise AppError("REPORT_NOT_FOUND", "尚未生成周报草稿", status_code=404)
    return report_response(item)


@admin_router.post("/tournaments/{tournament_id}/reports/generate", response_model=WeeklyReportResponse)
def generate_report(tournament_id: UUID, principal: Authenticated, db: Annotated[Session, Depends(get_db)]):
    require_tournament_owner(db, tournament_id, principal.user_id)
    return report_response(WeeklyReportService(db).generate(tournament_id, principal.user_id))


@admin_router.post("/reports/{report_id}/publish", response_model=WeeklyReportResponse)
def publish_report(report_id: UUID, principal: Authenticated, db: Annotated[Session, Depends(get_db)]):
    require_report_owner(db, report_id, principal.user_id)
    return report_response(WeeklyReportService(db).publish(report_id, principal.user_id))
