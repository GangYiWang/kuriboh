"""Create retained Phase 6 message-center and pinned-announcement test data."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.content.models import Announcement  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.db import models as _models  # noqa: E402,F401
from app.db.session import SessionLocal  # noqa: E402
from app.messages.models import Message, MessageType  # noqa: E402
from app.reports.models import WeeklyReport, WeeklyReportStatus  # noqa: E402
from app.tournaments.models import Tournament  # noqa: E402
from app.users.models import User  # noqa: E402

ADMIN_QQ = "40000000"
PLAYER_QQ = "40000001"
PINNED_TITLE = "Phase 6 功能统一测试说明"


def main() -> None:
    settings = get_settings()
    if settings.environment != "development":
        raise RuntimeError("Phase 6 test data can only be seeded in development")
    now = datetime.now(UTC)
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.qq_number == ADMIN_QQ))
        player = db.scalar(select(User).where(User.qq_number == PLAYER_QQ))
        if admin is None or player is None:
            raise RuntimeError("Run the retained Phase 4 test-data seed first")

        announcement = db.scalar(select(Announcement).where(Announcement.title == PINNED_TITLE))
        if announcement is None:
            announcement = Announcement(
                title=PINNED_TITLE,
                content_html=(
                    "<h2>Phase 6 统一测试</h2>"
                    "<p>请依次检查首页当前赛事、我的赛事、消息已读状态，以及管理员通知和操作日志。</p>"
                ),
                is_pinned=True,
                published_at=now,
                author_id=admin.id,
            )
            db.add(announcement)
        else:
            announcement.is_pinned = True

        tournament = db.scalar(select(Tournament).where(Tournament.name == "Phase 4 Top 8 功能测试赛"))
        report = db.scalar(select(WeeklyReport).where(
            WeeklyReport.status == WeeklyReportStatus.PUBLISHED.value
        ).order_by(WeeklyReport.published_at.desc()).limit(1))
        samples = [
            (
                "phase6:sample:registration-approved",
                MessageType.REGISTRATION_APPROVED,
                "报名审核通过（示例）",
                "这是一条已读示例消息，用于检查消息中心的已读样式。",
                f"/tournaments/{tournament.id}" if tournament else "/my-tournaments",
                now - timedelta(minutes=25),
                now - timedelta(minutes=20),
            ),
            (
                "phase6:sample:tournament-notice",
                MessageType.TOURNAMENT_NOTICE,
                "赛事临时通知（示例）",
                "请提前进入比赛页面确认当前对阵和桌号。",
                f"/tournaments/{tournament.id}" if tournament else "/my-tournaments",
                now - timedelta(minutes=12),
                None,
            ),
            (
                "phase6:sample:platform-notice",
                MessageType.PLATFORM_NOTICE,
                "平台通知（示例）",
                "Phase 6 功能已经开放，请完成统一测试。",
                "/messages",
                now - timedelta(minutes=8),
                None,
            ),
        ]
        if report is not None:
            samples.append((
                "phase6:sample:report-published",
                MessageType.REPORT_PUBLISHED,
                "赛事周报已发布（示例）",
                "点击查看已发布且不可撤回的赛事周报。",
                f"/reports/{report.id}",
                now - timedelta(minutes=4),
                None,
            ))
        for key, kind, title, body, action_url, created_at, read_at in samples:
            if db.scalar(select(Message.id).where(Message.dedupe_key == key)) is not None:
                continue
            db.add(Message(
                recipient_id=player.id,
                sender_id=admin.id,
                type=kind.value,
                title=title,
                body=body,
                action_url=action_url,
                related_type="phase6_sample",
                dedupe_key=key,
                read_at=read_at,
                created_at=created_at,
                updated_at=created_at,
            ))
        db.commit()
    print("Phase 6 retained test data is ready for QQ 40000001.")


if __name__ == "__main__":
    main()
