from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.deck_submissions.models import DeckSubmission
from app.matches.models import Match
from app.reports.models import WeeklyReport
from app.tournaments.service import TournamentService


def require_tournament_owner(db: Session, tournament_id: UUID, user_id: UUID) -> None:
    TournamentService(db).require_owner(tournament_id, user_id)


def require_match_owner(db: Session, match_id: UUID, user_id: UUID) -> None:
    match = db.get(Match, match_id)
    if match is None:
        raise AppError("MATCH_NOT_FOUND", "对局不存在", status_code=404)
    require_tournament_owner(db, match.tournament_id, user_id)


def require_deck_submission_owner(db: Session, submission_id: UUID, user_id: UUID) -> None:
    submission = db.get(DeckSubmission, submission_id)
    if submission is None:
        raise AppError("DECK_SUBMISSION_NOT_FOUND", "卡组提交不存在", status_code=404)
    require_tournament_owner(db, submission.tournament_id, user_id)


def require_report_owner(db: Session, report_id: UUID, user_id: UUID) -> None:
    report = db.get(WeeklyReport, report_id)
    if report is None:
        raise AppError("REPORT_NOT_FOUND", "周报不存在", status_code=404)
    require_tournament_owner(db, report.tournament_id, user_id)
