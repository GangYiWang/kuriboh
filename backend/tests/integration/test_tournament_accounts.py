from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select

from app.audit.models import AuditLog
from app.content.models import BanlistVersion
from app.messages.models import Message
from app.registrations.models import Registration
from app.tournament_accounts.models import (
    AccountReplacementRequest,
    AccountReplacementStatus,
    AccountType,
    TournamentAccount,
    TournamentAccountStatus,
)
from app.tournament_accounts.crypto import CredentialCipher
from app.tournaments.models import Tournament, TournamentStatus


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_published_tournament(client, session_factory, owner_id, owner_token: str) -> str:
    with session_factory() as db:
        banlist = db.scalar(select(BanlistVersion).order_by(BanlistVersion.created_at).limit(1))
        if banlist is None:
            banlist = BanlistVersion(
                major_version=9,
                minor_version=1,
                title="赛事账号测试禁卡表",
                content_html="<p>测试</p>",
                published_at=datetime.now(UTC),
                created_by_id=owner_id,
            )
            db.add(banlist)
            db.commit()
            db.refresh(banlist)
        banlist_id = banlist.id
    created = client.post(
        "/api/admin/tournaments",
        headers=auth(owner_token),
        json={
            "name": "赛事账号分发测试赛",
            "description": "测试赛事账号库存与领取",
            "planned_start_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            "max_players": 8,
            "swiss_rounds": 3,
            "playoff_size": 2,
            "banlist_version_id": str(banlist_id),
        },
    )
    assert created.status_code == 201, created.json()
    tournament_id = created.json()["id"]
    published = client.post(
        f"/api/admin/tournaments/{tournament_id}/publish",
        headers=auth(owner_token),
    )
    assert published.status_code == 200, published.json()
    return tournament_id


def register_and_approve(client, tournament_id: str, player_token: str, owner_token: str) -> str:
    applied = client.post(
        f"/api/tournaments/{tournament_id}/registrations",
        headers=auth(player_token),
        json={"nickname_matches_game": True, "accepts_rules": True},
    )
    assert applied.status_code == 201, applied.json()
    registration_id = applied.json()["id"]
    approved = client.post(
        f"/api/admin/tournaments/{tournament_id}/registrations/{registration_id}/approve",
        headers=auth(owner_token),
    )
    assert approved.status_code == 200, approved.json()
    return registration_id


def import_file(client, tournament_id: str, owner_token: str, account_type: str, content: bytes):
    return client.post(
        f"/api/admin/tournaments/{tournament_id}/accounts/{account_type}/imports",
        headers=auth(owner_token),
        files={"file": (f"{account_type.lower()}.txt", content, "text/plain")},
    )


def test_import_is_atomic_case_sensitive_and_encrypted(client, make_user, session_factory) -> None:
    owner, owner_token = make_user(qq_number="83000001", nickname="账号导入管理员")
    _, other_token = make_user(qq_number="83000002", nickname="其他赛事管理员")
    tournament_id = create_published_tournament(client, session_factory, owner.id, owner_token)

    forbidden = import_file(
        client, tournament_id, other_token, AccountType.KONAMI.value, b"CaseUser----password-1"
    )
    imported = import_file(
        client,
        tournament_id,
        owner_token,
        AccountType.KONAMI.value,
        (
            "\n科乐美账号:CaseUser,密码:password-1------邮箱:first@example.com\n"
            "科乐美账号:caseuser,密码:password-2------邮箱:second@example.com\n\n"
        ).encode(),
    )

    assert forbidden.status_code == 403
    assert imported.status_code == 200, imported.json()
    assert imported.json()["imported_count"] == 2
    assert imported.json()["available_count"] == 2

    admin_list = client.get(
        f"/api/admin/tournaments/{tournament_id}/accounts?type=KONAMI",
        headers=auth(owner_token),
    )
    assert admin_list.status_code == 200
    assert admin_list.headers["cache-control"] == "no-store"
    assert {item["account"] for item in admin_list.json()["items"]} == {"CaseUser", "caseuser"}
    assert all("password" not in item for item in admin_list.json()["items"])

    with session_factory() as db:
        stored = list(db.scalars(select(TournamentAccount)))
        audit = db.scalar(select(AuditLog).where(
            AuditLog.action_type == "TOURNAMENT_ACCOUNTS_IMPORTED"
        ))
    assert len(stored) == 2
    assert all(item.account_ciphertext not in {"CaseUser", "caseuser"} for item in stored)
    assert all(item.password_ciphertext not in {"password-1", "password-2"} for item in stored)
    cipher = CredentialCipher()
    assert {cipher.decrypt(item.account_ciphertext) for item in stored} == {"CaseUser", "caseuser"}
    assert {cipher.decrypt(item.password_ciphertext) for item in stored} == {"password-1", "password-2"}
    assert audit is not None
    assert "password" not in str(audit.after_json).lower()

    invalid = import_file(
        client,
        tournament_id,
        owner_token,
        AccountType.KONAMI.value,
        b"new-account----new-password\nbroken-line",
    )
    assert invalid.status_code == 400
    assert invalid.json()["code"] == "ACCOUNT_IMPORT_INVALID"
    assert invalid.json()["details"]["errors"] == [
        {"line": 2, "reason": "必须使用四个短横线分隔账号和密码"}
    ]
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(TournamentAccount)) == 2


