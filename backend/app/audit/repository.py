from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.audit.models import AuditLog


class AuditLogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(
        self,
        *,
        offset: int,
        limit: int,
        tournament_id: UUID | None = None,
        action_type: str | None = None,
    ) -> tuple[list[AuditLog], int]:
        filters = []
        if tournament_id is not None:
            filters.append(AuditLog.tournament_id == tournament_id)
        if action_type:
            filters.append(AuditLog.action_type == action_type)
        items = list(self.db.scalars(
            select(AuditLog)
            .where(*filters)
            .options(selectinload(AuditLog.operator))
            .order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        ))
        total = self.db.scalar(select(func.count()).select_from(AuditLog).where(*filters)) or 0
        return items, int(total)
