from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.audit.repository import AuditLogRepository
from app.audit.schemas import AuditLogListResponse, AuditLogResponse
from app.auth.dependencies import CurrentPrincipal, require_roles
from app.auth.roles import Role
from app.db.session import get_db


router = APIRouter(prefix="/admin", tags=["admin-audit"])
Admin = Annotated[CurrentPrincipal, Depends(require_roles(Role.TOURNAMENT_ADMIN))]


@router.get("/audit-logs", response_model=AuditLogListResponse)
def list_audit_logs(
    _: Admin,
    db: Annotated[Session, Depends(get_db)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    tournament_id: UUID | None = None,
    action_type: Annotated[str | None, Query(max_length=64)] = None,
):
    items, total = AuditLogRepository(db).list(
        offset=offset,
        limit=limit,
        tournament_id=tournament_id,
        action_type=action_type,
    )
    return AuditLogListResponse(
        items=[AuditLogResponse(
            id=item.id,
            operator_id=item.operator_id,
            operator_nickname=item.operator.nickname,
            tournament_id=item.tournament_id,
            action_type=item.action_type,
            target_type=item.target_type,
            target_id=item.target_id,
            before_json=item.before_json,
            after_json=item.after_json,
            created_at=item.created_at,
        ) for item in items],
        total=total,
    )
