from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.auth.security import create_token, verify_password
from app.users.models import User


def registration_payload(**overrides: str) -> dict[str, str]:
    payload = {
        "identifier_type": "PHONE",
        "identifier": "13800138000",
        "nickname": "海盐栗子",
        "password": "secure123",
        "confirm_password": "secure123",
    }
    payload.update(overrides)
    return payload


def test_register_by_phone_login_profile_and_change_password(
    client,
    session_factory: sessionmaker[Session],
) -> None:
    registered = client.post("/api/auth/register", json=registration_payload())
    assert registered.status_code == 201, registered.json()
    token = registered.json()["access_token"]
    assert registered.json()["user"]["role"] == "PLAYER"
    assert registered.json()["user"]["phone_number"] == "13800138000"
    assert registered.json()["user"]["qq_number"] is None

    with session_factory() as db:
        user = db.scalar(select(User).where(User.phone_number == "13800138000"))
        assert user is not None
        assert user.password_hash != "secure123"
        assert verify_password("secure123", user.password_hash)

    profile = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert profile.status_code == 200
    assert profile.json()["nickname"] == "海盐栗子"

    changed = client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "secure123",
            "new_password": "654321",
            "confirm_password": "654321",
        },
    )
    assert changed.status_code == 204
    assert client.post(
        "/api/auth/login",
        json={"identifier": "13800138000", "password": "secure123"},
    ).status_code == 401
    assert client.post(
        "/api/auth/login",
        json={"identifier": "13800138000", "password": "654321"},
    ).status_code == 200


def test_register_and_login_by_qq_number(client) -> None:
    registered = client.post(
        "/api/auth/register",
        json=registration_payload(
            identifier_type="QQ",
            identifier="123456789",
            nickname="栗子选手",
        ),
    )

    assert registered.status_code == 201, registered.json()
    assert registered.json()["user"]["phone_number"] is None
    assert registered.json()["user"]["qq_number"] == "123456789"
    login = client.post(
        "/api/auth/login",
        json={"identifier": "123456789", "password": "secure123"},
    )
    assert login.status_code == 200


def test_duplicate_identifiers_and_nickname_are_rejected(client) -> None:
    assert client.post("/api/auth/register", json=registration_payload()).status_code == 201

    duplicate_phone = client.post(
        "/api/auth/register",
        json=registration_payload(nickname="另一位玩家"),
    )
    cross_type_duplicate = client.post(
        "/api/auth/register",
        json=registration_payload(
            identifier_type="QQ",
            identifier="13800138000",
            nickname="第三位玩家",
        ),
    )
    duplicate_nickname = client.post(
        "/api/auth/register",
        json=registration_payload(
            identifier_type="QQ",
            identifier="987654321",
        ),
    )

    assert duplicate_phone.status_code == 409
    assert duplicate_phone.json()["code"] == "PHONE_NUMBER_EXISTS"
    assert cross_type_duplicate.status_code == 409
    assert cross_type_duplicate.json()["code"] == "QQ_NUMBER_EXISTS"
    assert duplicate_nickname.status_code == 409
    assert duplicate_nickname.json()["code"] == "NICKNAME_EXISTS"


def test_invalid_phone_registration_is_rejected(client) -> None:
    response = client.post(
        "/api/auth/register",
        json=registration_payload(identifier="12345678901"),
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_password_requires_at_least_six_characters(client) -> None:
    accepted = client.post(
        "/api/auth/register",
        json=registration_payload(password="123456", confirm_password="123456"),
    )
    rejected = client.post(
        "/api/auth/register",
        json=registration_payload(
            identifier_type="QQ",
            identifier="987654321",
            nickname="短密码测试",
            password="12345",
            confirm_password="12345",
        ),
    )

    assert accepted.status_code == 201, accepted.json()
    assert rejected.status_code == 422
    assert rejected.json()["code"] == "VALIDATION_ERROR"


def test_legacy_qq_account_can_still_login(client, make_user) -> None:
    make_user(qq_number="12345678", password="password123")

    response = client.post(
        "/api/auth/login",
        json={"identifier": "12345678", "password": "password123"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["qq_number"] == "12345678"


def test_unbound_qq_flow_never_creates_a_second_account(client, make_user, session_factory: sessionmaker[Session]) -> None:
    user, access_token = make_user()
    binding_token = create_token("openid-not-yet-bound", token_type="qq_binding", expires_minutes=10)

    before = None
    with session_factory() as db:
        before = db.scalar(select(func.count()).select_from(User))
    response = client.post(
        "/api/auth/qq/bind",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"binding_token": binding_token},
    )
    with session_factory() as db:
        after = db.scalar(select(func.count()).select_from(User))
        bound_user = db.get(User, user.id)

    assert response.status_code == 200
    assert response.json()["qq_bound"] is True
    assert before == after == 1
    assert bound_user.qq_openid == "openid-not-yet-bound"


def test_qq_oauth_reports_unconfigured_without_credentials(client) -> None:
    response = client.get("/api/auth/qq/status")
    assert response.status_code == 200
    assert response.json() == {"configured": False, "authorization_url": None, "state": None}
