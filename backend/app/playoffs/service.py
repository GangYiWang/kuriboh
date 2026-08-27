from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import add_audit_log
from app.core.errors import AppError
from app.matches.models import Match, MatchStage, MatchStatus, MatchSubmission, ResultSource, SubmittedResult
from app.playoffs.algorithm import SeededParticipant, generate_playoff_bracket, playoff_stage_name
from app.playoffs.models import PlayoffRound, PlayoffRoundStatus
from app.playoffs.repository import PlayoffRepository
from app.playoffs.schemas import (
    MyPlayoffMatchResponse,
    PlayoffMatchResponse,
    PlayoffOverviewResponse,
    PlayoffRoundResponse,
)
from app.registrations.models import ParticipantStatus
from app.swiss.models import SwissRoundStatus
from app.swiss.repository import SwissRepository
from app.tournaments.models import Tournament, TournamentStatus
from app.tournaments.service import TournamentService


class PlayoffService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = PlayoffRepository(db)
        self.swiss = SwissRepository(db)
        self.tournaments = TournamentService(db)

    def _prepare_stage(self, tournament_id: UUID) -> tuple[Tournament, PlayoffRound, list[Match]]:
        tournament = self.tournaments.require(tournament_id, for_update=True)
        if tournament.status not in {TournamentStatus.SWISS.value, TournamentStatus.ELIMINATION.value}:
            raise AppError("INVALID_TOURNAMENT_STATE", "赛事当前不能生成淘汰赛签表", status_code=409)
        latest = self.repository.latest_round(tournament_id)
        if latest and latest.status == PlayoffRoundStatus.DRAFT.value:
            raise AppError("PLAYOFF_PREVIEW_EXISTS", "当前淘汰阶段预览已经存在", status_code=409)
        if latest and latest.status != PlayoffRoundStatus.COMPLETED.value:
            raise AppError("PLAYOFF_STAGE_INCOMPLETE", "当前淘汰阶段尚未完成", status_code=409)
        if latest and latest.bracket_size == 2:
            raise AppError("PLAYOFF_FINISHED", "决赛已经完成，等待赛事主办方结束赛事", status_code=409)

        if latest is None:
            round_item, matches = self._generate_first_round(tournament)
        else:
            round_item, matches = self._generate_next_round(tournament_id, latest)
        return tournament, round_item, matches

    def _store_stage(self, round_item: PlayoffRound, matches: list[Match]) -> None:
        self.db.add(round_item)
        self.db.flush()
        for match in matches:
            match.playoff_round_id = round_item.id
            self.db.add(match)

    def _publish_stage_state(
        self,
        tournament: Tournament,
        round_item: PlayoffRound,
    ) -> None:
        previous = [
            item for item in self.repository.rounds(tournament.id)
            if item.stage_no < round_item.stage_no
        ]
        if previous and previous[-1].status != PlayoffRoundStatus.COMPLETED.value:
            raise AppError("PLAYOFF_STAGE_INCOMPLETE", "上一淘汰阶段尚未完成", status_code=409)
        if previous:
            for match in self.repository.round_matches(previous[-1].id):
                match.result_locked = True
        else:
            for swiss_round in self.swiss.rounds(tournament.id, published_only=True):
                for match in self.swiss.round_matches(swiss_round.id):
                    match.result_locked = True
        round_item.status = PlayoffRoundStatus.PUBLISHED.value
        round_item.published_at = datetime.now(UTC)
        tournament.status = TournamentStatus.ELIMINATION.value

    def generate_preview(self, tournament_id: UUID, operator_id: UUID) -> PlayoffRoundResponse:
        _, round_item, matches = self._prepare_stage(tournament_id)
        self._store_stage(round_item, matches)
        add_audit_log(
            self.db,
            operator_id=operator_id,
            tournament_id=tournament_id,
            action_type="PLAYOFF_STAGE_GENERATED",
            target_type="playoff_round",
            target_id=round_item.id,
            after={"stage_no": round_item.stage_no, "bracket_size": round_item.bracket_size},
        )
        self.db.commit()
        return self.round_response(round_item)

    def generate_and_publish(self, tournament_id: UUID, operator_id: UUID) -> PlayoffRoundResponse:
        existing = self.repository.latest_round(tournament_id)
        if existing and existing.status == PlayoffRoundStatus.DRAFT.value:
            tournament = self.tournaments.require(tournament_id, for_update=True)
            round_item = self.repository.get_round(tournament_id, existing.id, for_update=True)
            if round_item is None:
                raise AppError("PLAYOFF_ROUND_NOT_FOUND", "淘汰阶段不存在", status_code=404)
            self._publish_stage_state(tournament, round_item)
            action_type = "PLAYOFF_STAGE_PUBLISHED"
        else:
            tournament, round_item, matches = self._prepare_stage(tournament_id)
            self._store_stage(round_item, matches)
            self._publish_stage_state(tournament, round_item)
            action_type = "PLAYOFF_STAGE_GENERATED_AND_PUBLISHED"
        add_audit_log(
            self.db,
            operator_id=operator_id,
            tournament_id=tournament_id,
            action_type=action_type,
            target_type="playoff_round",
            target_id=round_item.id,
            after={
                "stage_no": round_item.stage_no,
                "bracket_size": round_item.bracket_size,
                "name": round_item.name,
            },
        )
        self.db.commit()
        return self.round_response(round_item)

    def _generate_first_round(self, tournament) -> tuple[PlayoffRound, list[Match]]:
        latest_swiss = self.swiss.latest_round(tournament.id)
        if (
            latest_swiss is None
            or latest_swiss.status != SwissRoundStatus.COMPLETED.value
            or latest_swiss.round_no != tournament.swiss_rounds
        ):
            raise AppError("SWISS_NOT_FINISHED", "完成全部瑞士轮后才能生成淘汰赛", status_code=409)
        ranking_round_no, rankings = self.swiss.latest_rankings(tournament.id)
        if ranking_round_no != tournament.swiss_rounds:
            raise AppError("SWISS_RANKING_NOT_READY", "瑞士轮最终排名尚未生成", status_code=409)
        active = [item for item in rankings if item.participant.status == ParticipantStatus.ACTIVE.value]
        playoff_size = tournament.playoff_size or 0
        if len(active) < playoff_size:
            raise AppError("INSUFFICIENT_PLAYOFF_PLAYERS", "有效选手不足以生成配置的淘汰赛", status_code=409)
        seeded = [
            SeededParticipant(seed=index, participant_id=item.participant_id)
            for index, item in enumerate(active[:playoff_size], start=1)
        ]
        pairings = generate_playoff_bracket(seeded)
        round_item = PlayoffRound(
            tournament_id=tournament.id,
            stage_no=1,
            bracket_size=playoff_size,
            name=playoff_stage_name(playoff_size),
            status=PlayoffRoundStatus.DRAFT.value,
        )
        matches = [
            Match(
                tournament_id=tournament.id,
                stage=MatchStage.ELIMINATION.value,
                round_no=1,
                table_no=index,
                seed_a=pairing.player_a.seed,
                seed_b=pairing.player_b.seed,
                player_a_id=pairing.player_a.participant_id,
                player_b_id=pairing.player_b.participant_id,
                status=MatchStatus.WAITING.value,
            )
            for index, pairing in enumerate(pairings, start=1)
        ]
        return round_item, matches

    def _generate_next_round(self, tournament_id: UUID, previous: PlayoffRound) -> tuple[PlayoffRound, list[Match]]:
        previous_matches = self.repository.round_matches(previous.id)
        if any(match.winner_id is None for match in previous_matches):
            raise AppError("PLAYOFF_STAGE_INCOMPLETE", "上一阶段仍有未确认赛果", status_code=409)
        next_size = previous.bracket_size // 2
        round_item = PlayoffRound(
            tournament_id=tournament_id,
            stage_no=previous.stage_no + 1,
            bracket_size=next_size,
            name=playoff_stage_name(next_size),
            status=PlayoffRoundStatus.DRAFT.value,
        )
        matches: list[Match] = []
        for index in range(0, len(previous_matches), 2):
            left = previous_matches[index]
            right = previous_matches[index + 1]
            left_seed = left.seed_a if left.winner_id == left.player_a_id else left.seed_b
            right_seed = right.seed_a if right.winner_id == right.player_a_id else right.seed_b
            matches.append(Match(
                tournament_id=tournament_id,
                stage=MatchStage.ELIMINATION.value,
                round_no=round_item.stage_no,
                table_no=len(matches) + 1,
                seed_a=left_seed,
                seed_b=right_seed,
                player_a_id=left.winner_id,
                player_b_id=right.winner_id,
                status=MatchStatus.WAITING.value,
            ))
        return round_item, matches

    def publish_round(self, tournament_id: UUID, round_id: UUID, operator_id: UUID) -> PlayoffRoundResponse:
        tournament = self.tournaments.require(tournament_id, for_update=True)
        round_item = self.repository.get_round(tournament_id, round_id, for_update=True)
        if round_item is None:
            raise AppError("PLAYOFF_ROUND_NOT_FOUND", "淘汰阶段不存在", status_code=404)
        if round_item.status != PlayoffRoundStatus.DRAFT.value:
            raise AppError("PLAYOFF_ALREADY_PUBLISHED", "淘汰阶段已经发布", status_code=409)
        self._publish_stage_state(tournament, round_item)
        add_audit_log(
            self.db,
            operator_id=operator_id,
            tournament_id=tournament_id,
            action_type="PLAYOFF_STAGE_PUBLISHED",
            target_type="playoff_round",
            target_id=round_item.id,
            after={"stage_no": round_item.stage_no, "name": round_item.name},
        )
        self.db.commit()
        return self.round_response(round_item)

    def submit_result(self, match_id: UUID, user_id: UUID, result: SubmittedResult) -> MyPlayoffMatchResponse:
        match = self.db.scalar(select(Match).where(Match.id == match_id).with_for_update())
        if match is None or match.stage != MatchStage.ELIMINATION.value:
            raise AppError("MATCH_NOT_FOUND", "淘汰赛对局不存在", status_code=404)
        round_item = self.db.get(PlayoffRound, match.playoff_round_id)
        if round_item is None or round_item.status == PlayoffRoundStatus.DRAFT.value:
            raise AppError("MATCH_NOT_PUBLISHED", "淘汰赛对局尚未发布", status_code=409)
        participant = self.swiss.participant_for_user(match.tournament_id, user_id)
        if participant is None or participant.id not in {match.player_a_id, match.player_b_id}:
            raise AppError("MATCH_NOT_FOUND", "这不是你的淘汰赛对局", status_code=404)
        if match.result_locked:
            raise AppError("MATCH_RESULT_LOCKED", "下一淘汰阶段已发布，本场赛果已锁定", status_code=409)
        if match.status == MatchStatus.COMPLETED.value:
            raise AppError("MATCH_ALREADY_COMPLETED", "赛果已经确认，选手不能继续修改", status_code=409)
        submission = self.db.scalar(select(MatchSubmission).where(
            MatchSubmission.match_id == match.id,
            MatchSubmission.participant_id == participant.id,
        ))
        if submission is None:
            self.db.add(MatchSubmission(
                match_id=match.id,
                participant_id=participant.id,
                submitted_result=result.value,
            ))
        else:
            submission.submitted_result = result.value
        self.db.flush()
        self._apply_submissions(match, round_item)
        self.db.commit()
        return self.my_match_response(match, participant.id)

    def forfeit(
        self,
        match_id: UUID,
        loser_id: UUID,
        reason: str | None,
        operator_id: UUID,
    ) -> PlayoffMatchResponse:
        match = self.db.scalar(select(Match).where(Match.id == match_id).with_for_update())
        if match is None or match.stage != MatchStage.ELIMINATION.value:
            raise AppError("MATCH_NOT_FOUND", "淘汰赛对局不存在", status_code=404)
        round_item = self.db.get(PlayoffRound, match.playoff_round_id)
        if round_item is None or round_item.status == PlayoffRoundStatus.DRAFT.value:
            raise AppError("MATCH_NOT_PUBLISHED", "淘汰赛对局尚未发布，不能判负", status_code=409)
        if match.result_locked:
            raise AppError("MATCH_RESULT_LOCKED", "下一淘汰阶段已发布，本场赛果已锁定", status_code=409)
        if loser_id not in {match.player_a_id, match.player_b_id}:
            raise AppError("INVALID_FORFEIT_PLAYER", "被判负选手必须是本场选手", status_code=400)
        normalized_reason = reason.strip() if reason and reason.strip() else None
        winner_id = match.player_b_id if loser_id == match.player_a_id else match.player_a_id
        before = {
            "winner_id": str(match.winner_id) if match.winner_id else None,
            "status": match.status,
            "submissions": {
                str(item.participant_id): item.submitted_result for item in match.submissions
            },
        }
        self._apply_admin_results(match, winner_id, loser_id)
        match.winner_id = winner_id
        match.status = MatchStatus.COMPLETED.value
        match.result_source = ResultSource.ADMIN.value
        self.db.flush()
        self._discard_later_draft(match.tournament_id, round_item.stage_no)
        self._finish_round_if_ready(round_item)
        add_audit_log(
            self.db,
            operator_id=operator_id,
            tournament_id=match.tournament_id,
            action_type="PLAYOFF_MATCH_FORFEIT",
            target_type="match",
            target_id=match.id,
            before=before,
            after={"winner_id": str(winner_id), "loser_id": str(loser_id), "reason": normalized_reason},
        )
        self.db.commit()
        return self.match_response(match, admin=True)

    def _apply_admin_results(self, match: Match, winner_id: UUID, loser_id: UUID) -> None:
        submissions = {item.participant_id: item for item in match.submissions}
        for participant_id, result in (
            (winner_id, SubmittedResult.WIN.value),
            (loser_id, SubmittedResult.LOSS.value),
        ):
            submission = submissions.get(participant_id)
            if submission is None:
                self.db.add(MatchSubmission(
                    match_id=match.id,
                    participant_id=participant_id,
                    submitted_result=result,
                ))
            else:
                submission.submitted_result = result

    def overview(self, tournament_id: UUID, *, admin: bool = False) -> PlayoffOverviewResponse:
        tournament = self.tournaments.require(tournament_id)
        rounds = self.repository.rounds(tournament_id, published_only=not admin)
        final = next((item for item in rounds if item.bracket_size == 2), None)
        final_match = self.repository.round_matches(final.id)[0] if final and final.status == PlayoffRoundStatus.COMPLETED.value else None
        champion = final_match.winner if final_match else None
        return PlayoffOverviewResponse(
            playoff_size=tournament.playoff_size or 0,
            rounds=[self.round_response(item, admin=admin) for item in rounds],
            champion_id=champion.id if champion else None,
            champion_nickname=champion.nickname_snapshot if champion else None,
            awaiting_tournament_end=bool(
                final_match and tournament.status == TournamentStatus.ELIMINATION.value
            ),
        )

    def my_matches(self, tournament_id: UUID, user_id: UUID) -> list[MyPlayoffMatchResponse]:
        self.tournaments.require(tournament_id)
        participant = self.swiss.participant_for_user(tournament_id, user_id)
        if participant is None:
            raise AppError("PARTICIPANT_NOT_FOUND", "你不是本届赛事正式参赛选手", status_code=404)
        items: list[MyPlayoffMatchResponse] = []
        for round_item in self.repository.rounds(tournament_id, published_only=True):
            for match in self.repository.round_matches(round_item.id):
                if participant.id in {match.player_a_id, match.player_b_id}:
                    items.append(self.my_match_response(match, participant.id))
        return items

    def round_response(self, round_item: PlayoffRound, *, admin: bool = True) -> PlayoffRoundResponse:
        return PlayoffRoundResponse(
            id=round_item.id,
            stage_no=round_item.stage_no,
            bracket_size=round_item.bracket_size,
            name=round_item.name,
            status=PlayoffRoundStatus(round_item.status),
            published_at=round_item.published_at,
            completed_at=round_item.completed_at,
            matches=[self.match_response(item, admin=admin) for item in self.repository.round_matches(round_item.id)],
        )

    def match_response(self, match: Match, *, admin: bool) -> PlayoffMatchResponse:
        submissions = {item.participant_id: SubmittedResult(item.submitted_result) for item in match.submissions}
        return PlayoffMatchResponse(
            id=match.id,
            stage_no=match.round_no,
            table_no=match.table_no,
            seed_a=match.seed_a or 0,
            seed_b=match.seed_b or 0,
            player_a_id=match.player_a_id,
            player_a_nickname=match.player_a.nickname_snapshot,
            player_b_id=match.player_b_id,
            player_b_nickname=match.player_b.nickname_snapshot,
            winner_id=match.winner_id,
            status=MatchStatus(match.status),
            result_source=match.result_source,
            result_locked=match.result_locked,
            player_a_result=submissions.get(match.player_a_id) if admin else None,
            player_b_result=submissions.get(match.player_b_id) if admin else None,
        )

    def my_match_response(self, match: Match, participant_id: UUID) -> MyPlayoffMatchResponse:
        base = self.match_response(match, admin=False)
        submissions = {item.participant_id: SubmittedResult(item.submitted_result) for item in match.submissions}
        opponent_id = match.player_b_id if participant_id == match.player_a_id else match.player_a_id
        return MyPlayoffMatchResponse(
            **base.model_dump(),
            my_participant_id=participant_id,
            my_submission=submissions.get(participant_id),
            opponent_submission=submissions.get(opponent_id),
            opponent_submitted=opponent_id in submissions,
        )

    def _apply_submissions(self, match: Match, round_item: PlayoffRound) -> None:
        submissions = {item.participant_id: item.submitted_result for item in match.submissions}
        if len(submissions) < 2:
            match.status = MatchStatus.WAITING.value
            return
        a_result = submissions[match.player_a_id]
        b_result = submissions[match.player_b_id]
        if a_result == SubmittedResult.WIN.value and b_result == SubmittedResult.LOSS.value:
            match.winner_id = match.player_a_id
        elif a_result == SubmittedResult.LOSS.value and b_result == SubmittedResult.WIN.value:
            match.winner_id = match.player_b_id
        else:
            match.status = MatchStatus.CONFLICT.value
            match.winner_id = None
            match.result_source = None
            return
        match.status = MatchStatus.COMPLETED.value
        match.result_source = ResultSource.PLAYERS.value
        self.db.flush()
        self._finish_round_if_ready(round_item)

    def _finish_round_if_ready(self, round_item: PlayoffRound) -> None:
        if self.repository.incomplete_count(round_item.id):
            return
        round_item.status = PlayoffRoundStatus.COMPLETED.value
        round_item.completed_at = datetime.now(UTC)

    def _discard_later_draft(self, tournament_id: UUID, stage_no: int) -> None:
        latest = self.repository.latest_round(tournament_id)
        if latest and latest.status == PlayoffRoundStatus.DRAFT.value and latest.stage_no > stage_no:
            self.repository.discard_round(latest)
            self.db.flush()
