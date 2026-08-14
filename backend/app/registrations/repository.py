from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.registrations.models import Registration, RegistrationStatus


class RegistrationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, registration_id: UUID, *, for_update: bool = False) -> Registration | None:
        statement = select(Registration).where(Registration.id == registration_id)
        if for_update:
            statement = statement.with_for_update()
        else:
            statement = statement.options(joinedload(Registration.user))
        return self.db.scalar(statement)

    def for_user(self, tournament_id: UUID, user_id: UUID, *, for_update: bool = False) -> Registration | None:
        statement = select(Registration).where(
            Registration.tournament_id == tournament_id, Registration.user_id == user_id
        )
        if for_update:
            statement = statement.with_for_update()
        else:
            statement = statement.options(joinedload(Registration.user))
        return self.db.scalar(statement)

    def list_for_tournament(self, tournament_id: UUID) -> tuple[list[Registration], int]:
        admin_visible = (
            (Registration.status != RegistrationStatus.CANCELED.value)
            | Registration.reviewed_by_id.is_not(None)
        )
        statement = (
            select(Registration)
            .where(Registration.tournament_id == tournament_id, admin_visible)
            .options(joinedload(Registration.user))
            .order_by(Registration.created_at.asc())
        )
        items = list(self.db.scalars(statement))
        total = self.db.scalar(
            select(func.count()).select_from(Registration).where(
                Registration.tournament_id == tournament_id,
                admin_visible,
            )
        ) or 0
        return items, total

    def count_by_status(self, tournament_id: UUID, status: RegistrationStatus) -> int:
        return int(self.db.scalar(
            select(func.count()).select_from(Registration).where(
                Registration.tournament_id == tournament_id,
                Registration.status == status.value,
            )
        ) or 0)
