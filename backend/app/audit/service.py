from uuid import UUID

from sqlalchemy.orm import Session

from app.audit.models import AuditLog


def add_audit_log(
    db: Session,
    *,
    operator_id: UUID,
    action_type: str,
    target_type: str,
    target_id: UUID,
    tournament_id: UUID | None = None,
    before: dict | None = None,
    after: dict | None = None,
) -> None:
    db.add(AuditLog(
        operator_id=operator_id,
        tournament_id=tournament_id,
        action_type=action_type,
        target_type=target_type,
        target_id=str(target_id),
        before_json=before,
        after_json=after,
    ))