def test_exact_duplicate_import_is_rejected_without_partial_write(client, make_user, session_factory) -> None:
    owner, owner_token = make_user(qq_number="83000003", nickname="重复账号管理员")
    tournament_id = create_published_tournament(client, session_factory, owner.id, owner_token)
    first = import_file(
        client, tournament_id, owner_token, AccountType.STEAM.value, b"steam-user----steam-password"
    )
    duplicate = import_file(
        client,
        tournament_id,
        owner_token,
        AccountType.STEAM.value,
        b"another-user----another-password\nsteam-user----changed-password",
    )

    assert first.status_code == 200
    assert duplicate.status_code == 400
    assert duplicate.json()["code"] == "ACCOUNT_IMPORT_INVALID"
    assert duplicate.json()["details"]["errors"] == [
        {"line": 2, "reason": "该账号已导入过本场赛事"}
    ]
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(TournamentAccount)) == 1


def test_approved_player_claims_each_type_once_and_can_view_it(client, make_user, session_factory) -> None:
    owner, owner_token = make_user(qq_number="83000004", nickname="领取账号管理员")
    player, player_token = make_user(qq_number="83000005", nickname="领取账号选手")
    _, pending_token = make_user(qq_number="83000006", nickname="待审核选手")
    tournament_id = create_published_tournament(client, session_factory, owner.id, owner_token)
    register_and_approve(client, tournament_id, player_token, owner_token)
    pending = client.post(
        f"/api/tournaments/{tournament_id}/registrations",
        headers=auth(pending_token),
        json={"nickname_matches_game": True, "accepts_rules": True},
    )
    assert pending.status_code == 201
    assert import_file(
        client, tournament_id, owner_token, AccountType.KONAMI.value, b"konami-user----konami-password"
    ).status_code == 200
    assert import_file(
        client, tournament_id, owner_token, AccountType.STEAM.value, b"steam-user----steam-password"
    ).status_code == 200

    blocked = client.post(
        f"/api/tournaments/{tournament_id}/accounts/KONAMI/claim",
        headers=auth(pending_token),
    )
    claimed = client.post(
        f"/api/tournaments/{tournament_id}/accounts/KONAMI/claim",
        headers=auth(player_token),
    )
    duplicate = client.post(
        f"/api/tournaments/{tournament_id}/accounts/KONAMI/claim",
        headers=auth(player_token),
    )
    steam = client.post(
        f"/api/tournaments/{tournament_id}/accounts/STEAM/claim",
        headers=auth(player_token),
    )
    mine = client.get(
        f"/api/tournaments/{tournament_id}/accounts/me",
        headers=auth(player_token),
    )

    assert blocked.status_code == 403
    assert blocked.json()["code"] == "APPROVED_REGISTRATION_REQUIRED"
    assert claimed.status_code == 200, claimed.json()
    assert claimed.headers["cache-control"] == "no-store"
    assert claimed.json()["account"] == "konami-user"
    assert claimed.json()["password"] == "konami-password"
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "ACCOUNT_ALREADY_CLAIMED"
    assert steam.status_code == 200
    assert mine.status_code == 200
    assert mine.headers["cache-control"] == "no-store"
    assert {item["account_type"] for item in mine.json()["items"]} == {"KONAMI", "STEAM"}

    admin_list = client.get(
        f"/api/admin/tournaments/{tournament_id}/accounts?type=KONAMI",
        headers=auth(owner_token),
    ).json()
    assert admin_list["summaries"][0] == {
        "account_type": "KONAMI",
        "total": 1,
        "available": 0,
        "reserved": 0,
        "claimed": 1,
        "invalid": 0,
        "transferred": 0,
    }
    assert admin_list["items"][0]["claimed_by_user_id"] == str(player.id)
    assert admin_list["items"][0]["claimed_by_nickname"] == "领取账号选手"

    with session_factory() as db:
        registration = db.scalar(select(Registration).where(
            Registration.tournament_id == UUID(tournament_id),
            Registration.user_id == player.id,
        ))
        claims = list(db.scalars(select(TournamentAccount).where(
            TournamentAccount.claimed_registration_id == registration.id
        )))
    assert len(claims) == 2


