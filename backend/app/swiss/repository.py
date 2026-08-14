from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.matches.models import Match, MatchSubmission, MatchStatus
from app.registrations.models import ParticipantStatus, TournamentParticipant
from app.swiss.models import RankingSnapshot, SwissRound, SwissRoundStatus


class SwissRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def rounds(self, tournament_id: UUID, *, published_only: bool = False) -> list[SwissRound]:
        statement = select(SwissRound).where(SwissRound.tournament_id == tournament_id)
        if published_only:
            statement = statement.where(SwissRound.status != SwissRoundStatus.DRAFT.value)
        return list(self.db.scalars(statement.order_by(SwissRound.round_no)))

    def latest_round(self, tournament_id: UUID) -> SwissRound | None:
        return self.db.scalar(
            select(SwissRound)
            .where(SwissRound.tournament_id == tournament_id)
            .order_by(SwissRound.round_no.desc())
            .limit(1)
        )

    def get_round(self, tournament_id: UUID, round_id: UUID, *, for_update: bool = False) -> SwissRound | None:
        statement = select(SwissRound).where(
            SwissRound.id == round_id,
            SwissRound.tournament_id == tournament_id,
        )
        if for_update:
            statement = statement.with_for_update()
        return self.db.scalar(statement)

    def active_participants(self, tournament_id: UUID) -> list[TournamentParticipant]:
        return list(self.db.scalars(
            select(TournamentParticipant)
            .where(
                TournamentParticipant.tournament_id == tournament_id,
                TournamentParticipant.status == ParticipantStatus.ACTIVE.value,
            )
            .order_by(TournamentParticipant.nickname_snapshot, TournamentParticipant.id)
        ))

    def participants(self, tournament_id: UUID) -> list[TournamentParticipant]:
        return list(self.db.scalars(
            select(TournamentParticipant)
            .where(TournamentParticipant.tournament_id == tournament_id)
            .order_by(TournamentParticipant.nickname_snapshot, TournamentParticipant.id)
        ))

    def participant_for_user(self, tournament_id: UUID, user_id: UUID) -> TournamentParticipant | None:
        return self.db.scalar(select(TournamentParticipant).where(
            TournamentParticipant.tournament_id == tournament_id,
            TournamentParticipant.user_id == user_id,
        ))

    def round_matches(self, round_id: UUID) -> list[Match]:
        return list(self.db.scalars(
            select(Match)
            .where(Match.swiss_round_id == round_id)
            .options(
                selectinload(Match.player_a),
                selectinload(Match.player_b),
                selectinload(Match.winner),
                selectinload(Match.submissions),
            )
            .order_by(Match.table_no)
        ))

    def get_match(self, match_id: UUID, *, for_update: bool = False) -> Match | None:
        statement = select(Match).where(Match.id == match_id)
        if for_update:
            statement = statement.with_for_update()
        return self.db.scalar(statement)

    def completed_matches(self, tournament_id: UUID, through_round: int | None = None) -> list[Match]:
        statement = select(Match).where(
            Match.tournament_id == tournament_id,
            Match.status == MatchStatus.COMPLETED.value,
        )
        if through_round is not None:
            statement = statement.where(Match.round_no <= through_round)
        return list(self.db.scalars(statement.order_by(Match.round_no, Match.table_no)))

    def incomplete_count(self, round_id: UUID) -> int:
        return self.db.scalar(select(func.count()).select_from(Match).where(
            Match.swiss_round_id == round_id,
            Match.status != MatchStatus.COMPLETED.value,
        )) or 0

    def latest_rankings(self, tournament_id: UUID) -> tuple[int, list[RankingSnapshot]]:
        round_no = self.db.scalar(
            select(func.max(SwissRound.round_no)).where(
                SwissRound.tournament_id == tournament_id,
                SwissRound.status == SwissRoundStatus.COMPLETED.value,
            )
        )
        if round_no is None:
            return 0, []
        items = list(self.db.scalars(
            select(RankingSnapshot)
            .join(SwissRound, RankingSnapshot.swiss_round_id == SwissRound.id)
            .where(SwissRound.tournament_id == tournament_id, SwissRound.round_no == round_no)
            .options(selectinload(RankingSnapshot.participant))
            .order_by(RankingSnapshot.rank)
        ))
        return round_no, items

    def discard_round(self, round_item: SwissRound) -> None:
        self.db.delete(round_item)

    def delete_rankings(self, round_id: UUID) -> None:
        self.db.execute(delete(RankingSnapshot).where(RankingSnapshot.swiss_round_id == round_id))

    def submissions(self, match_id: UUID) -> list[MatchSubmission]:
        return list(self.db.scalars(select(MatchSubmission).where(MatchSubmission.match_id == match_id)))
