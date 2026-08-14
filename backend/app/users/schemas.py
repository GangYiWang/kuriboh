from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.auth.roles import Role


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    qq_number: str
    nickname: str
    role: Role
    qq_bound: bool
    created_at: datetime


def user_response(user: object) -> UserResponse:
    return UserResponse(
        id=user.id,
        qq_number=user.qq_number,
        nickname=user.nickname,
        role=Role(user.role),
        qq_bound=user.qq_openid is not None,
        created_at=user.created_at,
    )