def test_empty_inventory_and_closed_tournament_boundaries(client, make_user, session_factory) -> None:
    owner, owner_token = make_user(qq_number="83000007", nickname="库存边界管理员")
    _, player_token = make_user(qq_number="83000008", nickname="库存边界选手")
    tournament_id = create_published_tournament(client, session_factory, owner.id, owner_token)
    register_and_approve(client, tournament_id, player_token, owner_token)

    empty = client.post(
        f"/api/tournaments/{tournament_id}/accounts/KONAMI/claim",
        headers=auth(player_token),
    )
    assert empty.status_code == 409
    assert empty.json()["code"] == "ACCOUNT_INVENTORY_EMPTY"

    with session_factory() as db:
        tournament = db.get(Tournament, UUID(tournament_id))
        tournament.status = TournamentStatus.ENDED.value
        tournament.ended_at = datetime.now(UTC)
        db.commit()

    closed_claim = client.post(
        f"/api/tournaments/{tournament_id}/accounts/KONAMI/claim",
        headers=auth(player_token),
    )
    closed_import = import_file(
        client, tournament_id, owner_token, AccountType.KONAMI.value, b"late-user----late-password"
    )
    assert closed_claim.status_code == 409
    assert closed_claim.json()["code"] == "ACCOUNT_CLAIM_CLOSED"
    assert closed_import.status_code == 409
    assert closed_import.json()["code"] == "ACCOUNT_IMPORT_CLOSED"


