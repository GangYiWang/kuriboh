"""Create retained local player accounts 40000009 through 40000022."""

from pathlib import Path
import sys

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth.roles import Role  # noqa: E402
from app.auth.security import hash_password  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.db import models as _models  # noqa: E402,F401
from app.db.session import SessionLocal  # noqa: E402
from app.users.models import User  # noqa: E402

PASSWORD = "12345678"
PLAYER_NUMBERS = range(9, 23)


def main() -> None:
    if get_settings().environment != "development":
        raise RuntimeError("仅允许在 development 环境创建测试账号")

    created: list[str] = []
    existing: list[str] = []
    with SessionLocal() as db:
        for number in PLAYER_NUMBERS:
            qq_number = f"400000{number:02d}"
            nickname = f"Phase5测试选手{number:02d}"
            account = db.scalar(select(User).where(User.qq_number == qq_number))
            if account is not None:
                existing.append(qq_number)
                continue
            nickname_owner = db.scalar(select(User).where(User.nickname == nickname))
            if nickname_owner is not None:
                raise RuntimeError(f"昵称已被其他账号占用：{nickname}")
            db.add(User(
                qq_number=qq_number,
                nickname=nickname,
                password_hash=hash_password(PASSWORD),
                role=Role.USER.value,
            ))
            created.append(qq_number)
        db.commit()

    print(f"created={','.join(created) or 'none'}")
    print(f"existing={','.join(existing) or 'none'}")
    print(f"password={PASSWORD}")


if __name__ == "__main__":
    main()
