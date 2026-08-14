from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.messages.models import Message


class MessageRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_for_recipient(self, message_id: UUID, recipient_id: UUID, *, for_update: bool = False) -> Message | None:
        statement = select(Message).where(Message.id == message_id, Message.recipient_id == recipient_id)
        if for_update:
            statement = statement.with_for_update()
        return self.db.scalar(statement)

    def list_for_recipient(self, recipient_id: UUID, *, offset: int, limit: int) -> tuple[list[Message], int]:
        filters = [Message.recipient_id == recipient_id]
        items = list(self.db.scalars(
            select(Message).where(*filters).order_by(Message.created_at.desc()).offset(offset).limit(limit)
        ))
        total = self.db.scalar(select(func.count()).select_from(Message).where(*filters)) or 0
        return items, int(total)

    def unread_count(self, recipient_id: UUID) -> int:
        return int(self.db.scalar(select(func.count()).select_from(Message).where(
            Message.recipient_id == recipient_id,
            Message.read_at.is_(None),
        )) or 0)

    def has_dedupe_key(self, dedupe_key: str) -> bool:
        return self.db.scalar(select(Message.id).where(Message.dedupe_key == dedupe_key).limit(1)) is not None
