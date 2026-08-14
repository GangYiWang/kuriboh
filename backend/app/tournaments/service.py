from datetime import UTC, datetime
import secrets
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.orm import Session

from app.audit.service import add_audit_log
from app.content.models import BanlistVersion
from app.core.errors import AppError
from app.deck_submissions.models import DeckSubmission
from app.matches.models import Match, MatchStatus
from app.reports.models import WeeklyReport, WeeklyReportStatus
from app.playoffs.models import PlayoffRound, PlayoffRoundStatus
from app.registrations.models import ParticipantStatus, RegistrationStatus, TournamentParticipant
from app.registrations.repository import RegistrationRepository
from app.tournaments.models import Tournament, TournamentStatus
from app.tournaments.repository import TournamentRepository
from app.tournaments.schemas import (
    MyTournamentListResponse,
    MyTournamentMatchSummary,
    MyTournamentRankingSummary,
    MyTournamentResponse,
    TournamentCreateRequest,
    TournamentResponse,
    TournamentUpdateRequest,
)
from app.swiss.models import RankingSnapshot, SwissRound, SwissRoundStatus


CORE_FIELDS = {"max_players", "swiss_rounds", "playoff_size", "banlist_version_id"}
TOURNAMENT_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def tournament_response(
    tournament: Tournament,
    approved_count: int,
    pending_count: int,
) -> TournamentResponse:
    return TournamentResponse(
        id=tournament.id,
        code=tournament.code,
        created_by_id=tournament.created_by_id,
        name=tournament.name,
        description=tournament.description,
        planned_start_at=tournament.planned_start_at,
        max_players=tournament.max_players,
        swiss_rounds=tournament.swiss_rounds,
        playoff_size=tournament.playoff_size,
        banlist_version_id=tournament.banlist_version_id,
        banlist_version=tournament.banlist_version.version if tournament.banlist_version else None,
        status=TournamentStatus(tournament.status),
        published_at=tournament.published_at,
        started_at=tournament.started_at,
        ended_at=tournament.ended_at,
        approved_count=approved_count,
        pending_count=pending_count,
        created_at=tournament.created_at,
        updated_at=tournament.updated_at,
    )


class TournamentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = TournamentRepository(db)
        self.registrations = RegistrationRepository(db)

    def require(self, tournament_id: UUID, *, for_update: bool = False) -> Tournament:
        tournament = self.repository.get(tournament_id, for_update=for_update)
        if tournament is None:
            raise AppError("TOURNAMENT_NOT_FOUND", "赛事不存在", status_code=404)
        return tournament

    def require_owner(
        self,
        tournament_id: UUID,
        user_id: UUID,
        *,
        for_update: bool = False,
    ) -> Tournament:
        tournament = self.require(tournament_id, for_update=for_update)
        if tournament.created_by_id != user_id:
            raise AppError("TOURNAMENT_OWNER_REQUIRED", "只有赛事创建者可以管理该赛事", status_code=403)
        return tournament

    def get_by_code(self, code: str) -> Tournament:
        tournament = self.repository.get_by_code(code)
        if tournament is None:
            raise AppError("TOURNAMENT_NOT_FOUND", "未找到该比赛码对应的赛事", status_code=404)
        return tournament

    def created_tournaments(
        self,
        user_id: UUID,
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[Tournament], int]:
        return self.repository.list_created_by(user_id, offset=offset, limit=limit)

    def my_tournaments(self, user_id: UUID) -> MyTournamentListResponse:
        registrations = self.repository.registrations_for_user(user_id)
        items: list[MyTournamentResponse] = []
        for registration in registrations:
            participant = registration.participant
            current_match = None
            ranking = None
            if participant is not None:
                match = self.db.scalar(
                    select(Match)
                    .where(
                        Match.tournament_id == registration.tournament_id,
                        or_(Match.player_a_id == participant.id, Match.player_b_id == participant.id),
                        Match.status != MatchStatus.COMPLETED.value,
                    )
                    .options(selectinload(Match.player_a), selectinload(Match.player_b))
                    .order_by(Match.created_at.desc())
                    .limit(1)
                )
                if match is not None:
                    opponent = match.player_b if match.player_a_id == participant.id else match.player_a
                    current_match = MyTournamentMatchSummary(
                        id=match.id,
                        stage=match.stage,
                        round_no=match.round_no,
                        table_no=match.table_no,
                        opponent_nickname=opponent.nickname_snapshot if opponent else None,
                        status=match.status,
                    )
                ranking_row = self.db.scalar(
                    select(RankingSnapshot)
                    .where(RankingSnapshot.participant_id == participant.id)
                    .order_by(RankingSnapshot.created_at.desc())
                    .limit(1)
                )
                if ranking_row is not None:
                    ranking = MyTournamentRankingSummary(
                        rank=ranking_row.rank,
                        wins=ranking_row.wins,
                        losses=ranking_row.losses,
                    )
            report_id = self.db.scalar(select(WeeklyReport.id).where(
                WeeklyReport.tournament_id == registration.tournament_id,
                WeeklyReport.status == WeeklyReportStatus.PUBLISHED.value,
            ))
            tournament = registration.tournament
            items.append(MyTournamentResponse(
                id=tournament.id,
                name=tournament.name,
                status=TournamentStatus(tournament.status),
                planned_start_at=tournament.planned_start_at,
                registration_status=registration.status,
                participant_status=participant.status if participant else None,
                current_match=current_match,
                ranking=ranking,
                report_id=report_id,
            ))
        return MyTournamentListResponse(items=items, total=len(items))

    def create_draft(self, request: TournamentCreateRequest, user_id: UUID) -> Tournament:
        if request.banlist_version_id is not None and self.db.get(BanlistVersion, request.banlist_version_id) is None:
            raise AppError("BANLIST_NOT_FOUND", "禁卡表版本不存在", status_code=404)
        self._validate_sizes(request.max_players, request.playoff_size)
        tournament = Tournament(
            **request.model_dump(),
            status=TournamentStatus.DRAFT.value,
            created_by_id=user_id,
        )
        self.db.add(tournament)
        self.db.commit()
        return self.require(tournament.id)

    def create_and_publish(self, request: TournamentCreateRequest, user_id: UUID) -> Tournament:
        self._validate_publish_request(request)
        if self.db.get(BanlistVersion, request.banlist_version_id) is None:
            raise AppError("BANLIST_NOT_FOUND", "禁卡表版本不存在", status_code=404)
        self._validate_sizes(request.max_players, request.playoff_size)
        tournament = Tournament(
            **request.model_dump(),
            code=self._generate_code(),
            status=TournamentStatus.REGISTRATION.value,
            published_at=datetime.now(UTC),
            created_by_id=user_id,
        )
        self.db.add(tournament)
        self.db.flush()
        add_audit_log(
            self.db,
            operator_id=user_id,
            tournament_id=tournament.id,
            action_type="TOURNAMENT_CREATED_AND_PUBLISHED",
            target_type="tournament",
            target_id=tournament.id,
            before=None,
            after={"status": TournamentStatus.REGISTRATION.value, "code": tournament.code},
        )
        self.db.commit()
        return self.require(tournament.id)

    def update(self, tournament: Tournament, request: TournamentUpdateRequest) -> Tournament:
        supplied = request.model_fields_set
        if TournamentStatus(tournament.status) in {
            TournamentStatus.SWISS,
            TournamentStatus.ELIMINATION,
            TournamentStatus.ENDED,
        } and CORE_FIELDS.intersection(supplied):
            raise AppError("CORE_CONFIG_LOCKED", "赛事开始后核心配置不可修改", status_code=409)

        values = request.model_dump(exclude_unset=True)
        if "banlist_version_id" in values and values["banlist_version_id"] is not None:
            if self.db.get(BanlistVersion, values["banlist_version_id"]) is None:
                raise AppError("BANLIST_NOT_FOUND", "禁卡表版本不存在", status_code=404)
        max_players = values.get("max_players", tournament.max_players)
        playoff_size = values.get("playoff_size", tournament.playoff_size)
        self._validate_sizes(max_players, playoff_size)
        if tournament.status != TournamentStatus.DRAFT.value:
            prospective = {
                field: values.get(field, getattr(tournament, field))
                for field in CORE_FIELDS | {"planned_start_at"}
            }
            if any(value is None for value in prospective.values()):
                raise AppError("INCOMPLETE_TOURNAMENT", "已发布赛事的核心配置不能为空", status_code=409)
        for field, value in values.items():
            setattr(tournament, field, value)
        self.db.commit()
        return self.require(tournament.id)

    def publish(self, tournament_id: UUID, operator_id: UUID) -> Tournament:
        tournament = self.require(tournament_id, for_update=True)
        if tournament.status != TournamentStatus.DRAFT.value:
            raise AppError("INVALID_TOURNAMENT_STATE", "只有草稿赛事可以发布", status_code=409)
        missing = [
            label
            for field, label in (
                ("planned_start_at", "预计比赛开始时间"),
                ("max_players", "最大参赛人数"),
                ("swiss_rounds", "瑞士轮轮数"),
                ("playoff_size", "淘汰赛晋级人数"),
                ("banlist_version_id", "禁卡表版本"),
            )
            if getattr(tournament, field) is None
        ]
        if missing:
            raise AppError("INCOMPLETE_TOURNAMENT", "发布前请补全赛事核心配置", details={"missing": missing})
        self._validate_sizes(tournament.max_players, tournament.playoff_size)
        if tournament.code is None:
            tournament.code = self._generate_code()
        tournament.status = TournamentStatus.REGISTRATION.value
        tournament.published_at = datetime.now(UTC)
        add_audit_log(
            self.db,
            operator_id=operator_id,
            tournament_id=tournament.id,
            action_type="TOURNAMENT_PUBLISHED",
            target_type="tournament",
            target_id=tournament.id,
            before={"status": TournamentStatus.DRAFT.value},
            after={"status": TournamentStatus.REGISTRATION.value},
        )
        self.db.commit()
        return self.require(tournament.id)

    def start(self, tournament_id: UUID, operator_id: UUID) -> Tournament:
        tournament = self.require(tournament_id, for_update=True)
        if tournament.status != TournamentStatus.REGISTRATION.value:
            raise AppError("INVALID_TOURNAMENT_STATE", "只有报名中的赛事可以开始", status_code=409)
        pending_count = self.registrations.count_by_status(tournament.id, RegistrationStatus.PENDING)
        if pending_count:
            raise AppError(
                "PENDING_REGISTRATIONS",
                "仍有待审核报名，处理完成后才能开始赛事",
                status_code=409,
                details={"pending_count": pending_count},
            )
        registrations, _ = self.registrations.list_for_tournament(tournament.id)
        participant_count = 0
        for registration in registrations:
            if registration.status == RegistrationStatus.APPROVED.value:
                self.db.add(TournamentParticipant(
                    tournament_id=tournament.id,
                    user_id=registration.user_id,
                    registration_id=registration.id,
                    nickname_snapshot=registration.user.nickname,
                    status=ParticipantStatus.ACTIVE.value,
                    bye_count=0,
                ))
                participant_count += 1
        tournament.status = TournamentStatus.SWISS.value
        tournament.started_at = datetime.now(UTC)
        add_audit_log(
            self.db,
            operator_id=operator_id,
            tournament_id=tournament.id,
            action_type="TOURNAMENT_STARTED",
            target_type="tournament",
            target_id=tournament.id,
            before={"status": TournamentStatus.REGISTRATION.value},
            after={"status": TournamentStatus.SWISS.value, "participant_count": participant_count},
        )
        self.db.commit()
        return self.require(tournament.id)

    def end(self, tournament_id: UUID, operator_id: UUID) -> Tournament:
        tournament = self.require(tournament_id, for_update=True)
        if tournament.status != TournamentStatus.ELIMINATION.value:
            raise AppError("INVALID_TOURNAMENT_STATE", "只有淘汰赛中的赛事可以结束", status_code=409)
        final_round = self.db.scalar(select(PlayoffRound).where(
            PlayoffRound.tournament_id == tournament.id,
            PlayoffRound.bracket_size == 2,
            PlayoffRound.status == PlayoffRoundStatus.COMPLETED.value,
        ))
        if final_round is None:
            raise AppError("FINAL_NOT_COMPLETED", "决赛完成后才能结束赛事", status_code=409)
        final_match = self.db.scalar(select(Match).where(
            Match.playoff_round_id == final_round.id,
            Match.status == MatchStatus.COMPLETED.value,
        ))
        if final_match is None or final_match.winner_id is None or final_match.player_b_id is None:
            raise AppError("FINAL_NOT_COMPLETED", "决赛赛果尚未确认", status_code=409)

        placements = self._final_four_placements(tournament.id, final_match)
        if len(placements) != 4:
            raise AppError("FINAL_FOUR_UNAVAILABLE", "无法从赛事结果确定最终四强", status_code=409)
        for placement, participant_id in enumerate(placements, start=1):
            self.db.add(DeckSubmission(
                tournament_id=tournament.id,
                participant_id=participant_id,
                placement=placement,
            ))
        self.db.execute(
            update(Match).where(Match.tournament_id == tournament.id).values(result_locked=True)
        )
        tournament.status = TournamentStatus.ENDED.value
        tournament.ended_at = datetime.now(UTC)
        add_audit_log(
            self.db,
            operator_id=operator_id,
            tournament_id=tournament.id,
            action_type="TOURNAMENT_ENDED",
            target_type="tournament",
            target_id=tournament.id,
            before={"status": TournamentStatus.ELIMINATION.value},
            after={"status": TournamentStatus.ENDED.value, "final_four": [str(item) for item in placements]},
        )
        self.db.commit()
        return self.require(tournament.id)

    def _final_four_placements(self, tournament_id: UUID, final_match: Match) -> list[UUID]:
        champion_id = final_match.winner_id
        runner_up_id = final_match.player_b_id if champion_id == final_match.player_a_id else final_match.player_a_id
        placements = [champion_id, runner_up_id]
        semifinal = self.db.scalar(select(PlayoffRound).where(
            PlayoffRound.tournament_id == tournament_id,
            PlayoffRound.bracket_size == 4,
            PlayoffRound.status == PlayoffRoundStatus.COMPLETED.value,
        ))
        if semifinal is not None:
            semifinal_matches = list(self.db.scalars(
                select(Match).where(Match.playoff_round_id == semifinal.id).order_by(Match.table_no)
            ))
            semifinal_losers: list[tuple[int, UUID]] = []
            for match in semifinal_matches:
                if match.winner_id is None or match.player_b_id is None:
                    continue
                loser_id = match.player_b_id if match.winner_id == match.player_a_id else match.player_a_id
                loser_seed = match.seed_b if loser_id == match.player_b_id else match.seed_a
                semifinal_losers.append((loser_seed or 9999, loser_id))
            placements.extend(item[1] for item in sorted(semifinal_losers))

        if len(set(placements)) < 4:
            latest_swiss = self.db.scalar(select(SwissRound).where(
                SwissRound.tournament_id == tournament_id,
                SwissRound.status == SwissRoundStatus.COMPLETED.value,
            ).order_by(SwissRound.round_no.desc()).limit(1))
            if latest_swiss is not None:
                ranked_ids = list(self.db.scalars(select(RankingSnapshot.participant_id).where(
                    RankingSnapshot.swiss_round_id == latest_swiss.id,
                ).order_by(RankingSnapshot.rank)))
                placements.extend(item for item in ranked_ids if item not in placements)
        return list(dict.fromkeys(placements))[:4]

    @staticmethod
    def _validate_sizes(max_players: int | None, playoff_size: int | None) -> None:
        if max_players is not None and playoff_size is not None and playoff_size > max_players:
            raise AppError("INVALID_PLAYOFF_SIZE", "淘汰赛晋级人数不能超过最大参赛人数")

    @staticmethod
    def _validate_publish_request(request: TournamentCreateRequest) -> None:
        missing = [
            label
            for field, label in (
                ("planned_start_at", "预计比赛开始时间"),
                ("max_players", "最大参赛人数"),
                ("swiss_rounds", "瑞士轮轮数"),
                ("playoff_size", "淘汰赛晋级人数"),
                ("banlist_version_id", "禁卡表版本"),
            )
            if getattr(request, field) is None
        ]
        if missing:
            raise AppError(
                "INCOMPLETE_TOURNAMENT",
                "发布前请补全赛事核心配置",
                details={"missing": missing},
            )

    def _generate_code(self) -> str:
        for _ in range(32):
            code = "".join(secrets.choice(TOURNAMENT_CODE_ALPHABET) for _ in range(6))
            if self.db.scalar(select(Tournament.id).where(Tournament.code == code)) is None:
                return code
        raise AppError("TOURNAMENT_CODE_UNAVAILABLE", "暂时无法生成比赛码，请稍后重试", status_code=503)
