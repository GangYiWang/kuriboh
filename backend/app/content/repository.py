from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.content.models import Announcement, BanlistVersion


class BanlistRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def latest(self, *, for_update: bool = False) -> BanlistVersion | None:
        statement = select(BanlistVersion).order_by(
            BanlistVersion.major_version.desc(),
            BanlistVersion.minor_version.desc(),
        ).limit(1)
        if for_update:
            statement = statement.with_for_update()
        return self.db.scalar(statement)

    def get(self, item_id: UUID) -> BanlistVersion | None:
        return self.db.get(BanlistVersion, item_id)

    def list(self, offset: int, limit: int) -> tuple[list[BanlistVersion], int]:
        items = list(self.db.scalars(
            select(BanlistVersion)
            .order_by(BanlistVersion.published_at.desc())
            .offset(offset)
            .limit(limit)
        ))
        total = self.db.scalar(select(func.count()).select_from(BanlistVersion)) or 0
        return items, total


class AnnouncementRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, item_id: UUID) -> Announcement | None:
        return self.db.get(Announcement, item_id)

    def list(self, offset: int, limit: int) -> tuple[list[Announcement], int]:
        items = list(self.db.scalars(
            select(Announcement)
            .order_by(Announcement.is_pinned.desc(), Announcement.published_at.desc())
            .offset(offset)
            .limit(limit)
        ))
        total = self.db.scalar(select(func.count()).select_from(Announcement)) or 0
        return items, total
