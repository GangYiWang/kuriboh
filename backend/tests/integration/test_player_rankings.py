from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.auth.roles import Role
from app.statistics.models import PlayerStatistics


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def add_statistics(
    session_factory: sessionmaker[Session],
    user_id: UUID,
    *,
    points: int,
    champions: int,
    runner_ups: int = 0,
    top_4: int = 0,
    top_8: int = 0,
    wins: int = 0,
    losses: int = 0,
    byes: int = 0,
    tournaments: int = 0,
) -> None:
    with session_factory() as db:
        db.add(PlayerStatistics(
            user_id=user_id,
            tournament_count=tournaments,
            total_points=points,
            champion_count=champions,
            runner_up_count=runner_ups,
            top_4_count=top_4,
            top_8_count=top_8,
            total_wins=wins,
            total_losses=losses,
            total_byes=byes,
        ))
        db.commit()


def test_player_rankings_require_platform_admin(client: TestClient, make_user) -> None:
    _, user_token = make_user(qq_number="ranking-user", nickname="普通用户")

    unauthenticated = client.get("/api/admin/player-rankings")
    forbidden = client.get("/api/admin/player-rankings", headers=auth(user_token))

    assert unauthenticated.status_code == 401
    assert forbidden.status_code == 403


def test_player_rankings_include_all_users_and_keep_global_rank_when_searching(
    client: TestClient,
    make_user,
    session_factory: sessionmaker[Session],
) -> None:
    _, admin_token = make_user(
        qq_number="ranking-admin",
        nickname="平台管理员",
        role=Role.PLATFORM_ADMIN,
    )
    leader, _ = make_user(qq_number="ranking-leader", nickname="积分领先者")
    champion, _ = make_user(qq_number="ranking-champion", nickname="Flask")
    make_user(qq_number="ranking-zero", nickname="零积分玩家")
    add_statistics(
        session_factory,
        leader.id,
        points=8,
        champions=0,
        top_4=1,
        top_8=1,
        wins=10,
        losses=2,
        tournaments=2,
    )
    add_statistics(
        session_factory,
        champion.id,
        points=3,
        champions=1,
        top_4=1,
        top_8=1,
        wins=4,
        losses=1,
        byes=1,
        tournaments=1,
    )

    response = client.get(
        "/api/admin/player-rankings?offset=0&limit=20",
        headers=auth(admin_token),
    )

    assert response.status_code == 200, response.json()
    body = response.json()
    assert body["total"] == 4
    assert [item["nickname"] for item in body["items"][:2]] == ["积分领先者", "Flask"]
    assert [item["rank"] for item in body["items"]] == [1, 2, 3, 4]
    flask = body["items"][1]
    assert flask["champion_count"] == 1
    assert flask["total_points"] == 3
    assert flask["win_rate"] == 0.8
    zero = next(item for item in body["items"] if item["nickname"] == "零积分玩家")
    assert zero["total_points"] == 0
    assert zero["tournament_count"] == 0

    second_page = client.get(
        "/api/admin/player-rankings?offset=1&limit=1",
        headers=auth(admin_token),
    )
    assert second_page.status_code == 200
    assert second_page.json()["items"][0]["nickname"] == "Flask"
    assert second_page.json()["items"][0]["rank"] == 2

    searched = client.get(
        "/api/admin/player-rankings?search=Flask",
        headers=auth(admin_token),
    )
    assert searched.status_code == 200
    assert searched.json()["total"] == 1
    assert searched.json()["items"][0]["rank"] == 2


def test_player_rankings_use_achievement_tiebreakers(
    client: TestClient,
    make_user,
    session_factory: sessionmaker[Session],
) -> None:
    _, admin_token = make_user(
        qq_number="ranking-tie-admin",
        nickname="排名管理员",
        role=Role.PLATFORM_ADMIN,
    )
    runner_up, _ = make_user(qq_number="ranking-tie-a", nickname="亚军玩家")
    champion, _ = make_user(qq_number="ranking-tie-b", nickname="冠军玩家")
    add_statistics(session_factory, runner_up.id, points=4, champions=0, runner_ups=1)
    add_statistics(session_factory, champion.id, points=4, champions=1)

    response = client.get("/api/admin/player-rankings", headers=auth(admin_token))

    assert response.status_code == 200
    assert [item["nickname"] for item in response.json()["items"][:2]] == ["冠军玩家", "亚军玩家"]


def test_player_rankings_use_win_rate_instead_of_total_wins(
    client: TestClient,
    make_user,
    session_factory: sessionmaker[Session],
) -> None:
    _, admin_token = make_user(
        qq_number="ranking-rate-admin",
        nickname="胜率排名管理员",
        role=Role.PLATFORM_ADMIN,
    )
    high_rate, _ = make_user(qq_number="ranking-rate-a", nickname="Zulu高胜率")
    more_wins, _ = make_user(qq_number="ranking-rate-b", nickname="Alpha多胜场")
    add_statistics(
        session_factory,
        high_rate.id,
        points=2,
        champions=0,
        top_4=1,
        top_8=1,
        wins=4,
        losses=1,
    )
    add_statistics(
        session_factory,
        more_wins.id,
        points=2,
        champions=0,
        top_4=1,
        top_8=1,
        wins=10,
        losses=5,
    )

    response = client.get("/api/admin/player-rankings", headers=auth(admin_token))

    assert response.status_code == 200
    assert [item["nickname"] for item in response.json()["items"][:2]] == [
        "Zulu高胜率",
        "Alpha多胜场",
    ]
