from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import get_settings
from app.core.errors import AppError

password_hasher = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = password_hasher.hash("not-a-real-user-password")


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def create_token(subject: str, *, token_type: str = "access", expires_minutes: int | None = None, **claims: Any) -> str:
    settings = get_settings()
    minutes = expires_minutes or settings.access_token_expire_minutes
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
        **claims,
    }
    return jwt.encode(payload, settings.auth_secret_key, algorithm="HS256")


def decode_token(token: str, *, expected_type: str = "access") -> dict[str, Any]:
    try:
        payload = jwt.decode(token, get_settings().auth_secret_key, algorithms=["HS256"])
    except InvalidTokenError as exc:
        raise AppError("INVALID_TOKEN", "登录凭证无效或已过期", status_code=401) from exc
    if payload.get("type") != expected_type or not payload.get("sub"):
        raise AppError("INVALID_TOKEN", "登录凭证类型无效", status_code=401)
    return payload
