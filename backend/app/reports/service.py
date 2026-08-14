from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.audit.service import add_audit_log
from app.core.errors import AppError
from app.deck_submissions.models import DeckSubmission, DeckSubmissionStatus
from app.deck_submissions.repository import DeckSubmissionRepository
from app.matches.models import Match
from app.messages.models import MessageType
from app.messages.service import add_automatic_message
from app.playoffs.models import PlayoffRound
from app.playoffs.repository import PlayoffRepository
from app.reports.models import WeeklyReport, WeeklyReportStatus
from app.reports.repository import WeeklyReportRepository
from app.reports.schemas import WeeklyReportResponse
from app.swiss.models import RankingSnapshot, SwissRound, SwissRoundStatus
from app.tournaments.models import TournamentStatus
from app.tournaments.service import TournamentService


def report_response(item: WeeklyReport) -> WeeklyReportResponse:
    return WeeklyReportResponse(
        id=item.id,
        tournament_id=item.tournament_id,
        tournament_name=item.tournament.name,
        status=WeeklyReportStatus(item.status),
        snapshot_content=item.snapshot_content,
        published_at=item.published_at,
        created_at=item.created_at,
    )


class WeeklyReportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = WeeklyReportRepository(db)

    def generate(self, tournament_id: UUID, operator_id: UUID) -> WeeklyReport:
        tournament = TournamentService(self.db).require(tournament_id, for_update=True)
        if tournament.status != TournamentStatus.ENDED.value:
            raise AppError("TOURNAMENT_NOT_ENDED", "赛事结束后才能生成周报", status_code=409)
        existing = self.repository.for_tournament(tournament_id, for_update=True)
        if existing is not None and existing.status == WeeklyReportStatus.PUBLISHED.value:
            raise AppError("REPORT_PUBLISHED", "周报已经发布，不可重新生成", status_code=409)
        decks = DeckSubmissionRepository(self.db).for_tournament(tournament_id)
        approved = [item for item in decks if item.status == DeckSubmissionStatus.APPROVED.value]
        if len(decks) != 4 or len(approved) != 4:
            raise AppError(
                "DECK_APPROVALS_INCOMPLETE",
                "四强卡组截图必须 4/4 审核通过后才能生成周报",
                status_code=409,
                details={"approved": len(approved), "required": 4},
            )
        snapshot = self._snapshot(tournament, approved)
        if existing is None:
            existing = WeeklyReport(
                tournament_id=tournament_id,
                status=WeeklyReportStatus.DRAFT.value,
                snapshot_content=snapshot,
                generated_by_id=operator_id,
            )
            self.db.add(existing)
        else:
            existing.snapshot_content = snapshot
            existing.generated_by_id = operator_id
        self.db.flush()
        add_audit_log(
            self.db,
            operator_id=operator_id,
            tournament_id=tournament_id,
            action_type="WEEKLY_REPORT_GENERATED",
            target_type="weekly_report",
            target_id=existing.id,
            after={"tournament_id": str(tournament_id), "status": WeeklyReportStatus.DRAFT.value},
        )
        self.db.commit()
        return self.repository.get(existing.id)  # type: ignore[return-value]

    def publish(self, report_id: UUID, operator_id: UUID) -> WeeklyReport:
        item = self.repository.get(report_id, for_update=True)
        if item is None:
            raise AppError("REPORT_NOT_FOUND", "周报不存在", status_code=404)
        if item.status != WeeklyReportStatus.DRAFT.value:
            raise AppError("REPORT_ALREADY_PUBLISHED", "周报已经发布，不可重复发布或撤回", status_code=409)
        item.status = WeeklyReportStatus.PUBLISHED.value
        item.published_at = datetime.now(UTC)
        add_audit_log(
            self.db,
            operator_id=operator_id,
            tournament_id=item.tournament_id,
            action_type="WEEKLY_REPORT_PUBLISHED",
            target_type="weekly_report",
            target_id=item.id,
            before={"status": WeeklyReportStatus.DRAFT.value},
            after={"status": WeeklyReportStatus.PUBLISHED.value, "published_at": item.published_at.isoformat()},
        )
        for participant in item.tournament.participants:
            add_automatic_message(
                self.db,
                recipient_id=participant.user_id,
                message_type=MessageType.REPORT_PUBLISHED,
                title="赛事周报已发布",
                body=f"“{item.tournament.name}”的赛事周报已经发布。",
                action_url=f"/reports/{item.id}",
                related_type="weekly_report",
                related_id=item.id,
                dedupe_key=f"report:{item.id}:published:{participant.user_id}",
            )
        self.db.commit()
        return self.repository.get(item.id)  # type: ignore[return-value]

    def _snapshot(self, tournament, decks: list[DeckSubmission]) -> dict:
        latest_swiss = self.db.scalar(select(SwissRound).where(
            SwissRound.tournament_id == tournament.id,
            SwissRound.status == SwissRoundStatus.COMPLETED.value,
        ).order_by(SwissRound.round_no.desc()).limit(1))
        rankings = []
        if latest_swiss is not None:
            rows = list(self.db.scalars(select(RankingSnapshot).where(
                RankingSnapshot.swiss_round_id == latest_swiss.id,
            ).options(selectinload(RankingSnapshot.participant)).order_by(RankingSnapshot.rank)))
            rankings = [{
                "rank": row.rank,
                "nickname": row.participant.nickname_snapshot,
                "wins": row.wins,
                "losses": row.losses,
                "omw": float(row.omw),
                "loss_round_score": row.loss_round_score,
            } for row in rows]

        playoff_rounds = []
        playoff_repository = PlayoffRepository(self.db)
        for round_item in playoff_repository.rounds(tournament.id, published_only=True):
            matches = playoff_repository.round_matches(round_item.id)
            playoff_rounds.append({
                "name": round_item.name,
                "stage_no": round_item.stage_no,
                "matches": [{
                    "seed_a": match.seed_a,
                    "player_a": match.player_a.nickname_snapshot,
                    "seed_b": match.seed_b,
                    "player_b": match.player_b.nickname_snapshot if match.player_b else "",
                    "winner": match.winner.nickname_snapshot if match.winner else "",
                } for match in matches],
            })
        ordered_decks = sorted(decks, key=lambda item: item.placement)
        return {
            "template_version": 1,
            "tournament": {
                "name": tournament.name,
                "competition_time": (tournament.started_at or tournament.planned_start_at).isoformat(),
                "ended_at": tournament.ended_at.isoformat() if tournament.ended_at else None,
                "participant_count": len(tournament.participants),
                "swiss_rounds": tournament.swiss_rounds,
                "playoff_size": tournament.playoff_size,
                "format": "BO1",
            },
            "podium": [{
                "placement": item.placement,
                "nickname": item.participant.nickname_snapshot,
                "image_url": item.image_path,
            } for item in ordered_decks],
            "swiss_rankings": rankings,
            "playoff_rounds": playoff_rounds,
        }
