from collections import defaultdict
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.matches.models import Match, MatchStatus
from app.playoffs.models import PlayoffRound, PlayoffRoundStatus
from app.registrations.models import TournamentParticipant
from app.statistics.models import PlayerStatistics, TournamentFinishLevel, TournamentPlayerResult
from app.statistics.schemas import PlayerStatisticsResponse, TournamentResultHistoryItem
from app.swiss.models import RankingSnapshot, SwissRound, SwissRoundStatus
from app.tournaments.models import Tournament


POINTS_RULE_VERSION = 1
POINTS_BY_FINISH_LEVEL: dict[TournamentFinishLevel, int] = {
    TournamentFinishLevel.PARTICIPATED: 0,
    TournamentFinishLevel.TOP_8: 1,
    TournamentFinishLevel.TOP_4: 2,
    TournamentFinishLevel.RUNNER_UP: 4,
    TournamentFinishLevel.CHAMPION: 8,
}


class TournamentStatisticsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def settle_tournament(
        self,
        tournament: Tournament,
        placements: list[UUID],
        settled_at: datetime,
    ) -> None:
        participants = list(self.db.scalars(
            select(TournamentParticipant)
            .where(TournamentParticipant.tournament_id == tournament.id)
            .order_by(TournamentParticipant.user_id)
        ))
        rankings = self._final_swiss_rankings(tournament.id)
        records = self._match_records(tournament.id, participants)
        finish_levels = self._finish_levels(tournament.id, placements, participants)
        placement_by_participant = {
            participant_id: placement
            for placement, participant_id in enumerate(placements, start=1)
        }

        results: list[TournamentPlayerResult] = []
        for participant in participants:
            finish_level = finish_levels[participant.id]
            wins, losses = records[participant.id]
            result = TournamentPlayerResult(
                tournament_id=tournament.id,
                participant_id=participant.id,
                user_id=participant.user_id,
                participant_status=participant.status,
                finish_level=finish_level.value,
                placement=placement_by_participant.get(participant.id),
                swiss_rank=rankings.get(participant.id),
                wins=wins,
                losses=losses,
                bye_count=participant.bye_count,
                points_awarded=POINTS_BY_FINISH_LEVEL[finish_level],
                points_rule_version=POINTS_RULE_VERSION,
                settled_at=settled_at,
            )
            self.db.add(result)
            results.append(result)

        self._upsert_player_statistics(results)

    def for_user(self, user_id: UUID) -> PlayerStatisticsResponse:
        statistics = self.db.get(PlayerStatistics, user_id)
        rows = self.db.execute(
            select(TournamentPlayerResult, Tournament)
            .join(Tournament, Tournament.id == TournamentPlayerResult.tournament_id)
            .where(TournamentPlayerResult.user_id == user_id)
            .order_by(TournamentPlayerResult.settled_at.desc())
        ).all()
        total_wins = statistics.total_wins if statistics else 0
        total_losses = statistics.total_losses if statistics else 0
        decided_matches = total_wins + total_losses
        return PlayerStatisticsResponse(
            tournament_count=statistics.tournament_count if statistics else 0,
            total_points=statistics.total_points if statistics else 0,
            champion_count=statistics.champion_count if statistics else 0,
            runner_up_count=statistics.runner_up_count if statistics else 0,
            top_4_count=statistics.top_4_count if statistics else 0,
            top_8_count=statistics.top_8_count if statistics else 0,
            total_wins=total_wins,
            total_losses=total_losses,
            total_byes=statistics.total_byes if statistics else 0,
            win_rate=round(total_wins / decided_matches, 4) if decided_matches else 0,
            results=[
                TournamentResultHistoryItem(
                    tournament_id=result.tournament_id,
                    tournament_name=tournament.name,
                    ended_at=tournament.ended_at or result.settled_at,
                    participant_status=result.participant_status,
                    finish_level=TournamentFinishLevel(result.finish_level),
                    placement=result.placement,
                    swiss_rank=result.swiss_rank,
                    wins=result.wins,
                    losses=result.losses,
                    bye_count=result.bye_count,
                    points_awarded=result.points_awarded,
                )
                for result, tournament in rows
            ],
        )

    def _final_swiss_rankings(self, tournament_id: UUID) -> dict[UUID, int]:
        final_round = self.db.scalar(
            select(SwissRound)
            .where(
                SwissRound.tournament_id == tournament_id,
                SwissRound.status == SwissRoundStatus.COMPLETED.value,
            )
            .order_by(SwissRound.round_no.desc())
            .limit(1)
        )
        if final_round is None:
            return {}
        return dict(self.db.execute(
            select(RankingSnapshot.participant_id, RankingSnapshot.rank)
            .where(RankingSnapshot.swiss_round_id == final_round.id)
        ).all())

    def _match_records(
        self,
        tournament_id: UUID,
        participants: list[TournamentParticipant],
    ) -> dict[UUID, tuple[int, int]]:
        wins: defaultdict[UUID, int] = defaultdict(int)
        losses: defaultdict[UUID, int] = defaultdict(int)
        matches = self.db.scalars(
            select(Match).where(
                Match.tournament_id == tournament_id,
                Match.status == MatchStatus.COMPLETED.value,
                Match.player_b_id.is_not(None),
                Match.winner_id.is_not(None),
            )
        )
        for match in matches:
            winner_id = match.winner_id
            if winner_id is None or match.player_b_id is None:
                continue
            loser_id = match.player_b_id if winner_id == match.player_a_id else match.player_a_id
            wins[winner_id] += 1
            losses[loser_id] += 1
        return {
            participant.id: (wins[participant.id], losses[participant.id])
            for participant in participants
        }

    def _finish_levels(
        self,
        tournament_id: UUID,
        placements: list[UUID],
        participants: list[TournamentParticipant],
    ) -> dict[UUID, TournamentFinishLevel]:
        levels = {
            participant.id: TournamentFinishLevel.PARTICIPATED
            for participant in participants
        }
        quarterfinal = self.db.scalar(select(PlayoffRound).where(
            PlayoffRound.tournament_id == tournament_id,
            PlayoffRound.bracket_size == 8,
            PlayoffRound.status == PlayoffRoundStatus.COMPLETED.value,
        ))
        if quarterfinal is not None:
            matches = self.db.scalars(select(Match).where(Match.playoff_round_id == quarterfinal.id))
            for match in matches:
                if match.winner_id is None or match.player_b_id is None:
                    continue
                loser_id = match.player_b_id if match.winner_id == match.player_a_id else match.player_a_id
                levels[loser_id] = TournamentFinishLevel.TOP_8

        for placement, participant_id in enumerate(placements, start=1):
            if placement == 1:
                levels[participant_id] = TournamentFinishLevel.CHAMPION
            elif placement == 2:
                levels[participant_id] = TournamentFinishLevel.RUNNER_UP
            else:
                levels[participant_id] = TournamentFinishLevel.TOP_4
        return levels

    def _upsert_player_statistics(self, results: list[TournamentPlayerResult]) -> None:
        values = [self._statistics_values(result) for result in results]
        dialect = self.db.get_bind().dialect.name
        if dialect == "postgresql":
            statement = postgresql_insert(PlayerStatistics).values(values)
            excluded = statement.excluded
            self.db.execute(statement.on_conflict_do_update(
                index_elements=[PlayerStatistics.user_id],
                set_=self._statistics_update_values(excluded),
            ))
            return
        if dialect == "sqlite":
            statement = sqlite_insert(PlayerStatistics).values(values)
            excluded = statement.excluded
            self.db.execute(statement.on_conflict_do_update(
                index_elements=[PlayerStatistics.user_id],
                set_=self._statistics_update_values(excluded),
            ))
            return
        raise RuntimeError(f"Unsupported database dialect for statistics settlement: {dialect}")

    @staticmethod
    def _statistics_values(result: TournamentPlayerResult) -> dict[str, UUID | int]:
        level = TournamentFinishLevel(result.finish_level)
        reached_top_4 = level in {
            TournamentFinishLevel.TOP_4,
            TournamentFinishLevel.RUNNER_UP,
            TournamentFinishLevel.CHAMPION,
        }
        reached_top_8 = level in {
            TournamentFinishLevel.TOP_8,
            TournamentFinishLevel.TOP_4,
            TournamentFinishLevel.RUNNER_UP,
            TournamentFinishLevel.CHAMPION,
        }
        return {
            "user_id": result.user_id,
            "tournament_count": 1,
            "total_points": result.points_awarded,
            "champion_count": int(level == TournamentFinishLevel.CHAMPION),
            "runner_up_count": int(level == TournamentFinishLevel.RUNNER_UP),
            "top_4_count": int(reached_top_4),
            "top_8_count": int(reached_top_8),
            "total_wins": result.wins,
            "total_losses": result.losses,
            "total_byes": result.bye_count,
        }

    @staticmethod
    def _statistics_update_values(excluded) -> dict[str, object]:
        return {
            "tournament_count": PlayerStatistics.tournament_count + excluded.tournament_count,
            "total_points": PlayerStatistics.total_points + excluded.total_points,
            "champion_count": PlayerStatistics.champion_count + excluded.champion_count,
            "runner_up_count": PlayerStatistics.runner_up_count + excluded.runner_up_count,
            "top_4_count": PlayerStatistics.top_4_count + excluded.top_4_count,
            "top_8_count": PlayerStatistics.top_8_count + excluded.top_8_count,
            "total_wins": PlayerStatistics.total_wins + excluded.total_wins,
            "total_losses": PlayerStatistics.total_losses + excluded.total_losses,
            "total_byes": PlayerStatistics.total_byes + excluded.total_byes,
            "updated_at": func.now(),
        }
