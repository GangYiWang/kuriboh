from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.users.models import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, user_id: UUID) -> User | None:
        return self.db.get(User, user_id)

    def get_by_identifier(self, identifier: str) -> User | None:
        return self.db.scalar(
            select(User)
            .where(or_(User.phone_number == identifier, User.qq_number == identifier))
            .limit(1)
        )

    def get_by_qq_number(self, qq_number: str) -> User | None:
        return self.db.scalar(select(User).where(User.qq_number == qq_number))

    def get_by_qq_openid(self, openid: str) -> User | None:
        return self.db.scalar(select(User).where(User.qq_openid == openid))

    def find_registration_conflict(self, identifier: str, nickname: str) -> User | None:
        return self.db.scalar(
            select(User).where(or_(
                User.phone_number == identifier,
                User.qq_number == identifier,
                User.nickname == nickname,
            ))
        )

    def add(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user