def test_replacement_requires_reasons_and_rejected_player_can_apply_again(
    client, make_user, session_factory
) -> None:
    owner, owner_token = make_user(qq_number="83000009", nickname="换号拒绝管理员")
    _, other_token = make_user(qq_number="83000010", nickname="其他换号管理员")
    _, player_token = make_user(qq_number="83000011", nickname="换号申请选手")
    tournament_id = create_published_tournament(client, session_factory, owner.id, owner_token)
    register_and_approve(client, tournament_id, player_token, owner_token)
    assert import_file(
        client,
        tournament_id,
        owner_token,
        AccountType.KONAMI.value,
        b"first-konami----first-password\nsecond-konami----second-password",
    ).status_code == 200
    first_claim = client.post(
        f"/api/tournaments/{tournament_id}/accounts/KONAMI/claim",
        headers=auth(player_token),
    )
    assert first_claim.status_code == 200

    blank_request = client.post(
        f"/api/tournaments/{tournament_id}/accounts/KONAMI/replacement-requests",
        headers=auth(player_token),
        json={"reason": "   "},
    )
    requested = client.post(
        f"/api/tournaments/{tournament_id}/accounts/KONAMI/replacement-requests",
        headers=auth(player_token),
        json={"reason": "  无法登录账号  "},
    )
    request_id = requested.json()["id"]
    duplicate = client.post(
        f"/api/tournaments/{tournament_id}/accounts/KONAMI/replacement-requests",
        headers=auth(player_token),
        json={"reason": "再次申请"},
    )
    forbidden = client.get(
        f"/api/admin/tournaments/{tournament_id}/account-replacement-requests",
        headers=auth(other_token),
    )
    blank_rejection = client.post(
        f"/api/admin/tournaments/{tournament_id}/account-replacement-requests/{request_id}/reject",
        headers=auth(owner_token),
        json={"reason": ""},
    )
    rejected = client.post(
        f"/api/admin/tournaments/{tournament_id}/account-replacement-requests/{request_id}/reject",
        headers=auth(owner_token),
        json={"reason": "  人工检查后账号可以正常登录  "},
    )

    assert blank_request.status_code == 422
    assert requested.status_code == 200, requested.json()
    assert requested.json()["reason"] == "无法登录账号"
    assert requested.json()["status"] == AccountReplacementStatus.PENDING.value
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "ACCOUNT_REPLACEMENT_EXISTS"
    assert forbidden.status_code == 403
    assert blank_rejection.status_code == 422
    assert rejected.status_code == 200, rejected.json()
    assert rejected.json()["status"] == AccountReplacementStatus.REJECTED.value
    assert rejected.json()["rejection_reason"] == "人工检查后账号可以正常登录"

    mine = client.get(
        f"/api/tournaments/{tournament_id}/accounts/me",
        headers=auth(player_token),
    ).json()
    assert mine["items"][0]["account"] == first_claim.json()["account"]
    assert mine["replacement_requests"][0]["status"] == AccountReplacementStatus.REJECTED.value

    reapplied = client.post(
        f"/api/tournaments/{tournament_id}/accounts/KONAMI/replacement-requests",
        headers=auth(player_token),
        json={"reason": "仍然无法登录，申请再次检查"},
    )
    assert reapplied.status_code == 200, reapplied.json()
    assert reapplied.json()["status"] == AccountReplacementStatus.PENDING.value


