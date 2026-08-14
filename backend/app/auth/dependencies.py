from dataclasses import dataclass
from typing import Annotated, Callable
from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.roles import Role
from app.auth.security import decode_token
from app.core.errors import AppError
from app.db.session import get_db
from app.users.models import User


@dataclass(frozen=True, slots=True)
class CurrentPrincipal:
    user_id: UUID
    role: Role
    nickname: str = ""


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if not token:
        raise AppError("AUTH_REQUIRED", "请先登录", status_code=401)
    payload = decode_token(token)
    try:
        user_id = UUID(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise AppError("INVALID_TOKEN", "登录凭证无效", status_code=401) from exc
    user = db.get(User, user_id)
    if user is None:
        raise AppError("INVALID_TOKEN", "登录账号不存在", status_code=401)
    return user


def get_current_principal(
    user: Annotated[User, Depends(get_current_user)],
) -> CurrentPrincipal:
    return CurrentPrincipal(user_id=user.id, role=Role(user.role), nickname=user.nickname)


def require_roles(*allowed_roles: Role) -> Callable[..., CurrentPrincipal]:
    def checker(
        principal: Annotated[CurrentPrincipal, Depends(get_current_principal)],
    ) -> CurrentPrincipal:
        if principal.role not in allowed_roles:
            raise AppError("FORBIDDEN", "没有执行此操作的权限", status_code=403)
        return principal

    return checker
