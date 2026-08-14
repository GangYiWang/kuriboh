from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.matches.models import Match
from app.playoffs.models import PlayoffRound, PlayoffRoundStatus


class PlayoffRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def rounds(self, tournament_id: UUID, *, published_only: bool = False) -> list[PlayoffRound]:
        statement = select(PlayoffRound).where(PlayoffRound.tournament_id == tournament_id)
        if published_only:
            statement = statement.where(PlayoffRound.status != PlayoffRoundStatus.DRAFT.value)
        return list(self.db.scalars(statement.order_by(PlayoffRound.stage_no)))

    def latest_round(self, tournament_id: UUID) -> PlayoffRound | None:
        return self.db.scalar(
            select(PlayoffRound)
            .where(PlayoffRound.tournament_id == tournament_id)
            .order_by(PlayoffRound.stage_no.desc())
            .limit(1)
        )

    def get_round(self, tournament_id: UUID, round_id: UUID, *, for_update: bool = False) -> PlayoffRound | None:
        statement = select(PlayoffRound).where(
            PlayoffRound.id == round_id,
            PlayoffRound.tournament_id == tournament_id,
        )
        if for_update:
            statement = statement.with_for_update()
        return self.db.scalar(statement)

    def round_matches(self, round_id: UUID) -> list[Match]:
        return list(self.db.scalars(
            select(Match)
            .where(Match.playoff_round_id == round_id)
            .options(
                selectinload(Match.player_a),
                selectinload(Match.player_b),
                selectinload(Match.winner),
                selectinload(Match.submissions),
            )
            .order_by(Match.table_no)
        ))

    def incomplete_count(self, round_id: UUID) -> int:
        from app.matches.models import MatchStatus

        return self.db.scalar(select(func.count()).select_from(Match).where(
            Match.playoff_round_id == round_id,
            Match.status != MatchStatus.COMPLETED.value,
        )) or 0

    def discard_round(self, round_item: PlayoffRound) -> None:
        self.db.delete(round_item)
