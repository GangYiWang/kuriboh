from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit.service import add_audit_log
from app.content.models import Announcement, BanlistVersion
from app.content.repository import AnnouncementRepository, BanlistRepository
from app.content.sanitizer import sanitize_rich_text
from app.core.errors import AppError


class BanlistService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = BanlistRepository(db)

    @staticmethod
    def next_version(latest: BanlistVersion | None) -> tuple[int, int]:
        if latest is None:
            return 1, 0
        if latest.minor_version >= 9:
            return latest.major_version + 1, 0
        return latest.major_version, latest.minor_version + 1

    def publish(self, *, title: str, content_html: str, user_id: UUID) -> BanlistVersion:
        clean_content = sanitize_rich_text(content_html)
        if not clean_content:
            raise AppError("EMPTY_CONTENT", "禁卡表内容不能为空")
        latest = self.repository.latest(for_update=True)
        major, minor = self.next_version(latest)
        item = BanlistVersion(
            major_version=major,
            minor_version=minor,
            title=title.strip(),
            content_html=clean_content,
            published_at=datetime.now(UTC),
            created_by_id=user_id,
        )
        self.db.add(item)
        try:
            self.db.flush()
            add_audit_log(
                self.db,
                operator_id=user_id,
                action_type="BANLIST_PUBLISHED",
                target_type="banlist_version",
                target_id=item.id,
                after={"version": item.version, "title": item.title},
            )
            self.db.commit()
            self.db.refresh(item)
        except IntegrityError as exc:
            self.db.rollback()
            raise AppError("VERSION_CONFLICT", "版本生成冲突，请重试", status_code=409) from exc
        return item


class AnnouncementService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = AnnouncementRepository(db)

    def publish(self, *, title: str, content_html: str, is_pinned: bool, user_id: UUID) -> Announcement:
        clean_content = sanitize_rich_text(content_html)
        if not clean_content:
            raise AppError("EMPTY_CONTENT", "公告内容不能为空")
        item = Announcement(
            title=title.strip(),
            content_html=clean_content,
            is_pinned=is_pinned,
            published_at=datetime.now(UTC),
            author_id=user_id,
        )
        self.db.add(item)
        self.db.flush()
        add_audit_log(
            self.db,
            operator_id=user_id,
            action_type="ANNOUNCEMENT_PUBLISHED",
            target_type="announcement",
            target_id=item.id,
            after={"title": item.title, "is_pinned": item.is_pinned},
        )
        self.db.commit()
        self.db.refresh(item)
        return item

    def update(
        self,
        item: Announcement,
        *,
        title: str | None,
        content_html: str | None,
        is_pinned: bool | None,
        operator_id: UUID,
    ) -> Announcement:
        before = {"title": item.title, "is_pinned": item.is_pinned}
        if title is not None:
            item.title = title.strip()
        if content_html is not None:
            item.content_html = sanitize_rich_text(content_html)
        if is_pinned is not None:
            item.is_pinned = is_pinned
        add_audit_log(
            self.db,
            operator_id=operator_id,
            action_type="ANNOUNCEMENT_UPDATED",
            target_type="announcement",
            target_id=item.id,
            before=before,
            after={"title": item.title, "is_pinned": item.is_pinned},
        )
        self.db.commit()
        self.db.refresh(item)
        return item
