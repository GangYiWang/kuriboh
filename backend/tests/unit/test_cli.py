import subprocess
import sys
from uuid import uuid4

import pytest

from app.auth.security import verify_password
from app.cli import reset_user_password
from app.users.models import User


def test_cli_loads_complete_model_registry() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.cli import User; from sqlalchemy.orm import configure_mappers; configure_mappers()",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_reset_user_password_uses_fixed_temporary_password(
    make_user, session_factory, monkeypatch, capsys
) -> None:
    user, _ = make_user(qq_number="86000001", nickname="密码重置用户", password="old-password")
    monkeypatch.setattr("app.cli.SessionLocal", session_factory)

    reset_user_password(user.id)

    with session_factory() as db:
        updated = db.get(User, user.id)
        assert updated is not None
        assert verify_password("123456", updated.password_hash)
        assert not verify_password("old-password", updated.password_hash)
    output = capsys.readouterr().out
    assert str(user.id) in output
    assert "123456" in output


def test_reset_user_password_rejects_unknown_user(session_factory, monkeypatch) -> None:
    monkeypatch.setattr("app.cli.SessionLocal", session_factory)

    with pytest.raises(SystemExit, match="用户不存在"):
        reset_user_password(uuid4())
