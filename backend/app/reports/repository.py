from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.reports.models import WeeklyReport, WeeklyReportStatus


class WeeklyReportRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def for_tournament(self, tournament_id: UUID, *, for_update: bool = False) -> WeeklyReport | None:
        statement = select(WeeklyReport).where(
            WeeklyReport.tournament_id == tournament_id
        ).options(selectinload(WeeklyReport.tournament))
        if for_update:
            statement = statement.with_for_update()
        return self.db.scalar(statement)

    def get(self, report_id: UUID, *, published_only: bool = False, for_update: bool = False) -> WeeklyReport | None:
        statement = select(WeeklyReport).where(WeeklyReport.id == report_id)
        if published_only:
            statement = statement.where(WeeklyReport.status == WeeklyReportStatus.PUBLISHED.value)
        statement = statement.options(selectinload(WeeklyReport.tournament))
        if for_update:
            statement = statement.with_for_update()
        return self.db.scalar(statement)

    def list_published(self, offset: int, limit: int) -> tuple[list[WeeklyReport], int]:
        filters = [WeeklyReport.status == WeeklyReportStatus.PUBLISHED.value]
        items = list(self.db.scalars(select(WeeklyReport).where(*filters).options(
            selectinload(WeeklyReport.tournament)
        ).order_by(WeeklyReport.published_at.desc()).offset(offset).limit(limit)))
        total = self.db.scalar(select(func.count()).select_from(WeeklyReport).where(*filters)) or 0
        return items, total
