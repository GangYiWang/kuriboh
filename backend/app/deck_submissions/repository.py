from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.deck_submissions.models import DeckSubmission
from app.registrations.models import TournamentParticipant


class DeckSubmissionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def options():
        return (selectinload(DeckSubmission.participant).selectinload(TournamentParticipant.user),)

    def for_tournament(self, tournament_id: UUID) -> list[DeckSubmission]:
        return list(self.db.scalars(select(DeckSubmission).where(
            DeckSubmission.tournament_id == tournament_id,
        ).options(*self.options()).order_by(DeckSubmission.placement)))

    def for_user(self, tournament_id: UUID, user_id: UUID, *, for_update: bool = False) -> DeckSubmission | None:
        statement = select(DeckSubmission).join(DeckSubmission.participant).where(
            DeckSubmission.tournament_id == tournament_id,
            TournamentParticipant.user_id == user_id,
        ).options(*self.options())
        if for_update:
            statement = statement.with_for_update()
        return self.db.scalar(statement)

    def get(self, submission_id: UUID, *, for_update: bool = False) -> DeckSubmission | None:
        statement = select(DeckSubmission).where(DeckSubmission.id == submission_id).options(*self.options())
        if for_update:
            statement = statement.with_for_update()
        return self.db.scalar(statement)
