from uuid import UUID

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.registrations.models import Registration, RegistrationStatus, TournamentParticipant
from app.tournaments.models import Tournament, TournamentStatus


class TournamentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, tournament_id: UUID, *, for_update: bool = False) -> Tournament | None:
        statement = (
            select(Tournament)
            .where(Tournament.id == tournament_id)
            .options(selectinload(Tournament.banlist_version))
        )
        if for_update:
            statement = statement.with_for_update()
        return self.db.scalar(statement)

    def list_public(
        self,
        *,
        offset: int,
        limit: int,
        status: TournamentStatus | None,
        search: str | None,
    ) -> tuple[list[Tournament], int]:
        filters = [Tournament.status != TournamentStatus.DRAFT.value]
        if status is not None:
            filters.append(Tournament.status == status.value)
        if search:
            filters.append(Tournament.name.ilike(f"%{search.strip()}%"))
        statement = (
            select(Tournament)
            .where(*filters)
            .options(selectinload(Tournament.banlist_version))
            .order_by(Tournament.planned_start_at.desc(), Tournament.created_at.desc())
        )
        items = list(self.db.scalars(statement.offset(offset).limit(limit)))
        total = self.db.scalar(select(func.count()).select_from(Tournament).where(*filters)) or 0
        return items, total

    def list_admin(self, *, offset: int, limit: int) -> tuple[list[Tournament], int]:
        statement = (
            select(Tournament)
            .options(selectinload(Tournament.banlist_version))
            .order_by(Tournament.created_at.desc())
        )
        items = list(self.db.scalars(statement.offset(offset).limit(limit)))
        total = self.db.scalar(select(func.count()).select_from(Tournament)) or 0
        return items, total

    def registration_counts(self, tournament_id: UUID) -> tuple[int, int]:
        rows = self.db.execute(
            select(Registration.status, func.count())
            .where(Registration.tournament_id == tournament_id)
            .group_by(Registration.status)
        ).all()
        counts = {status: count for status, count in rows}
        return (
            int(counts.get(RegistrationStatus.APPROVED.value, 0)),
            int(counts.get(RegistrationStatus.PENDING.value, 0)),
        )

    def participants(self, tournament_id: UUID) -> list[TournamentParticipant]:
        return list(self.db.scalars(
            select(TournamentParticipant)
            .where(TournamentParticipant.tournament_id == tournament_id)
            .order_by(TournamentParticipant.nickname_snapshot)
        ))

    def registrations_for_user(self, user_id: UUID) -> list[Registration]:
        return list(self.db.scalars(
            select(Registration)
            .join(Registration.tournament)
            .where(Registration.user_id == user_id)
            .options(
                selectinload(Registration.tournament),
                selectinload(Registration.participant),
            )
            .order_by(
                case((Tournament.status == TournamentStatus.ENDED.value, 1), else_=0),
                Tournament.planned_start_at.asc(),
                Tournament.created_at.desc(),
            )
        ))
