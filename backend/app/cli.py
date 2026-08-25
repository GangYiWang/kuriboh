import argparse
from getpass import getpass
import re
from typing import Literal

from sqlalchemy.exc import IntegrityError

from app.auth.roles import Role
from app.auth.security import hash_password
from app.db.models import User
from app.db.session import SessionLocal
from app.users.repository import UserRepository


IdentifierType = Literal["PHONE", "QQ"]


def create_admin(identifier_type: IdentifierType, identifier: str, nickname: str, password: str | None) -> None:
    if identifier_type == "PHONE" and re.fullmatch(r"1[3-9][0-9]{9}", identifier) is None:
        raise SystemExit("请输入有效的中国大陆手机号")
    if identifier_type == "QQ" and re.fullmatch(r"[1-9][0-9]{4,19}", identifier) is None:
        raise SystemExit("QQ 号必须是 5～20 位数字且不能以 0 开头")
    chosen_password = password or getpass("管理员密码：")
    if len(chosen_password) < 8:
        raise SystemExit("密码至少需要 8 个字符")
    with SessionLocal() as db:
        repository = UserRepository(db)
        existing = repository.find_registration_conflict(identifier, nickname)
        if existing is not None:
            raise SystemExit("手机号、QQ 号或昵称已经存在")
        user = User(
            phone_number=identifier if identifier_type == "PHONE" else None,
            qq_number=identifier if identifier_type == "QQ" else None,
            nickname=nickname.strip(),
            password_hash=hash_password(chosen_password),
            role=Role.TOURNAMENT_ADMIN.value,
        )
        try:
            repository.add(user)
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise SystemExit("手机号、QQ 号或昵称已经存在") from exc
        print(f"已创建管理员：{user.nickname} ({identifier})")


def main() -> None:
    parser = argparse.ArgumentParser(description="栗子杯后台管理命令")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create_admin_parser = subparsers.add_parser("create-admin", help="创建初始赛事管理员")
    identifier_group = create_admin_parser.add_mutually_exclusive_group(required=True)
    identifier_group.add_argument("--phone", dest="phone_number")
    identifier_group.add_argument("--qq", dest="qq_number")
    create_admin_parser.add_argument("--nickname", required=True)
    create_admin_parser.add_argument("--password", help="省略时安全地交互输入")
    args = parser.parse_args()
    if args.command == "create-admin":
        identifier_type: IdentifierType = "PHONE" if args.phone_number else "QQ"
        create_admin(
            identifier_type,
            args.phone_number or args.qq_number,
            args.nickname,
            args.password,
        )


if __name__ == "__main__":
    main()
