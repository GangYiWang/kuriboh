"""Create retained Phase 5 deck-review and published-report test scenarios."""

from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
import sys

from PIL import Image
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.content.models import BanlistVersion  # noqa: E402
from app.content.storage import LocalImageStorage  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.db import models as _models  # noqa: E402,F401
from app.db.session import SessionLocal  # noqa: E402
from app.deck_submissions.models import DeckSubmissionStatus  # noqa: E402
from app.deck_submissions.repository import DeckSubmissionRepository  # noqa: E402
from app.deck_submissions.service import DeckSubmissionService  # noqa: E402
from app.matches.models import Match, MatchStage, MatchStatus, ResultSource  # noqa: E402
from app.playoffs.models import PlayoffRound, PlayoffRoundStatus  # noqa: E402
from app.registrations.models import Registration, RegistrationStatus, TournamentParticipant  # noqa: E402
from app.reports.repository import WeeklyReportRepository  # noqa: E402
from app.reports.service import WeeklyReportService  # noqa: E402
from app.swiss.models import RankingSnapshot, SwissRound, SwissRoundStatus  # noqa: E402
from app.tournaments.models import Tournament, TournamentStatus  # noqa: E402
from app.tournaments.service import TournamentService  # noqa: E402
from app.users.models import User  # noqa: E402

ADMIN_QQ = "40000000"
PLAYER_QQS = [f"4000000{index}" for index in range(1, 9)]
PASSWORD = "12345678"
REVIEW_TOURNAMENT = "Phase 5 卡组审核测试赛"
PUBLISHED_TOURNAMENT = "Phase 5 已发布周报示例赛"


def create_completed_tournament(db, name: str, admin: User, players: list[User], banlist: BanlistVersion) -> Tournament:
    existing = db.scalar(select(Tournament).where(Tournament.name == name))
    if existing is not None:
        return existing
    now = datetime.now(UTC)
    tournament = Tournament(
        name=name,
        description="保留用于 Phase 5 本地验收：赛事已结束，最终四强与所有赛果均已锁定。",
        planned_start_at=now - timedelta(days=2),
        max_players=8,
        swiss_rounds=1,
        playoff_size=8,
        banlist_version_id=banlist.id,
        status=TournamentStatus.ELIMINATION.value,
        published_at=now - timedelta(days=3),
        started_at=now - timedelta(days=2),
        created_by_id=admin.id,
    )
    db.add(tournament)
    db.flush()
    participants = []
    for player in players:
        registration = Registration(
            tournament_id=tournament.id,
            user_id=player.id,
            status=RegistrationStatus.APPROVED.value,
            reviewed_by_id=admin.id,
            reviewed_at=now - timedelta(days=3),
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
        published_at=now - timedelta(days=2),
        completed_at=now - timedelta(days=2),
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

    stages = [
        (1, 8, "八强", [(0, 7, 1, 8), (3, 4, 4, 5), (1, 6, 2, 7), (2, 5, 3, 6)]),
        (2, 4, "半决赛", [(0, 3, 1, 4), (1, 2, 2, 3)]),
        (3, 2, "决赛", [(0, 1, 1, 2)]),
    ]
    for stage_no, bracket_size, stage_name, pairings in stages:
        round_item = PlayoffRound(
            tournament_id=tournament.id,
            stage_no=stage_no,
            bracket_size=bracket_size,
            name=stage_name,
            status=PlayoffRoundStatus.COMPLETED.value,
            published_at=now - timedelta(days=2) + timedelta(hours=stage_no),
            completed_at=now - timedelta(days=2) + timedelta(hours=stage_no + 1),
        )
        db.add(round_item)
        db.flush()
        for table_no, (a_index, b_index, seed_a, seed_b) in enumerate(pairings, start=1):
            db.add(Match(
                tournament_id=tournament.id,
                playoff_round_id=round_item.id,
                stage=MatchStage.ELIMINATION.value,
                round_no=stage_no,
                table_no=table_no,
                seed_a=seed_a,
                seed_b=seed_b,
                player_a_id=participants[a_index].id,
                player_b_id=participants[b_index].id,
                winner_id=participants[a_index].id,
                status=MatchStatus.COMPLETED.value,
                result_source=ResultSource.ADMIN.value,
            ))
    db.commit()
    return TournamentService(db).end(tournament.id, admin.id)


def sample_image(color: tuple[int, int, int]) -> bytes:
    output = BytesIO()
    Image.new("RGB", (960, 540), color=color).save(output, format="PNG")
    return output.getvalue()


def main() -> None:
    if get_settings().environment != "development":
        raise RuntimeError("仅允许在 development 环境创建测试数据")
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.qq_number == ADMIN_QQ))
        players = list(db.scalars(select(User).where(User.qq_number.in_(PLAYER_QQS)).order_by(User.qq_number)))
        if admin is None or len(players) != 8:
            raise RuntimeError("请先运行 seed_phase4_test_data.py 创建 40000000～40000008 测试账号")
        banlist = db.scalar(select(BanlistVersion).order_by(
            BanlistVersion.major_version.desc(), BanlistVersion.minor_version.desc()
        ).limit(1))
        if banlist is None:
            raise RuntimeError("至少需要一个已发布禁卡表版本")

        review_tournament = create_completed_tournament(db, REVIEW_TOURNAMENT, admin, players, banlist)
        published_tournament = create_completed_tournament(db, PUBLISHED_TOURNAMENT, admin, players, banlist)
        report = WeeklyReportRepository(db).for_tournament(published_tournament.id)
        if report is None:
            colors = [(141, 61, 45), (52, 91, 112), (83, 112, 73), (128, 89, 121)]
            decks = DeckSubmissionRepository(db).for_tournament(published_tournament.id)
            for item, color in zip(decks, colors, strict=True):
                image_path, _, _, _ = LocalImageStorage().save(sample_image(color))
                item.image_path = image_path
                item.status = DeckSubmissionStatus.PENDING_REVIEW.value
            db.commit()
            deck_service = DeckSubmissionService(db)
            for item in DeckSubmissionRepository(db).for_tournament(published_tournament.id):
                deck_service.review(item.id, "approve", None, admin.id)
            report_service = WeeklyReportService(db)
            report = report_service.generate(published_tournament.id, admin.id)
            report = report_service.publish(report.id, admin.id)

        print(f"review_tournament_id={review_tournament.id}")
        print(f"published_report_tournament_id={published_tournament.id}")
        print(f"published_report_id={report.id}")
        print(f"admin={ADMIN_QQ}/{PASSWORD}")
        print(f"players={PLAYER_QQS[0]}-{PLAYER_QQS[-1]}/{PASSWORD}")


if __name__ == "__main__":
    main()
