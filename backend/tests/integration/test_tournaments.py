from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select

from app.auth.roles import Role
from app.audit.models import AuditLog
from app.content.models import BanlistVersion
from app.registrations.models import Registration, RegistrationStatus, TournamentParticipant
from app.tournaments.models import Tournament, TournamentStatus


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def seed_banlist(session_factory, admin_id):
    with session_factory() as db:
        item = BanlistVersion(
            major_version=1,
            minor_version=0,
            title="Phase 2 测试禁卡表",
            content_html="<p>测试</p>",
            published_at=datetime.now(UTC),
            created_by_id=admin_id,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item.id


def tournament_payload(banlist_id, **overrides):
    payload = {
        "name": "栗子杯 Phase 2 测试赛",
        "description": "报名与开赛规则验收",
        "planned_start_at": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
        "max_players": 2,
        "swiss_rounds": 3,
        "playoff_size": 2,
        "banlist_version_id": str(banlist_id),
    }
    payload.update(overrides)
    return payload


def create_and_publish(client, admin_token, banlist_id, **overrides):
    created = client.post(
        "/api/admin/tournaments",
        headers=auth(admin_token),
        json=tournament_payload(banlist_id, **overrides),
    )
    assert created.status_code == 201, created.json()
    tournament_id = created.json()["id"]
    published = client.post(f"/api/admin/tournaments/{tournament_id}/publish", headers=auth(admin_token))
    assert published.status_code == 200, published.json()
    return tournament_id


def test_draft_is_private_and_publish_opens_registration(client, make_user, session_factory) -> None:
    admin, admin_token = make_user(
        qq_number="80000001", nickname="赛事管理员", role=Role.USER
    )
    banlist_id = seed_banlist(session_factory, admin.id)
    created = client.post(
        "/api/admin/tournaments",
        headers=auth(admin_token),
        json=tournament_payload(banlist_id),
    )
    tournament_id = created.json()["id"]

    assert created.status_code == 201
    assert created.json()["status"] == "DRAFT"
    assert client.get("/api/tournaments").json()["total"] == 0
    assert client.get(f"/api/tournaments/{tournament_id}").status_code == 404

    published = client.post(f"/api/admin/tournaments/{tournament_id}/publish", headers=auth(admin_token))
    assert published.status_code == 200
    assert published.json()["status"] == "REGISTRATION"
    assert client.get("/api/tournaments").json()["total"] == 1


def test_draft_can_be_incomplete_but_publish_requires_core_fields(client, make_user) -> None:
    _, admin_token = make_user(
        qq_number="80000002", nickname="草稿管理员", role=Role.USER
    )
    created = client.post(
        "/api/admin/tournaments",
        headers=auth(admin_token),
        json={"name": "尚未配置完成的赛事"},
    )
    published = client.post(
        f"/api/admin/tournaments/{created.json()['id']}/publish",
        headers=auth(admin_token),
    )

    assert created.status_code == 201
    assert published.status_code == 400
    assert published.json()["code"] == "INCOMPLETE_TOURNAMENT"


def test_registration_capacity_review_and_duplicate_boundary(client, make_user, session_factory) -> None:
    admin, admin_token = make_user(
        qq_number="80000003", nickname="审核管理员", role=Role.USER
    )
    player_a, token_a = make_user(qq_number="80000004", nickname="玩家甲")
    _, token_b = make_user(qq_number="80000005", nickname="玩家乙")
    _, token_c = make_user(qq_number="80000006", nickname="玩家丙")
    _, token_d = make_user(qq_number="80000012", nickname="玩家丁")
    banlist_id = seed_banlist(session_factory, admin.id)
    tournament_id = create_and_publish(client, admin_token, banlist_id, max_players=2)
    confirmation = {"nickname_matches_game": True, "accepts_rules": True}

    first = client.post(
        f"/api/tournaments/{tournament_id}/registrations", headers=auth(token_a), json=confirmation
    )
    second = client.post(
        f"/api/tournaments/{tournament_id}/registrations", headers=auth(token_b), json=confirmation
    )
    third = client.post(
        f"/api/tournaments/{tournament_id}/registrations", headers=auth(token_c), json=confirmation
    )
    duplicate = client.post(
        f"/api/tournaments/{tournament_id}/registrations", headers=auth(token_a), json=confirmation
    )
    approved = client.post(
        f"/api/admin/tournaments/{tournament_id}/registrations/{first.json()['id']}/approve",
        headers=auth(admin_token),
    )
    second_approved = client.post(
        f"/api/admin/tournaments/{tournament_id}/registrations/{second.json()['id']}/approve",
        headers=auth(admin_token),
    )
    over_capacity = client.post(
        f"/api/admin/tournaments/{tournament_id}/registrations/{third.json()['id']}/approve",
        headers=auth(admin_token),
    )
    closed_for_new = client.post(
        f"/api/tournaments/{tournament_id}/registrations", headers=auth(token_d), json=confirmation
    )

    assert first.status_code == second.status_code == third.status_code == 201
    assert duplicate.status_code == 409
    assert approved.json()["status"] == "APPROVED"
    assert second_approved.json()["status"] == "APPROVED"
    assert over_capacity.status_code == 409
    assert over_capacity.json()["code"] == "TOURNAMENT_FULL"
    assert closed_for_new.status_code == 409
    with session_factory() as db:
        approved_count = db.scalar(select(func.count()).select_from(Registration).where(
            Registration.tournament_id == UUID(tournament_id),
            Registration.status == RegistrationStatus.APPROVED.value,
        ))
    assert approved_count == 2


def test_cancel_reject_and_restore_transitions(client, make_user, session_factory) -> None:
    admin, admin_token = make_user(
        qq_number="80000007", nickname="恢复管理员", role=Role.USER
    )
    _, player_token = make_user(qq_number="80000008", nickname="恢复玩家")
    banlist_id = seed_banlist(session_factory, admin.id)
    tournament_id = create_and_publish(client, admin_token, banlist_id)
    applied = client.post(
        f"/api/tournaments/{tournament_id}/registrations",
        headers=auth(player_token),
        json={"nickname_matches_game": True, "accepts_rules": True},
    )
    registration_id = applied.json()["id"]

    rejected = client.post(
        f"/api/admin/tournaments/{tournament_id}/registrations/{registration_id}/reject",
        headers=auth(admin_token),
    )
    restored = client.post(
        f"/api/admin/tournaments/{tournament_id}/registrations/{registration_id}/restore",
        headers=auth(admin_token),
    )
    canceled = client.post(
        f"/api/tournaments/{tournament_id}/registrations/cancel", headers=auth(player_token)
    )
    admin_list = client.get(
        f"/api/admin/tournaments/{tournament_id}/registrations", headers=auth(admin_token)
    )
    reapplied = client.post(
        f"/api/tournaments/{tournament_id}/registrations",
        headers=auth(player_token),
        json={"nickname_matches_game": True, "accepts_rules": True},
    )
    admin_canceled = client.post(
        f"/api/admin/tournaments/{tournament_id}/registrations/{registration_id}/cancel",
        headers=auth(admin_token),
    )
    blocked_reapply = client.post(
        f"/api/tournaments/{tournament_id}/registrations",
        headers=auth(player_token),
        json={"nickname_matches_game": True, "accepts_rules": True},
    )
    admin_list_after_cancel = client.get(
        f"/api/admin/tournaments/{tournament_id}/registrations", headers=auth(admin_token)
    )

    assert rejected.json()["status"] == "REJECTED"
    assert restored.json()["status"] == "APPROVED"
    assert canceled.json()["status"] == "CANCELED"
    assert admin_list.status_code == 200
    assert all(item["id"] != registration_id for item in admin_list.json()["items"])
    assert admin_list.json()["total"] == 0
    assert reapplied.status_code == 201
    assert reapplied.json()["id"] == registration_id
    assert reapplied.json()["status"] == "PENDING"
    assert admin_canceled.json()["status"] == "CANCELED"
    assert blocked_reapply.status_code == 409
    assert blocked_reapply.json()["code"] == "REGISTRATION_EXISTS"
    assert admin_list_after_cancel.json()["total"] == 1
    assert admin_list_after_cancel.json()["items"][0]["id"] == registration_id


def test_start_blocks_pending_snapshots_approved_and_locks_core_config(client, make_user, session_factory) -> None:
    admin, admin_token = make_user(
        qq_number="80000009", nickname="开赛管理员", role=Role.USER
    )
    player, player_token = make_user(qq_number="80000010", nickname="正式选手")
    banlist_id = seed_banlist(session_factory, admin.id)
    tournament_id = create_and_publish(client, admin_token, banlist_id)
    applied = client.post(
        f"/api/tournaments/{tournament_id}/registrations",
        headers=auth(player_token),
        json={"nickname_matches_game": True, "accepts_rules": True},
    )

    blocked = client.post(f"/api/admin/tournaments/{tournament_id}/start", headers=auth(admin_token))
    client.post(
        f"/api/admin/tournaments/{tournament_id}/registrations/{applied.json()['id']}/approve",
        headers=auth(admin_token),
    )
    started = client.post(f"/api/admin/tournaments/{tournament_id}/start", headers=auth(admin_token))
    late_apply = client.post(
        f"/api/tournaments/{tournament_id}/registrations",
        headers=auth(player_token),
        json={"nickname_matches_game": True, "accepts_rules": True},
    )
    locked = client.patch(
        f"/api/admin/tournaments/{tournament_id}",
        headers=auth(admin_token),
        json={"max_players": 64},
    )
    description_update = client.patch(
        f"/api/admin/tournaments/{tournament_id}",
        headers=auth(admin_token),
        json={"description": "开赛后仍可修正文案"},
    )

    assert blocked.status_code == 409
    assert blocked.json()["code"] == "PENDING_REGISTRATIONS"
    assert started.status_code == 200
    assert started.json()["status"] == "SWISS"
    assert late_apply.status_code == 409
    assert late_apply.json()["code"] == "REGISTRATION_CLOSED"
    assert locked.status_code == 409
    assert locked.json()["code"] == "CORE_CONFIG_LOCKED"
    assert description_update.status_code == 200
    assert client.delete(
        f"/api/admin/tournaments/{tournament_id}", headers=auth(admin_token)
    ).status_code == 409
    assert client.post(
        f"/api/admin/tournaments/{tournament_id}/cancel",
        headers=auth(admin_token),
        json={"reason": "已经开赛"},
    ).status_code == 409
    with session_factory() as db:
        participants = list(db.scalars(select(TournamentParticipant)))
        tournament = db.get(Tournament, UUID(tournament_id))
    assert len(participants) == 1
    assert participants[0].user_id == player.id
    assert participants[0].nickname_snapshot == "正式选手"
    assert tournament.status == TournamentStatus.SWISS.value


def test_user_can_create_draft_but_cannot_manage_another_users_tournament(client, make_user) -> None:
    _, owner_token = make_user(qq_number="80000011", nickname="普通用户")
    _, other_token = make_user(qq_number="80000012", nickname="其他用户")

    created = client.post(
        "/api/admin/tournaments",
        headers=auth(owner_token),
        json={"name": "普通用户草稿赛事"},
    )
    forbidden = client.get(
        f"/api/admin/tournaments/{created.json()['id']}",
        headers=auth(other_token),
    )

    assert created.status_code == 201
    assert created.json()["status"] == "DRAFT"
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "TOURNAMENT_OWNER_REQUIRED"


def test_tournament_owner_can_also_register_as_player(client, make_user, session_factory) -> None:
    admin, admin_token = make_user(
        qq_number="80000013", nickname="参赛管理员", role=Role.USER
    )
    banlist_id = seed_banlist(session_factory, admin.id)
    tournament_id = create_and_publish(client, admin_token, banlist_id)

    response = client.post(
        f"/api/tournaments/{tournament_id}/registrations",
        headers=auth(admin_token),
        json={"nickname_matches_game": True, "accepts_rules": True},
    )

    assert response.status_code == 201
    assert response.json()["user_id"] == str(admin.id)
    assert response.json()["status"] == RegistrationStatus.PENDING.value

    with session_factory() as db:
        registration = db.scalar(select(Registration).where(
            Registration.tournament_id == UUID(tournament_id),
            Registration.user_id == admin.id,
        ))
    assert registration is not None
    assert registration.status == RegistrationStatus.PENDING.value


def test_owner_can_soft_delete_unstarted_tournament_without_active_registrations(
    client, make_user, session_factory
) -> None:
    owner, owner_token = make_user(qq_number="80000014", nickname="删除赛事管理员")
    _, other_token = make_user(qq_number="80000015", nickname="非赛事所有者")
    _, player_token = make_user(qq_number="80000019", nickname="已取消报名玩家")
    banlist_id = seed_banlist(session_factory, owner.id)
    tournament_id = create_and_publish(client, owner_token, banlist_id)
    client.post(
        f"/api/tournaments/{tournament_id}/registrations",
        headers=auth(player_token),
        json={"nickname_matches_game": True, "accepts_rules": True},
    )
    client.post(
        f"/api/tournaments/{tournament_id}/registrations/cancel",
        headers=auth(player_token),
    )
    tournament_code = client.get(f"/api/tournaments/{tournament_id}").json()["code"]
    blocked_cancel = client.post(
        f"/api/admin/tournaments/{tournament_id}/cancel",
        headers=auth(owner_token),
        json={"reason": None},
    )

    forbidden = client.delete(
        f"/api/admin/tournaments/{tournament_id}", headers=auth(other_token)
    )
    deleted = client.delete(
        f"/api/admin/tournaments/{tournament_id}", headers=auth(owner_token)
    )

    assert forbidden.status_code == 403
    assert blocked_cancel.status_code == 409
    assert blocked_cancel.json()["code"] == "TOURNAMENT_HAS_NO_ACTIVE_REGISTRATIONS"
    assert deleted.status_code == 204
    assert client.get(f"/api/tournaments/{tournament_id}").status_code == 404
    assert client.get(f"/api/tournaments/code/{tournament_code}").status_code == 404
    assert client.get(
        f"/api/admin/tournaments/{tournament_id}", headers=auth(owner_token)
    ).status_code == 404
    assert client.get("/api/tournaments").json()["total"] == 0
    assert client.get(
        f"/api/tournaments/{tournament_id}/registrations/me", headers=auth(player_token)
    ).status_code == 404
    assert client.get("/api/me/tournaments", headers=auth(player_token)).json()["total"] == 0
    assert client.get(
        "/api/me/created-tournaments", headers=auth(owner_token)
    ).json()["total"] == 0

    with session_factory() as db:
        tournament = db.get(Tournament, UUID(tournament_id))
        audit = db.scalar(select(AuditLog).where(
            AuditLog.tournament_id == UUID(tournament_id),
            AuditLog.action_type == "TOURNAMENT_DELETED",
        ))
    assert tournament is not None
    assert tournament.deleted_at is not None
    assert audit is not None


def test_tournament_with_active_registration_is_canceled_instead_of_deleted(
    client, make_user, session_factory
) -> None:
    owner, owner_token = make_user(qq_number="80000016", nickname="取消赛事管理员")
    player, player_token = make_user(qq_number="80000017", nickname="被取消报名玩家")
    _, approved_player_token = make_user(qq_number="80000018", nickname="已通过报名玩家")
    banlist_id = seed_banlist(session_factory, owner.id)
    tournament_id = create_and_publish(client, owner_token, banlist_id)
    applied = client.post(
        f"/api/tournaments/{tournament_id}/registrations",
        headers=auth(player_token),
        json={"nickname_matches_game": True, "accepts_rules": True},
    )
    approved_application = client.post(
        f"/api/tournaments/{tournament_id}/registrations",
        headers=auth(approved_player_token),
        json={"nickname_matches_game": True, "accepts_rules": True},
    )
    client.post(
        f"/api/admin/tournaments/{tournament_id}/registrations/{approved_application.json()['id']}/approve",
        headers=auth(owner_token),
    )

    blocked_delete = client.delete(
        f"/api/admin/tournaments/{tournament_id}", headers=auth(owner_token)
    )
    canceled = client.post(
        f"/api/admin/tournaments/{tournament_id}/cancel",
        headers=auth(owner_token),
        json={"reason": "  参赛人数不足  "},
    )

    assert blocked_delete.status_code == 409
    assert blocked_delete.json()["code"] == "TOURNAMENT_HAS_ACTIVE_REGISTRATIONS"
    assert canceled.status_code == 200, canceled.json()
    assert canceled.json()["status"] == "CANCELED"
    assert canceled.json()["cancellation_reason"] == "参赛人数不足"
    assert canceled.json()["canceled_at"] is not None
    assert canceled.json()["pending_count"] == 0
    assert canceled.json()["approved_count"] == 0

    public = client.get(f"/api/tournaments/{tournament_id}")
    player_tournaments = client.get("/api/me/tournaments", headers=auth(player_token)).json()
    assert public.status_code == 200
    assert public.json()["status"] == "CANCELED"
    assert player_tournaments["total"] == 1
    assert player_tournaments["items"][0]["status"] == "CANCELED"
    assert player_tournaments["items"][0]["registration_status"] == "CANCELED"

    blocked_start = client.post(
        f"/api/admin/tournaments/{tournament_id}/start", headers=auth(owner_token)
    )
    blocked_update = client.patch(
        f"/api/admin/tournaments/{tournament_id}",
        headers=auth(owner_token),
        json={"description": "不应允许修改"},
    )
    blocked_apply = client.post(
        f"/api/tournaments/{tournament_id}/registrations",
        headers=auth(player_token),
        json={"nickname_matches_game": True, "accepts_rules": True},
    )
    assert blocked_start.status_code == 409
    assert blocked_update.status_code == 409
    assert blocked_update.json()["code"] == "TOURNAMENT_CANCELED"
    assert blocked_apply.status_code == 409
    assert blocked_apply.json()["code"] == "REGISTRATION_CLOSED"

    with session_factory() as db:
        registration = db.get(Registration, UUID(applied.json()["id"]))
        canceled_registration_count = db.scalar(select(func.count()).select_from(Registration).where(
            Registration.tournament_id == UUID(tournament_id),
            Registration.status == RegistrationStatus.CANCELED.value,
        ))
        audit = db.scalar(select(AuditLog).where(
            AuditLog.tournament_id == UUID(tournament_id),
            AuditLog.action_type == "TOURNAMENT_CANCELED",
        ))
    assert registration is not None
    assert registration.user_id == player.id
    assert registration.status == RegistrationStatus.CANCELED.value
    assert registration.reviewed_by_id == owner.id
    assert registration.reviewed_at is not None
    assert canceled_registration_count == 2
    assert audit is not None
    assert audit.before_json["pending_count"] == 1
    assert audit.before_json["approved_count"] == 1
