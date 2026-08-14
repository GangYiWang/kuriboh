from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit.service import add_audit_log
from app.core.errors import AppError
from app.messages.models import MessageType
from app.messages.service import add_automatic_message
from app.registrations.models import Registration, RegistrationStatus
from app.registrations.repository import RegistrationRepository
from app.registrations.schemas import RegistrationResponse
from app.tournaments.models import TournamentStatus
from app.tournaments.repository import TournamentRepository


def registration_response(registration: Registration) -> RegistrationResponse:
    return RegistrationResponse(
        id=registration.id,
        tournament_id=registration.tournament_id,
        user_id=registration.user_id,
        nickname=registration.user.nickname,
        status=RegistrationStatus(registration.status),
        reviewed_by_id=registration.reviewed_by_id,
        reviewed_at=registration.reviewed_at,
        created_at=registration.created_at,
        updated_at=registration.updated_at,
    )


class RegistrationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = RegistrationRepository(db)
        self.tournaments = TournamentRepository(db)

    def apply(self, tournament_id: UUID, user_id: UUID) -> Registration:
        tournament = self._lock_registration_tournament(tournament_id)
        registration = self.repository.for_user(tournament_id, user_id, for_update=True)
        if registration is not None:
            if (
                registration.status == RegistrationStatus.CANCELED.value
                and registration.reviewed_by_id is None
            ):
                self._require_capacity(tournament.id, tournament.max_players)
                registration.status = RegistrationStatus.PENDING.value
                registration.reviewed_at = None
                self.db.commit()
                return self.repository.get(registration.id)  # type: ignore[return-value]
            raise AppError("REGISTRATION_EXISTS", "你已经提交过该赛事报名", status_code=409)
        self._require_capacity(tournament.id, tournament.max_players)
        registration = Registration(
            tournament_id=tournament_id,
            user_id=user_id,
            status=RegistrationStatus.PENDING.value,
        )
        self.db.add(registration)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise AppError("REGISTRATION_EXISTS", "你已经提交过该赛事报名", status_code=409) from exc
        return self.repository.get(registration.id)  # type: ignore[return-value]

    def cancel_by_player(self, tournament_id: UUID, user_id: UUID) -> Registration:
        self._lock_registration_tournament(tournament_id)
        registration = self.repository.for_user(tournament_id, user_id, for_update=True)
        if registration is None:
            raise AppError("REGISTRATION_NOT_FOUND", "尚未报名该赛事", status_code=404)
        if registration.status not in {RegistrationStatus.PENDING.value, RegistrationStatus.APPROVED.value}:
            raise AppError("INVALID_REGISTRATION_STATE", "当前报名状态不可取消", status_code=409)
        registration.status = RegistrationStatus.CANCELED.value
        registration.reviewed_by_id = None
        registration.reviewed_at = datetime.now(UTC)
        self.db.commit()
        return self.repository.get(registration.id)  # type: ignore[return-value]

    def review(self, tournament_id: UUID, registration_id: UUID, action: str, operator_id: UUID) -> Registration:
        tournament = self._lock_registration_tournament(tournament_id)
        registration = self.repository.get(registration_id, for_update=True)
        if registration is None or registration.tournament_id != tournament_id:
            raise AppError("REGISTRATION_NOT_FOUND", "报名记录不存在", status_code=404)
        before_status = registration.status

        if action == "approve":
            self._require_status(registration, RegistrationStatus.PENDING)
            self._require_capacity(tournament.id, tournament.max_players)
            registration.status = RegistrationStatus.APPROVED.value
        elif action == "reject":
            self._require_status(registration, RegistrationStatus.PENDING)
            registration.status = RegistrationStatus.REJECTED.value
        elif action == "cancel":
            if registration.status not in {RegistrationStatus.PENDING.value, RegistrationStatus.APPROVED.value}:
                raise AppError("INVALID_REGISTRATION_STATE", "当前报名状态不可取消", status_code=409)
            registration.status = RegistrationStatus.CANCELED.value
        elif action == "restore":
            if registration.status not in {RegistrationStatus.REJECTED.value, RegistrationStatus.CANCELED.value}:
                raise AppError("INVALID_REGISTRATION_STATE", "当前报名状态不可恢复", status_code=409)
            self._require_capacity(tournament.id, tournament.max_players)
            registration.status = RegistrationStatus.APPROVED.value
        else:
            raise AppError("INVALID_REVIEW_ACTION", "不支持的审核操作")

        registration.reviewed_by_id = operator_id
        registration.reviewed_at = datetime.now(UTC)
        add_audit_log(
            self.db,
            operator_id=operator_id,
            tournament_id=tournament_id,
            action_type=f"REGISTRATION_{action.upper()}",
            target_type="registration",
            target_id=registration.id,
            before={"status": before_status},
            after={"status": registration.status, "user_id": str(registration.user_id)},
        )
        notification = {
            "approve": (MessageType.REGISTRATION_APPROVED, "报名审核通过", f"你报名的“{tournament.name}”已审核通过。"),
            "restore": (MessageType.REGISTRATION_APPROVED, "报名已恢复", f"你在“{tournament.name}”的参赛资格已恢复。"),
            "reject": (MessageType.REGISTRATION_REJECTED, "报名审核未通过", f"你报名的“{tournament.name}”未通过审核。"),
            "cancel": (MessageType.REGISTRATION_CANCELED, "报名已被取消", f"你在“{tournament.name}”的报名已由管理员取消。"),
        }[action]
        add_automatic_message(
            self.db,
            recipient_id=registration.user_id,
            message_type=notification[0],
            title=notification[1],
            body=notification[2],
            action_url=f"/tournaments/{tournament_id}",
            related_type="registration",
            related_id=registration.id,
            dedupe_key=f"registration:{registration.id}:{action}",
        )
        self.db.commit()
        return self.repository.get(registration.id)  # type: ignore[return-value]

    def _lock_registration_tournament(self, tournament_id: UUID):
        tournament = self.tournaments.get(tournament_id, for_update=True)
        if tournament is None:
            raise AppError("TOURNAMENT_NOT_FOUND", "赛事不存在", status_code=404)
        if tournament.status != TournamentStatus.REGISTRATION.value:
            raise AppError("REGISTRATION_CLOSED", "该赛事当前未开放报名", status_code=409)
        return tournament

    def _require_capacity(self, tournament_id: UUID, max_players: int | None) -> None:
        if max_players is None:
            raise AppError("INCOMPLETE_TOURNAMENT", "赛事容量尚未配置", status_code=409)
        approved = self.repository.count_by_status(tournament_id, RegistrationStatus.APPROVED)
        if approved >= max_players:
            raise AppError("TOURNAMENT_FULL", "审核通过人数已达到上限", status_code=409)

    @staticmethod
    def _require_status(registration: Registration, expected: RegistrationStatus) -> None:
        if registration.status != expected.value:
            raise AppError("INVALID_REGISTRATION_STATE", "当前报名状态不允许此操作", status_code=409)
