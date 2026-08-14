from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit.service import add_audit_log
from app.core.errors import AppError
from app.messages.models import Message, MessageType
from app.messages.repository import MessageRepository
from app.messages.schemas import MessageListResponse, MessageResponse, MessageSendResponse
from app.registrations.models import TournamentParticipant
from app.tournaments.service import TournamentService
from app.users.models import User


class MessageService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = MessageRepository(db)

    def list_for_user(self, user_id: UUID, *, offset: int, limit: int) -> MessageListResponse:
        items, total = self.repository.list_for_recipient(user_id, offset=offset, limit=limit)
        return MessageListResponse(
            items=[MessageResponse.model_validate(item) for item in items],
            total=total,
            unread_count=self.repository.unread_count(user_id),
        )

    def mark_read(self, message_id: UUID, user_id: UUID) -> Message:
        item = self.repository.get_for_recipient(message_id, user_id, for_update=True)
        if item is None:
            raise AppError("MESSAGE_NOT_FOUND", "消息不存在", status_code=404)
        if item.read_at is None:
            item.read_at = datetime.now(UTC)
            self.db.commit()
        return item

    def mark_all_read(self, user_id: UUID) -> int:
        result = self.db.execute(update(Message).where(
            Message.recipient_id == user_id,
            Message.read_at.is_(None),
        ).values(read_at=datetime.now(UTC)))
        self.db.commit()
        return int(result.rowcount or 0)

    def send_tournament_notice(
        self, tournament_id: UUID, *, title: str, body: str, request_id: UUID, operator_id: UUID,
    ) -> MessageSendResponse:
        tournament = TournamentService(self.db).require(tournament_id, for_update=True)
        recipient_ids = list(self.db.scalars(select(TournamentParticipant.user_id).where(
            TournamentParticipant.tournament_id == tournament_id,
        ).order_by(TournamentParticipant.user_id)))
        if not recipient_ids:
            raise AppError("NO_TOURNAMENT_PARTICIPANTS", "赛事尚无正式参赛玩家", status_code=409)
        return self._send_batch(
            recipient_ids=recipient_ids,
            message_type=MessageType.TOURNAMENT_NOTICE,
            title=title,
            body=body,
            request_id=request_id,
            sender_id=operator_id,
            action_url=f"/tournaments/{tournament_id}",
            related_type="tournament",
            related_id=str(tournament_id),
            audit_action="TOURNAMENT_NOTICE_SENT",
            audit_target_id=tournament_id,
            tournament_id=tournament.id,
        )

    def send_platform_notice(
        self, *, title: str, body: str, request_id: UUID, operator_id: UUID,
    ) -> MessageSendResponse:
        recipient_ids = list(self.db.scalars(select(User.id).order_by(User.id)))
        return self._send_batch(
            recipient_ids=recipient_ids,
            message_type=MessageType.PLATFORM_NOTICE,
            title=title,
            body=body,
            request_id=request_id,
            sender_id=operator_id,
            action_url="/messages",
            related_type="platform",
            related_id=None,
            audit_action="PLATFORM_NOTICE_SENT",
            audit_target_id=request_id,
            tournament_id=None,
        )

    def _send_batch(
        self,
        *,
        recipient_ids: list[UUID],
        message_type: MessageType,
        title: str,
        body: str,
        request_id: UUID,
        sender_id: UUID,
        action_url: str,
        related_type: str,
        related_id: str | None,
        audit_action: str,
        audit_target_id: UUID,
        tournament_id: UUID | None,
    ) -> MessageSendResponse:
        clean_title = title.strip()
        clean_body = body.strip()
        first_key = f"manual:{request_id}:{recipient_ids[0]}" if recipient_ids else f"manual:{request_id}:empty"
        if self.repository.has_dedupe_key(first_key):
            return MessageSendResponse(sent_count=len(recipient_ids), duplicated=True)
        for recipient_id in recipient_ids:
            created_at = datetime.now(UTC)
            self.db.add(Message(
                recipient_id=recipient_id,
                sender_id=sender_id,
                type=message_type.value,
                title=clean_title,
                body=clean_body,
                action_url=action_url,
                related_type=related_type,
                related_id=related_id,
                dedupe_key=f"manual:{request_id}:{recipient_id}",
                created_at=created_at,
                updated_at=created_at,
            ))
        add_audit_log(
            self.db,
            operator_id=sender_id,
            tournament_id=tournament_id,
            action_type=audit_action,
            target_type="message_batch",
            target_id=audit_target_id,
            after={"title": clean_title, "recipient_count": len(recipient_ids)},
        )
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            if self.repository.has_dedupe_key(first_key):
                return MessageSendResponse(sent_count=len(recipient_ids), duplicated=True)
            raise
        return MessageSendResponse(sent_count=len(recipient_ids))


def add_automatic_message(
    db: Session,
    *,
    recipient_id: UUID,
    message_type: MessageType,
    title: str,
    body: str,
    action_url: str,
    related_type: str,
    related_id: UUID,
    dedupe_key: str,
) -> None:
    if MessageRepository(db).has_dedupe_key(dedupe_key):
        return
    db.add(Message(
        recipient_id=recipient_id,
        type=message_type.value,
        title=title,
        body=body,
        action_url=action_url,
        related_type=related_type,
        related_id=str(related_id),
        dedupe_key=dedupe_key,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    ))
