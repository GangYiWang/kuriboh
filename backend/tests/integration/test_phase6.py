from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.auth.roles import Role
from app.content.models import BanlistVersion


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def setup_started_tournament(client, make_user, session_factory):
    admin, admin_token = make_user(
        qq_number="96000000", nickname="Phase6管理员", role=Role.USER
    )
    _, token_a = make_user(qq_number="96000001", nickname="Phase6选手甲")
    _, token_b = make_user(qq_number="96000002", nickname="Phase6选手乙")
    with session_factory() as db:
        banlist = BanlistVersion(
            major_version=1,
            minor_version=0,
            title="Phase 6 禁卡表",
            content_html="<p>测试</p>",
            published_at=datetime.now(UTC),
            created_by_id=admin.id,
        )
        db.add(banlist)
        db.commit()
        db.refresh(banlist)
        banlist_id = banlist.id
    created = client.post("/api/admin/tournaments", headers=auth(admin_token), json={
        "name": "Phase 6 完整功能测试赛",
        "description": "消息、我的赛事与审计验收",
        "planned_start_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        "max_players": 2,
        "swiss_rounds": 1,
        "playoff_size": 2,
        "banlist_version_id": str(banlist_id),
    })
    tournament_id = created.json()["id"]
    client.post(f"/api/admin/tournaments/{tournament_id}/publish", headers=auth(admin_token))
    registrations = []
    for token in (token_a, token_b):
        registration = client.post(
            f"/api/tournaments/{tournament_id}/registrations",
            headers=auth(token),
            json={"nickname_matches_game": True, "accepts_rules": True},
        ).json()
        registrations.append(registration)
        approved = client.post(
            f"/api/admin/tournaments/{tournament_id}/registrations/{registration['id']}/approve",
            headers=auth(admin_token),
        )
        assert approved.status_code == 200, approved.json()
    started = client.post(f"/api/admin/tournaments/{tournament_id}/start", headers=auth(admin_token))
    assert started.status_code == 200, started.json()
    return tournament_id, admin_token, token_a, token_b


def test_phase6_messages_my_tournaments_audit_and_deduplication(client, make_user, session_factory) -> None:
    tournament_id, admin_token, token_a, _ = setup_started_tournament(client, make_user, session_factory)

    initial = client.get("/api/messages", headers=auth(token_a))
    assert initial.status_code == 200
    assert initial.json()["unread_count"] == 1
    assert initial.json()["items"][0]["type"] == "REGISTRATION_APPROVED"

    my_tournaments = client.get("/api/me/tournaments", headers=auth(token_a))
    assert my_tournaments.status_code == 200
    assert my_tournaments.json()["total"] == 1
    assert my_tournaments.json()["items"][0]["status"] == "SWISS"
    assert my_tournaments.json()["items"][0]["registration_status"] == "APPROVED"

    request_id = str(uuid4())
    payload = {"title": "临时场地通知", "body": "请在比赛开始前进入指定房间。", "request_id": request_id}
    sent = client.post(
        f"/api/admin/tournaments/{tournament_id}/messages",
        headers=auth(admin_token),
        json=payload,
    )
    duplicate = client.post(
        f"/api/admin/tournaments/{tournament_id}/messages",
        headers=auth(admin_token),
        json=payload,
    )
    assert sent.json() == {"sent_count": 2, "duplicated": False}
    assert duplicate.json() == {"sent_count": 2, "duplicated": True}

    messages = client.get("/api/messages", headers=auth(token_a)).json()
    assert messages["unread_count"] == 2
    assert [item["type"] for item in messages["items"]] == ["TOURNAMENT_NOTICE", "REGISTRATION_APPROVED"]
    read = client.post(f"/api/messages/{messages['items'][0]['id']}/read", headers=auth(token_a))
    assert read.json()["read_at"] is not None
    all_read = client.post("/api/messages/read-all", headers=auth(token_a))
    assert all_read.json()["unread_count"] == 0

    generated = client.post(
        f"/api/admin/tournaments/{tournament_id}/swiss/rounds/generate",
        headers=auth(admin_token),
        json={"seed": 6},
    )
    client.post(
        f"/api/admin/tournaments/{tournament_id}/swiss/rounds/{generated.json()['id']}/publish",
        headers=auth(admin_token),
    )
    assert client.get("/api/messages", headers=auth(token_a)).json()["total"] == 2

    audit = client.get(
        f"/api/tournaments/{tournament_id}/audit-logs?limit=100",
        headers=auth(admin_token),
    )
    assert audit.status_code == 200
    actions = {item["action_type"] for item in audit.json()["items"]}
    assert {"TOURNAMENT_PUBLISHED", "TOURNAMENT_STARTED", "REGISTRATION_APPROVE", "TOURNAMENT_NOTICE_SENT", "SWISS_ROUND_PUBLISHED"} <= actions

    assert client.get("/api/admin/audit-logs", headers=auth(token_a)).status_code == 403
    assert client.post(
        f"/api/admin/tournaments/{tournament_id}/messages", headers=auth(token_a), json=payload
    ).status_code == 403


def test_platform_notice_targets_registered_accounts(client, make_user) -> None:
    _, admin_token = make_user(
        qq_number="96000100", nickname="平台通知管理员", role=Role.PLATFORM_ADMIN
    )
    _, player_token = make_user(qq_number="96000101", nickname="平台通知选手")
    response = client.post("/api/admin/messages/platform", headers=auth(admin_token), json={
        "title": "平台维护通知",
        "body": "今晚进行短时维护。",
        "request_id": str(uuid4()),
    })
    assert response.status_code == 200
    assert response.json()["sent_count"] == 2
    player_messages = client.get("/api/messages", headers=auth(player_token)).json()
    assert player_messages["items"][0]["type"] == "PLATFORM_NOTICE"