def test_approved_replacement_reserves_account_until_player_claims(
    client, make_user, session_factory
) -> None:
    owner, owner_token = make_user(qq_number="83000012", nickname="换号通过管理员")
    player, player_token = make_user(qq_number="83000013", nickname="换号领取选手")
    tournament_id = create_published_tournament(client, session_factory, owner.id, owner_token)
    registration_id = register_and_approve(client, tournament_id, player_token, owner_token)
    assert import_file(
        client,
        tournament_id,
        owner_token,
        AccountType.STEAM.value,
        b"old-steam----old-password\nnew-steam----new-password",
    ).status_code == 200
    first = client.post(
        f"/api/tournaments/{tournament_id}/accounts/STEAM/claim",
        headers=auth(player_token),
    )
    assert first.status_code == 200
    original_account = first.json()["account"]
    replacement_account = "new-steam" if original_account == "old-steam" else "old-steam"
    replacement_password = "new-password" if replacement_account == "new-steam" else "old-password"
    requested = client.post(
        f"/api/tournaments/{tournament_id}/accounts/STEAM/replacement-requests",
        headers=auth(player_token),
        json={"reason": "账号提示受限"},
    )
    request_id = requested.json()["id"]
    approved = client.post(
        f"/api/admin/tournaments/{tournament_id}/account-replacement-requests/{request_id}/approve",
        headers=auth(owner_token),
    )

    assert approved.status_code == 200, approved.json()
    assert approved.json()["status"] == AccountReplacementStatus.APPROVED.value
    assert approved.json()["original_account"] == original_account
    assert approved.json()["replacement_account"] == replacement_account

    waiting = client.get(
        f"/api/tournaments/{tournament_id}/accounts/me",
        headers=auth(player_token),
    ).json()
    assert waiting["items"] == []
    assert waiting["replacement_requests"][0]["status"] == AccountReplacementStatus.APPROVED.value

    admin_inventory = client.get(
        f"/api/admin/tournaments/{tournament_id}/accounts?type=STEAM",
        headers=auth(owner_token),
    ).json()
    steam_summary = next(item for item in admin_inventory["summaries"] if item["account_type"] == "STEAM")
    assert steam_summary == {
        "account_type": "STEAM",
        "total": 2,
        "available": 0,
        "reserved": 1,
        "claimed": 0,
        "invalid": 1,
        "transferred": 0,
    }

    reclaimed = client.post(
        f"/api/tournaments/{tournament_id}/accounts/STEAM/claim",
        headers=auth(player_token),
    )
    assert reclaimed.status_code == 200, reclaimed.json()
    assert reclaimed.json()["account"] == replacement_account
    assert reclaimed.json()["password"] == replacement_password
    duplicate = client.post(
        f"/api/tournaments/{tournament_id}/accounts/STEAM/claim",
        headers=auth(player_token),
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "ACCOUNT_ALREADY_CLAIMED"

    completed = client.get(
        f"/api/tournaments/{tournament_id}/accounts/me",
        headers=auth(player_token),
    ).json()
    assert completed["items"][0]["account"] == replacement_account
    assert completed["replacement_requests"][0]["status"] == AccountReplacementStatus.COMPLETED.value

    with session_factory() as db:
        old_account = db.scalar(select(TournamentAccount).where(
            TournamentAccount.claimed_registration_id == UUID(registration_id),
            TournamentAccount.status == TournamentAccountStatus.INVALID.value,
        ))
        current_account = db.scalar(select(TournamentAccount).where(
            TournamentAccount.claimed_registration_id == UUID(registration_id),
            TournamentAccount.status == TournamentAccountStatus.CLAIMED.value,
        ))
        replacement_request = db.get(AccountReplacementRequest, UUID(request_id))
        message = db.scalar(select(Message).where(
            Message.recipient_id == player.id,
            Message.dedupe_key == f"account-replacement:{request_id}:approved",
        ))
    assert old_account is not None
    assert current_account is not None
    assert current_account.id != old_account.id
    assert replacement_request.status == AccountReplacementStatus.COMPLETED.value
    assert replacement_request.completed_at is not None
    assert message is not None


def test_replacement_approval_requires_available_inventory(client, make_user, session_factory) -> None:
    owner, owner_token = make_user(qq_number="83000014", nickname="无库存换号管理员")
    _, player_token = make_user(qq_number="83000015", nickname="无库存换号选手")
    tournament_id = create_published_tournament(client, session_factory, owner.id, owner_token)
    register_and_approve(client, tournament_id, player_token, owner_token)
    assert import_file(
        client, tournament_id, owner_token, AccountType.KONAMI.value, b"only-account----only-password"
    ).status_code == 200
    assert client.post(
        f"/api/tournaments/{tournament_id}/accounts/KONAMI/claim",
        headers=auth(player_token),
    ).status_code == 200
    requested = client.post(
        f"/api/tournaments/{tournament_id}/accounts/KONAMI/replacement-requests",
        headers=auth(player_token),
        json={"reason": "账号无法登录"},
    )
    request_id = requested.json()["id"]
    blocked = client.post(
        f"/api/admin/tournaments/{tournament_id}/account-replacement-requests/{request_id}/approve",
        headers=auth(owner_token),
    )

    assert blocked.status_code == 409
    assert blocked.json()["code"] == "ACCOUNT_INVENTORY_EMPTY"
    with session_factory() as db:
        request = db.get(AccountReplacementRequest, UUID(request_id))
        account = db.scalar(select(TournamentAccount).where(
            TournamentAccount.tournament_id == UUID(tournament_id)
        ))
    assert request.status == AccountReplacementStatus.PENDING.value
    assert account.status == TournamentAccountStatus.CLAIMED.value


def test_available_accounts_carry_over_from_all_ended_owner_tournaments(
    client, make_user, session_factory
) -> None:
    owner, owner_token = make_user(qq_number="83000016", nickname="余号结转管理员")
    other_owner, other_token = make_user(qq_number="83000017", nickname="其他余号管理员")
    _, player_token = make_user(qq_number="83000018", nickname="已领取选手")
    first_source_id = create_published_tournament(client, session_factory, owner.id, owner_token)
    second_source_id = create_published_tournament(client, session_factory, owner.id, owner_token)
    target_id = create_published_tournament(client, session_factory, owner.id, owner_token)
    other_source_id = create_published_tournament(client, session_factory, other_owner.id, other_token)

    register_and_approve(client, first_source_id, player_token, owner_token)
    assert import_file(
        client,
        first_source_id,
        owner_token,
        AccountType.KONAMI.value,
        b"claimed-konami----claimed-password\ncarry-konami-one----carry-password-one",
    ).status_code == 200
    assert import_file(
        client,
        first_source_id,
        owner_token,
        AccountType.STEAM.value,
        b"carry-steam----carry-steam-password",
    ).status_code == 200
    assert client.post(
        f"/api/tournaments/{first_source_id}/accounts/KONAMI/claim",
        headers=auth(player_token),
    ).status_code == 200
    assert import_file(
        client,
        second_source_id,
        owner_token,
        AccountType.KONAMI.value,
        b"carry-konami-two----carry-password-two",
    ).status_code == 200
    assert import_file(
        client,
        other_source_id,
        other_token,
        AccountType.STEAM.value,
        b"other-owner-steam----other-password",
    ).status_code == 200

    with session_factory() as db:
        for source_id in (first_source_id, second_source_id, other_source_id):
            tournament = db.get(Tournament, UUID(source_id))
            tournament.status = TournamentStatus.ENDED.value
            tournament.ended_at = datetime.now(UTC)
        db.commit()

    forbidden = client.get(
        f"/api/admin/tournaments/{target_id}/accounts/carryover-preview",
        headers=auth(other_token),
    )
    preview = client.get(
        f"/api/admin/tournaments/{target_id}/accounts/carryover-preview",
        headers=auth(owner_token),
    )
    carried = client.post(
        f"/api/admin/tournaments/{target_id}/accounts/carryover",
        headers=auth(owner_token),
        json={},
    )

    assert forbidden.status_code == 403
    assert preview.status_code == 200, preview.json()
    assert preview.json() == {
        "konami_count": 2,
        "steam_count": 1,
        "total_count": 3,
        "source_tournament_count": 2,
    }
    assert carried.status_code == 200, carried.json()
    assert carried.json() == preview.json()

    target_inventory = client.get(
        f"/api/admin/tournaments/{target_id}/accounts?type=KONAMI",
        headers=auth(owner_token),
    ).json()
    summaries = {item["account_type"]: item for item in target_inventory["summaries"]}
    assert summaries["KONAMI"]["available"] == 2
    assert summaries["STEAM"]["available"] == 1

    repeated = client.post(
        f"/api/admin/tournaments/{target_id}/accounts/carryover",
        headers=auth(owner_token),
        json={},
    )
    assert repeated.status_code == 200
    assert repeated.json()["total_count"] == 0

    with session_factory() as db:
        transferred = list(db.scalars(select(TournamentAccount).where(
            TournamentAccount.status == TournamentAccountStatus.TRANSFERRED.value,
        )))
        target_accounts = list(db.scalars(select(TournamentAccount).where(
            TournamentAccount.tournament_id == UUID(target_id),
        )))
        other_available = db.scalar(select(func.count()).select_from(TournamentAccount).where(
            TournamentAccount.tournament_id == UUID(other_source_id),
            TournamentAccount.status == TournamentAccountStatus.AVAILABLE.value,
        ))
        audit_actions = set(db.scalars(select(AuditLog.action_type).where(
            AuditLog.action_type.in_([
                "TOURNAMENT_ACCOUNTS_CARRIED_OVER_IN",
                "TOURNAMENT_ACCOUNTS_CARRIED_OVER_OUT",
            ])
        )))
    assert len(transferred) == 3
    assert len(target_accounts) == 3
    assert all(item.transferred_from_account_id is not None for item in target_accounts)
    assert other_available == 1
    assert audit_actions == {
        "TOURNAMENT_ACCOUNTS_CARRIED_OVER_IN",
        "TOURNAMENT_ACCOUNTS_CARRIED_OVER_OUT",
    }
