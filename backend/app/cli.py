import argparse
from getpass import getpass
import re
from typing import Literal
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.auth.roles import Role
from app.auth.security import hash_password
from app.db.models import User
from app.db.session import SessionLocal
from app.users.repository import UserRepository


IdentifierType = Literal["PHONE", "QQ"]
DEFAULT_RESET_PASSWORD = "123456"


def create_admin(identifier_type: IdentifierType, identifier: str, nickname: str, password: str | None) -> None:
    if identifier_type == "PHONE" and re.fullmatch(r"1[3-9][0-9]{9}", identifier) is None:
        raise SystemExit("请输入有效的中国大陆手机号")
    if identifier_type == "QQ" and re.fullmatch(r"[1-9][0-9]{4,19}", identifier) is None:
        raise SystemExit("QQ 号必须是 5～20 位数字且不能以 0 开头")
    chosen_password = password or getpass("管理员密码：")
    if len(chosen_password) < 6:
        raise SystemExit("密码至少需要 6 个字符")
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
            role=Role.PLATFORM_ADMIN.value,
        )
        try:
            repository.add(user)
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise SystemExit("手机号、QQ 号或昵称已经存在") from exc
        print(f"已创建平台管理员：{user.nickname} ({identifier})")


def reset_user_password(user_id: UUID) -> None:
    with SessionLocal() as db:
        user = UserRepository(db).get(user_id)
        if user is None:
            raise SystemExit(f"用户不存在：{user_id}")
        user.password_hash = hash_password(DEFAULT_RESET_PASSWORD)
        db.commit()
        print(f"已将用户 {user.nickname} ({user.id}) 的密码重置为临时密码 {DEFAULT_RESET_PASSWORD}")


def main() -> None:
    parser = argparse.ArgumentParser(description="栗子杯后台管理命令")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create_admin_parser = subparsers.add_parser("create-admin", help="创建初始平台管理员")
    identifier_group = create_admin_parser.add_mutually_exclusive_group(required=True)
    identifier_group.add_argument("--phone", dest="phone_number")
    identifier_group.add_argument("--qq", dest="qq_number")
    create_admin_parser.add_argument("--nickname", required=True)
    create_admin_parser.add_argument("--password", help="省略时安全地交互输入")
    reset_password_parser = subparsers.add_parser(
        "reset-password",
        help=f"按用户 ID 将密码重置为临时密码 {DEFAULT_RESET_PASSWORD}",
    )
    reset_password_parser.add_argument("--user-id", type=UUID, required=True)
    args = parser.parse_args()
    if args.command == "create-admin":
        identifier_type: IdentifierType = "PHONE" if args.phone_number else "QQ"
        create_admin(
            identifier_type,
            args.phone_number or args.qq_number,
            args.nickname,
            args.password,
        )
    elif args.command == "reset-password":
        reset_user_password(args.user_id)


if __name__ == "__main__":
    main()
