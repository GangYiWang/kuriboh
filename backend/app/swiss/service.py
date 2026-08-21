from __future__ import annotations

from datetime import UTC, datetime
from random import Random, SystemRandom
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import add_audit_log
from app.core.errors import AppError
from app.matches.models import Match, MatchStage, MatchStatus, MatchSubmission, ResultSource, SubmittedResult
from app.registrations.models import ParticipantStatus, TournamentParticipant
from app.swiss.algorithm import (
    MatchRecord,
    Pairing,
    PairingUnavailableError,
    StandingInput,
    calculate_rankings,
    generate_swiss_pairings,
    validate_pairing_draft,
)
from app.swiss.models import RankingSnapshot, SwissRound, SwissRoundStatus, Withdrawal
from app.swiss.repository import SwissRepository
from app.swiss.schemas import (
    MatchResponse,
    MyMatchResponse,
    RankingResponse,
    RoundResponse,
    SwissOverviewResponse,
    WithdrawResponse,
)
from app.tournaments.models import TournamentStatus
from app.tournaments.service import TournamentService


class SwissService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = SwissRepository(db)
        self.tournaments = TournamentService(db)

    def _require_swiss_tournament(self, tournament_id: UUID, *, for_update: bool = False):
        tournament = self.tournaments.require(tournament_id, for_update=for_update)
        if tournament.status != TournamentStatus.SWISS.value:
            raise AppError("INVALID_TOURNAMENT_STATE", "赛事当前不在瑞士轮阶段", status_code=409)
        return tournament

    def _standing_inputs(self, tournament_id: UUID, *, active_only: bool) -> list[StandingInput]:
        participants = (
            self.repository.active_participants(tournament_id)
            if active_only
            else self.repository.participants(tournament_id)
        )
        _, snapshots = self.repository.latest_rankings(tournament_id)
        snapshot_by_id = {item.participant_id: item for item in snapshots}
        ordered = sorted(participants, key=lambda item: item.nickname_snapshot.casefold())
        return [
            StandingInput(
                participant_id=item.id,
                nickname=item.nickname_snapshot,
                wins=snapshot_by_id[item.id].wins if item.id in snapshot_by_id else 0,
                losses=snapshot_by_id[item.id].losses if item.id in snapshot_by_id else 0,
                rank=snapshot_by_id[item.id].rank if item.id in snapshot_by_id else index,
                bye_count=item.bye_count,
            )
            for index, item in enumerate(ordered, start=1)
        ]

    def _prior_pairs(self, tournament_id: UUID, before_round: int | None = None) -> set[frozenset[UUID]]:
        pairs: set[frozenset[UUID]] = set()
        for match in self.repository.completed_matches(tournament_id, through_round=(before_round - 1) if before_round else None):
            if match.player_b_id is not None:
                pairs.add(frozenset((match.player_a_id, match.player_b_id)))
        return pairs

    def generate_preview(
        self,
        tournament_id: UUID,
        operator_id: UUID,
        *,
        seed: int | None,
        regenerate: bool,
    ) -> RoundResponse:
        tournament = self._require_swiss_tournament(tournament_id, for_update=True)
        latest = self.repository.latest_round(tournament_id)
        if latest and latest.status == SwissRoundStatus.DRAFT.value:
            if not regenerate:
                raise AppError("ROUND_PREVIEW_EXISTS", "下一轮预览已经存在", status_code=409)
            round_no = latest.round_no
            self.repository.discard_round(latest)
            self.db.flush()
        else:
            if regenerate:
                raise AppError("ROUND_PREVIEW_NOT_FOUND", "没有可重新生成的轮次预览", status_code=404)
            if latest and latest.status != SwissRoundStatus.COMPLETED.value:
                raise AppError("CURRENT_ROUND_INCOMPLETE", "当前轮仍有未完成或冲突对局", status_code=409)
            round_no = (latest.round_no + 1) if latest else 1

        if tournament.swiss_rounds is None or round_no > tournament.swiss_rounds:
            raise AppError("SWISS_ROUNDS_FINISHED", "已完成配置的全部瑞士轮", status_code=409)
        players = self._standing_inputs(tournament_id, active_only=True)
        if len(players) < 2:
            raise AppError("INSUFFICIENT_PARTICIPANTS", "至少需要 2 名有效选手才能生成配对", status_code=409)

        rng = Random(seed) if seed is not None else Random(SystemRandom().randrange(2**63))
        try:
            pairings = generate_swiss_pairings(players, self._prior_pairs(tournament_id), rng)
        except PairingUnavailableError as exc:
            raise AppError(
                "SWISS_PAIRING_UNAVAILABLE",
                "无法生成覆盖全部选手的无重复对阵，请检查退赛情况或调整瑞士轮配置",
                status_code=409,
            ) from exc
        round_item = SwissRound(
            tournament_id=tournament_id,
            round_no=round_no,
            status=SwissRoundStatus.DRAFT.value,
        )
        self.db.add(round_item)
        self.db.flush()
        for table_no, pairing in enumerate(pairings, start=1):
            self.db.add(Match(
                tournament_id=tournament_id,
                swiss_round_id=round_item.id,
                stage=MatchStage.SWISS.value,
                round_no=round_no,
                table_no=table_no,
                player_a_id=pairing.player_a_id,
                player_b_id=pairing.player_b_id,
                status=MatchStatus.WAITING.value,
                result_locked=False,
            ))
        add_audit_log(
            self.db,
            operator_id=operator_id,
            tournament_id=tournament_id,
            action_type="SWISS_ROUND_REGENERATED" if regenerate else "SWISS_ROUND_GENERATED",
            target_type="swiss_round",
            target_id=round_item.id,
            after={"round_no": round_no, "seed": seed},
        )
        self.db.commit()
        return self.round_response(round_item)

    def swap_players(
        self,
        tournament_id: UUID,
        round_id: UUID,
        first_id: UUID,
        second_id: UUID,
        operator_id: UUID,
    ) -> RoundResponse:
        self._require_swiss_tournament(tournament_id, for_update=True)
        round_item = self.repository.get_round(tournament_id, round_id, for_update=True)
        if round_item is None or round_item.status != SwissRoundStatus.DRAFT.value:
            raise AppError("ROUND_PREVIEW_NOT_EDITABLE", "只有未发布的轮次预览可以调整", status_code=409)
        if first_id == second_id:
            raise AppError("INVALID_SWAP", "请选择两名不同选手")
        matches = self.repository.round_matches(round_id)
        locations: dict[UUID, tuple[Match, str]] = {}
        for match in matches:
            locations[match.player_a_id] = (match, "player_a_id")
            if match.player_b_id:
                locations[match.player_b_id] = (match, "player_b_id")
        if first_id not in locations or second_id not in locations:
            raise AppError("INVALID_SWAP", "所选选手不在当前轮预览中", status_code=400)
        first_match, first_slot = locations[first_id]
        second_match, second_slot = locations[second_id]
        setattr(first_match, first_slot, second_id)
        setattr(second_match, second_slot, first_id)
        errors = validate_pairing_draft(
            [Pairing(item.player_a_id, item.player_b_id) for item in matches],
            {item.id for item in self.repository.active_participants(tournament_id)},
            self._prior_pairs(tournament_id, round_item.round_no),
        )
        if errors:
            self.db.rollback()
            raise AppError("INVALID_PAIRING_DRAFT", "调整后的对阵未通过校验", details={"errors": errors})
        add_audit_log(
            self.db,
            operator_id=operator_id,
            tournament_id=tournament_id,
            action_type="SWISS_PAIRING_SWAPPED",
            target_type="swiss_round",
            target_id=round_item.id,
            before={"first": str(first_id), "second": str(second_id)},
            after={"first": str(second_id), "second": str(first_id)},
        )
        self.db.commit()
        return self.round_response(round_item)

    def publish_round(self, tournament_id: UUID, round_id: UUID, operator_id: UUID) -> RoundResponse:
        self._require_swiss_tournament(tournament_id, for_update=True)
        round_item = self.repository.get_round(tournament_id, round_id, for_update=True)
        if round_item is None:
            raise AppError("ROUND_NOT_FOUND", "轮次不存在", status_code=404)
        if round_item.status != SwissRoundStatus.DRAFT.value:
            raise AppError("ROUND_ALREADY_PUBLISHED", "轮次已经发布", status_code=409)
        active_ids = {item.id for item in self.repository.active_participants(tournament_id)}
        matches = self.repository.round_matches(round_id)
        errors = validate_pairing_draft(
            [Pairing(item.player_a_id, item.player_b_id) for item in matches],
            active_ids,
            self._prior_pairs(tournament_id, round_item.round_no),
        )
        if errors:
            raise AppError("INVALID_PAIRING_DRAFT", "对阵预览未通过发布校验", details={"errors": errors})

        previous_rounds = [item for item in self.repository.rounds(tournament_id) if item.round_no < round_item.round_no]
        if previous_rounds and previous_rounds[-1].status != SwissRoundStatus.COMPLETED.value:
            raise AppError("PREVIOUS_ROUND_INCOMPLETE", "上一轮尚未完成", status_code=409)
        for previous in previous_rounds:
            for match in self.repository.round_matches(previous.id):
                match.result_locked = True

        round_item.status = SwissRoundStatus.PUBLISHED.value
        round_item.published_at = datetime.now(UTC)
        participant_by_id = {item.id: item for item in self.repository.active_participants(tournament_id)}
        for match in matches:
            if match.player_b_id is None:
                match.status = MatchStatus.COMPLETED.value
                match.winner_id = match.player_a_id
                match.result_source = ResultSource.BYE.value
                participant_by_id[match.player_a_id].bye_count += 1
        add_audit_log(
            self.db,
            operator_id=operator_id,
            tournament_id=tournament_id,
            action_type="SWISS_ROUND_PUBLISHED",
            target_type="swiss_round",
            target_id=round_item.id,
            after={"round_no": round_item.round_no},
        )
        self.db.flush()
        self._finish_round_if_ready(round_item)
        self.db.commit()
        return self.round_response(round_item)

    def submit_result(self, match_id: UUID, user_id: UUID, submitted: SubmittedResult) -> MyMatchResponse:
        match = self.repository.get_match(match_id, for_update=True)
        if match is None or match.stage != MatchStage.SWISS.value:
            raise AppError("MATCH_NOT_FOUND", "对局不存在", status_code=404)
        round_item = self.db.get(SwissRound, match.swiss_round_id)
        if round_item is None or round_item.status == SwissRoundStatus.DRAFT.value:
            raise AppError("MATCH_NOT_PUBLISHED", "对局尚未发布", status_code=409)
        participant = self.repository.participant_for_user(match.tournament_id, user_id)
        if participant is None or participant.id not in {match.player_a_id, match.player_b_id}:
            raise AppError("MATCH_NOT_FOUND", "这不是你的对局", status_code=404)
        if match.result_locked:
            raise AppError("MATCH_RESULT_LOCKED", "下一轮已发布，本轮赛果已锁定", status_code=409)
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
                submitted_result=submitted.value,
            ))
        else:
            submission.submitted_result = submitted.value
        self.db.flush()
        self._apply_player_submissions(match, round_item)
        self.db.commit()
        return self.my_match_response(match, participant.id)

    def resolve_match(
        self,
        match_id: UUID,
        winner_id: UUID,
        reason: str | None,
        operator_id: UUID,
    ) -> MatchResponse:
        match = self.repository.get_match(match_id, for_update=True)
        if match is None or match.stage != MatchStage.SWISS.value:
            raise AppError("MATCH_NOT_FOUND", "对局不存在", status_code=404)
        round_item = self.db.get(SwissRound, match.swiss_round_id)
        if round_item is None or round_item.status == SwissRoundStatus.DRAFT.value:
            raise AppError("MATCH_NOT_PUBLISHED", "对局尚未发布，不能裁定赛果", status_code=409)
        if match.result_locked:
            raise AppError("MATCH_RESULT_LOCKED", "下一轮已发布，本轮赛果已锁定", status_code=409)
        if winner_id not in {match.player_a_id, match.player_b_id} or match.player_b_id is None:
            raise AppError("INVALID_MATCH_WINNER", "裁定胜者必须是本场选手", status_code=400)
        normalized_reason = reason.strip() if reason and reason.strip() else None
        before = {"winner_id": str(match.winner_id) if match.winner_id else None, "status": match.status}
        match.winner_id = winner_id
        match.status = MatchStatus.COMPLETED.value
        match.result_source = ResultSource.ADMIN.value
        self.db.flush()
        self._discard_later_draft(match.tournament_id, round_item.round_no)
        self._finish_round_if_ready(round_item, force_recompute=True)
        add_audit_log(
            self.db,
            operator_id=operator_id,
            tournament_id=match.tournament_id,
            action_type="SWISS_MATCH_RESOLVED",
            target_type="match",
            target_id=match.id,
            before=before,
            after={"winner_id": str(winner_id), "status": match.status, "reason": normalized_reason},
        )
        self.db.commit()
        return self.match_response(match, admin=True)

    def withdraw(self, tournament_id: UUID, participant_id: UUID, operator_id: UUID) -> WithdrawResponse:
        self._require_swiss_tournament(tournament_id, for_update=True)
        participant = self.db.get(TournamentParticipant, participant_id)
        if participant is None or participant.tournament_id != tournament_id:
            raise AppError("PARTICIPANT_NOT_FOUND", "正式参赛选手不存在", status_code=404)
        if participant.status != ParticipantStatus.ACTIVE.value:
            raise AppError("PARTICIPANT_ALREADY_WITHDRAWN", "该选手已经退赛", status_code=409)
        latest = self.repository.latest_round(tournament_id)
        if latest and latest.status == SwissRoundStatus.PUBLISHED.value:
            raise AppError("WITHDRAWAL_WINDOW_CLOSED", "当前轮尚未结束，不能退赛", status_code=409)
        if latest and latest.status == SwissRoundStatus.DRAFT.value:
            after_round_no = latest.round_no - 1
            self.repository.discard_round(latest)
        else:
            after_round_no = latest.round_no if latest else 0
        participant.status = ParticipantStatus.WITHDRAWN.value
        self.db.add(Withdrawal(
            tournament_id=tournament_id,
            participant_id=participant.id,
            after_round_no=after_round_no,
            operator_id=operator_id,
        ))
        add_audit_log(
            self.db,
            operator_id=operator_id,
            tournament_id=tournament_id,
            action_type="SWISS_PARTICIPANT_WITHDRAWN",
            target_type="tournament_participant",
            target_id=participant.id,
            before={"status": ParticipantStatus.ACTIVE.value},
            after={"status": ParticipantStatus.WITHDRAWN.value, "after_round_no": after_round_no},
        )
        self.db.commit()
        return WithdrawResponse(participant_id=participant.id, status=participant.status, after_round_no=after_round_no)

    def overview(self, tournament_id: UUID) -> SwissOverviewResponse:
        tournament = self.tournaments.require(tournament_id)
        if tournament.status not in {TournamentStatus.SWISS.value, TournamentStatus.ELIMINATION.value, TournamentStatus.ENDED.value}:
            raise AppError("SWISS_NOT_STARTED", "赛事尚未进入瑞士轮", status_code=409)
        rounds = self.repository.rounds(tournament_id, published_only=True)
        latest = rounds[-1] if rounds else None
        ranking_round_no, rankings = self.repository.latest_rankings(tournament_id)
        return SwissOverviewResponse(
            current_round_no=latest.round_no if latest else 0,
            current_round_status=SwissRoundStatus(latest.status) if latest else None,
            completed_rounds=sum(item.status == SwissRoundStatus.COMPLETED.value for item in rounds),
            total_rounds=tournament.swiss_rounds or 0,
            ranking_round_no=ranking_round_no,
            rankings=[self._ranking_response(item) for item in rankings],
        )

    def published_rounds(self, tournament_id: UUID) -> list[RoundResponse]:
        self.tournaments.require(tournament_id)
        return [self.round_response(item, admin=False) for item in self.repository.rounds(tournament_id, published_only=True)]

    def admin_rounds(self, tournament_id: UUID) -> list[RoundResponse]:
        self._require_swiss_tournament(tournament_id)
        return [self.round_response(item, admin=True) for item in self.repository.rounds(tournament_id)]

    def my_matches(self, tournament_id: UUID, user_id: UUID) -> list[MyMatchResponse]:
        tournament = self.tournaments.require(tournament_id)
        if tournament.status not in {
            TournamentStatus.SWISS.value,
            TournamentStatus.ELIMINATION.value,
            TournamentStatus.ENDED.value,
        }:
            raise AppError("SWISS_NOT_STARTED", "赛事尚未进入瑞士轮", status_code=409)
        participant = self.repository.participant_for_user(tournament_id, user_id)
        if participant is None:
            raise AppError("PARTICIPANT_NOT_FOUND", "你不是本届赛事正式参赛选手", status_code=404)
        responses: list[MyMatchResponse] = []
        for round_item in self.repository.rounds(tournament_id, published_only=True):
            for match in self.repository.round_matches(round_item.id):
                if participant.id in {match.player_a_id, match.player_b_id}:
                    responses.append(self.my_match_response(match, participant.id))
        return responses

    def round_response(self, round_item: SwissRound, *, admin: bool = True) -> RoundResponse:
        return RoundResponse(
            id=round_item.id,
            round_no=round_item.round_no,
            status=SwissRoundStatus(round_item.status),
            published_at=round_item.published_at,
            completed_at=round_item.completed_at,
            matches=[self.match_response(item, admin=admin) for item in self.repository.round_matches(round_item.id)],
        )

    def match_response(self, match: Match, *, admin: bool) -> MatchResponse:
        submissions = {item.participant_id: SubmittedResult(item.submitted_result) for item in self.repository.submissions(match.id)}
        warnings: list[str] = []
        if match.player_b_id is None:
            prior_byes = match.player_a.bye_count - (1 if match.status == MatchStatus.COMPLETED.value else 0)
            if prior_byes > 0:
                warnings.append("重复 BYE")
        else:
            if frozenset((match.player_a_id, match.player_b_id)) in self._prior_pairs(match.tournament_id, match.round_no):
                warnings.append("重复对手")
            standings = {item.participant_id: item for item in self._standing_inputs(match.tournament_id, active_only=False)}
            if standings[match.player_a_id].wins != standings[match.player_b_id].wins and match.status == MatchStatus.WAITING.value:
                warnings.append("跨胜场组")
        return MatchResponse(
            id=match.id,
            round_no=match.round_no,
            table_no=match.table_no,
            player_a_id=match.player_a_id,
            player_a_nickname=match.player_a.nickname_snapshot,
            player_b_id=match.player_b_id,
            player_b_nickname=match.player_b.nickname_snapshot if match.player_b else None,
            winner_id=match.winner_id,
            status=MatchStatus(match.status),
            result_source=match.result_source,
            result_locked=match.result_locked,
            warnings=warnings,
            player_a_result=submissions.get(match.player_a_id) if admin else None,
            player_b_result=submissions.get(match.player_b_id) if admin and match.player_b_id else None,
        )

    def my_match_response(self, match: Match, participant_id: UUID) -> MyMatchResponse:
        base = self.match_response(match, admin=False)
        submissions = {item.participant_id: SubmittedResult(item.submitted_result) for item in self.repository.submissions(match.id)}
        opponent_id = match.player_b_id if participant_id == match.player_a_id else match.player_a_id
        return MyMatchResponse(
            **base.model_dump(),
            my_participant_id=participant_id,
            my_submission=submissions.get(participant_id),
            opponent_submission=submissions.get(opponent_id),
            opponent_submitted=opponent_id in submissions,
        )

    @staticmethod
    def _ranking_response(item: RankingSnapshot) -> RankingResponse:
        return RankingResponse(
            participant_id=item.participant_id,
            nickname=item.participant.nickname_snapshot,
            participant_status=item.participant.status,
            rank=item.rank,
            wins=item.wins,
            losses=item.losses,
            omw=float(item.omw),
            loss_round_score=item.loss_round_score,
        )

    def _apply_player_submissions(self, match: Match, round_item: SwissRound) -> None:
        submissions = {item.participant_id: item.submitted_result for item in self.repository.submissions(match.id)}
        if match.player_b_id is None or len(submissions) < 2:
            match.status = MatchStatus.WAITING.value
            match.winner_id = None
            match.result_source = None
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

    def _finish_round_if_ready(self, round_item: SwissRound, *, force_recompute: bool = False) -> None:
        if self.repository.incomplete_count(round_item.id):
            return
        if round_item.status != SwissRoundStatus.COMPLETED.value:
            round_item.status = SwissRoundStatus.COMPLETED.value
            round_item.completed_at = datetime.now(UTC)
        if force_recompute or not round_item.rankings:
            self._recompute_rankings(round_item)

    def _recompute_rankings(self, round_item: SwissRound) -> None:
        self.repository.delete_rankings(round_item.id)
        players = self._standing_inputs(round_item.tournament_id, active_only=False)
        records = [
            MatchRecord(
                round_no=match.round_no,
                player_a_id=match.player_a_id,
                player_b_id=match.player_b_id,
                winner_id=match.winner_id,
            )
            for match in self.repository.completed_matches(round_item.tournament_id, through_round=round_item.round_no)
            if match.winner_id is not None
        ]
        for ranking in calculate_rankings(players, records):
            self.db.add(RankingSnapshot(
                tournament_id=round_item.tournament_id,
                swiss_round_id=round_item.id,
                participant_id=ranking.participant_id,
                rank=ranking.rank,
                wins=ranking.wins,
                losses=ranking.losses,
                omw=ranking.omw,
                loss_round_score=ranking.loss_round_score,
            ))
        self.db.flush()

    def _discard_later_draft(self, tournament_id: UUID, after_round_no: int) -> None:
        latest = self.repository.latest_round(tournament_id)
        if latest and latest.status == SwissRoundStatus.DRAFT.value and latest.round_no > after_round_no:
            self.repository.discard_round(latest)
            self.db.flush()
