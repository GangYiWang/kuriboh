from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.audit.service import add_audit_log
from app.content.storage import LocalImageStorage
from app.core.errors import AppError
from app.deck_submissions.models import DeckSubmission, DeckSubmissionStatus
from app.deck_submissions.repository import DeckSubmissionRepository
from app.deck_submissions.schemas import DeckSubmissionListResponse, DeckSubmissionResponse
from app.reports.models import WeeklyReport, WeeklyReportStatus
from app.tournaments.models import TournamentStatus
from app.tournaments.service import TournamentService


def deck_response(item: DeckSubmission) -> DeckSubmissionResponse:
    return DeckSubmissionResponse(
        id=item.id,
        tournament_id=item.tournament_id,
        participant_id=item.participant_id,
        user_id=item.participant.user_id,
        nickname=item.participant.nickname_snapshot,
        placement=item.placement,
        image_url=item.image_path,
        status=DeckSubmissionStatus(item.status),
        review_note=item.review_note,
        reviewed_at=item.reviewed_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


class DeckSubmissionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = DeckSubmissionRepository(db)

    def my_submission(self, tournament_id: UUID, user_id: UUID) -> DeckSubmission:
        TournamentService(self.db).require(tournament_id)
        item = self.repository.for_user(tournament_id, user_id)
        if item is None:
            raise AppError("NOT_FINAL_FOUR", "只有本届赛事最终四强可以提交卡组截图", status_code=403)
        return item

    def upload(self, tournament_id: UUID, user_id: UUID, content: bytes) -> DeckSubmission:
        tournament = TournamentService(self.db).require(tournament_id)
        if tournament.status != TournamentStatus.ENDED.value:
            raise AppError("TOURNAMENT_NOT_ENDED", "赛事结束后才能上传四强卡组截图", status_code=409)
        item = self.repository.for_user(tournament_id, user_id, for_update=True)
        if item is None:
            raise AppError("NOT_FINAL_FOUR", "只有本届赛事最终四强可以提交卡组截图", status_code=403)
        if item.status == DeckSubmissionStatus.APPROVED.value:
            raise AppError("DECK_SUBMISSION_LOCKED", "卡组截图审核通过后不可替换", status_code=409)
        report = self.db.query(WeeklyReport).filter_by(tournament_id=tournament_id).one_or_none()
        if report is not None and report.status == WeeklyReportStatus.PUBLISHED.value:
            raise AppError("REPORT_PUBLISHED", "周报发布后不可替换卡组截图", status_code=409)
        image_path, _, _, _ = LocalImageStorage().save(content)
        item.image_path = image_path
        item.status = DeckSubmissionStatus.PENDING_REVIEW.value
        item.review_note = None
        item.reviewed_by_id = None
        item.reviewed_at = None
        self.db.commit()
        return self.repository.get(item.id)  # type: ignore[return-value]

    def list_for_admin(self, tournament_id: UUID) -> DeckSubmissionListResponse:
        TournamentService(self.db).require(tournament_id)
        items = self.repository.for_tournament(tournament_id)
        return DeckSubmissionListResponse(
            items=[deck_response(item) for item in items],
            approved_count=sum(item.status == DeckSubmissionStatus.APPROVED.value for item in items),
        )

    def review(self, submission_id: UUID, action: str, reason: str | None, operator_id: UUID) -> DeckSubmission:
        item = self.repository.get(submission_id, for_update=True)
        if item is None:
            raise AppError("DECK_SUBMISSION_NOT_FOUND", "卡组截图提交不存在", status_code=404)
        if item.status != DeckSubmissionStatus.PENDING_REVIEW.value:
            raise AppError("INVALID_DECK_REVIEW_STATE", "只有待审核截图可以执行该操作", status_code=409)
        before = {"status": item.status, "image_path": item.image_path}
        if action == "approve":
            item.status = DeckSubmissionStatus.APPROVED.value
            item.review_note = None
        elif action == "return":
            item.status = DeckSubmissionStatus.REUPLOAD_REQUIRED.value
            item.review_note = (reason or "").strip()
        else:
            raise AppError("INVALID_REVIEW_ACTION", "不支持的卡组审核操作", status_code=404)
        item.reviewed_by_id = operator_id
        item.reviewed_at = datetime.now(UTC)
        add_audit_log(
            self.db,
            operator_id=operator_id,
            tournament_id=item.tournament_id,
            action_type=f"DECK_SUBMISSION_{action.upper()}",
            target_type="deck_submission",
            target_id=item.id,
            before=before,
            after={"status": item.status, "reason": item.review_note},
        )
        self.db.commit()
        return self.repository.get(item.id)  # type: ignore[return-value]
