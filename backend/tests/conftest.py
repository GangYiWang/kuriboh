from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.roles import Role
from app.auth.security import create_token, hash_password
from app.core.config import get_settings
from app.db.session import get_db
from app.db.base import Base
from app.db import models  # noqa: F401
from app.main import app
from app.users.models import User


@pytest.fixture
def test_engine() -> Generator[Engine, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def session_factory(test_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def client(session_factory: sessionmaker[Session], tmp_path: Path) -> Generator[TestClient, None, None]:
    settings = get_settings()
    previous_upload_dir = settings.upload_dir
    settings.upload_dir = tmp_path / "uploads"

    def override_get_db() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    settings.upload_dir = previous_upload_dir


@pytest.fixture
def make_user(session_factory: sessionmaker[Session]):
    def factory(
        *,
        qq_number: str | None = "12345678",
        phone_number: str | None = None,
        nickname: str = "测试玩家",
        password: str = "password123",
        role: Role = Role.PLAYER,
        qq_openid: str | None = None,
    ) -> tuple[User, str]:
        with session_factory() as db:
            user = User(
                phone_number=phone_number,
                qq_number=qq_number,
                nickname=nickname,
                password_hash=hash_password(password),
                role=role.value,
                qq_openid=qq_openid,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            user_id = user.id
        return user, create_token(str(user_id))

    return factory
