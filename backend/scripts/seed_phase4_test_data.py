"""Create retained local Phase 4 test accounts and a published Top 8 bracket."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth.roles import Role  # noqa: E402
from app.auth.security import hash_password  # noqa: E402
from app.content.models import BanlistVersion  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.db import models as _models  # noqa: E402,F401
from app.db.session import SessionLocal  # noqa: E402
from app.playoffs.service import PlayoffService  # noqa: E402
from app.registrations.models import Registration, RegistrationStatus, TournamentParticipant  # noqa: E402
from app.swiss.models import RankingSnapshot, SwissRound, SwissRoundStatus  # noqa: E402
from app.tournaments.models import Tournament, TournamentStatus  # noqa: E402
from app.users.models import User  # noqa: E402

ADMIN_QQ = "40000000"
PLAYER_QQS = [f"4000000{index}" for index in range(1, 9)]
PASSWORD = "12345678"
TOURNAMENT_NAME = "Phase 4 Top 8 功能测试赛"


def main() -> None:
    if get_settings().environment != "development":
        raise RuntimeError("仅允许在 development 环境创建测试数据")

    with SessionLocal() as db:
        existing = db.scalar(select(Tournament).where(Tournament.name == TOURNAMENT_NAME))
        if existing is not None:
            print(f"existing_tournament_id={existing.id}")
            print("test data already exists; nothing changed")
            return

        if db.scalar(select(User).where(User.qq_number.in_([ADMIN_QQ, *PLAYER_QQS]))) is not None:
            raise RuntimeError("Phase 4 测试 QQ 号已被部分占用，请人工检查后重试")

        admin = User(
            qq_number=ADMIN_QQ,
            nickname="Phase4测试管理员",
            password_hash=hash_password(PASSWORD),
            role=Role.TOURNAMENT_ADMIN.value,
        )
        players = [
            User(
                qq_number=qq,
                nickname=f"Phase4测试选手{index:02d}",
                password_hash=hash_password(PASSWORD),
                role=Role.PLAYER.value,
            )
            for index, qq in enumerate(PLAYER_QQS, start=1)
        ]
        db.add_all([admin, *players])
        db.flush()

        banlist = db.scalar(
            select(BanlistVersion).order_by(
                BanlistVersion.major_version.desc(), BanlistVersion.minor_version.desc()
            ).limit(1)
        )
        if banlist is None:
            banlist = BanlistVersion(
                major_version=1,
                minor_version=0,
                title="Phase 4 测试禁卡表",
                content_html="<p>Phase 4 开发测试数据专用禁卡表。</p>",
                published_at=datetime.now(UTC),
                created_by_id=admin.id,
            )
            db.add(banlist)
            db.flush()

        tournament = Tournament(
            name=TOURNAMENT_NAME,
            description="保留给本地开发验收的 Top 8 固定种子淘汰赛；八强已经发布，等待双方提交赛果或管理员判负。",
            planned_start_at=datetime.now(UTC) + timedelta(days=7),
            max_players=8,
            swiss_rounds=1,
            playoff_size=8,
            banlist_version_id=banlist.id,
            status=TournamentStatus.SWISS.value,
            published_at=datetime.now(UTC),
            started_at=datetime.now(UTC),
            created_by_id=admin.id,
        )
        db.add(tournament)
        db.flush()

        participants: list[TournamentParticipant] = []
        for player in players:
            registration = Registration(
                tournament_id=tournament.id,
                user_id=player.id,
                status=RegistrationStatus.APPROVED.value,
                reviewed_by_id=admin.id,
                reviewed_at=datetime.now(UTC),
            )
            db.add(registration)
            db.flush()
            participant = TournamentParticipant(
                tournament_id=tournament.id,
                user_id=player.id,
                registration_id=registration.id,
                nickname_snapshot=player.nickname,
            )
            db.add(participant)
            db.flush()
            participants.append(participant)

        swiss_round = SwissRound(
            tournament_id=tournament.id,
            round_no=1,
            status=SwissRoundStatus.COMPLETED.value,
            published_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        db.add(swiss_round)
        db.flush()
        for rank, participant in enumerate(participants, start=1):
            db.add(RankingSnapshot(
                tournament_id=tournament.id,
                swiss_round_id=swiss_round.id,
                participant_id=participant.id,
                rank=rank,
                wins=8 - rank,
                losses=rank - 1,
                omw=(8 - rank) / 8,
                loss_round_score=rank - 1,
            ))
        db.commit()

        service = PlayoffService(db)
        preview = service.generate_preview(tournament.id, admin.id)
        published = service.publish_round(tournament.id, preview.id, admin.id)

        print(f"tournament_id={tournament.id}")
        print(f"admin={ADMIN_QQ}/{PASSWORD}")
        print(f"players={PLAYER_QQS[0]}-{PLAYER_QQS[-1]}/{PASSWORD}")
        print(f"playoff_round={published.name} {published.status}")


if __name__ == "__main__":
    main()
