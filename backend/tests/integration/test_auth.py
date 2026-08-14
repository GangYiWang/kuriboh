from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.auth.security import create_token, verify_password
from app.users.models import User


def registration_payload(**overrides: str) -> dict[str, str]:
    payload = {
        "qq_number": "123456789",
        "nickname": "海盐栗子",
        "password": "secure123",
        "confirm_password": "secure123",
    }
    payload.update(overrides)
    return payload


def test_register_login_profile_and_change_password(client, session_factory: sessionmaker[Session]) -> None:
    registered = client.post("/api/auth/register", json=registration_payload())
    assert registered.status_code == 201
    token = registered.json()["access_token"]
    assert registered.json()["user"]["role"] == "PLAYER"

    with session_factory() as db:
        user = db.scalar(select(User).where(User.qq_number == "123456789"))
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
            "new_password": "new-secure123",
            "confirm_password": "new-secure123",
        },
    )
    assert changed.status_code == 204
    assert client.post("/api/auth/login", json={"qq_number": "123456789", "password": "secure123"}).status_code == 401
    assert client.post("/api/auth/login", json={"qq_number": "123456789", "password": "new-secure123"}).status_code == 200


def test_duplicate_qq_number_and_nickname_are_rejected(client) -> None:
    assert client.post("/api/auth/register", json=registration_payload()).status_code == 201

    duplicate_qq = client.post(
        "/api/auth/register",
        json=registration_payload(nickname="另一位玩家"),
    )
    duplicate_nickname = client.post(
        "/api/auth/register",
        json=registration_payload(qq_number="987654321"),
    )

    assert duplicate_qq.status_code == 409
    assert duplicate_qq.json()["code"] == "QQ_NUMBER_EXISTS"
    assert duplicate_nickname.status_code == 409
    assert duplicate_nickname.json()["code"] == "NICKNAME_EXISTS"


def test_login_accepts_short_development_qq_number(client, make_user) -> None:
    make_user(qq_number="111", password="123")

    response = client.post("/api/auth/login", json={"qq_number": "111", "password": "123"})

    assert response.status_code == 200
    assert response.json()["user"]["role"] == "PLAYER"


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
