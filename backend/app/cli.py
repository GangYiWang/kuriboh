import argparse
from getpass import getpass

from sqlalchemy.exc import IntegrityError

from app.auth.roles import Role
from app.auth.security import hash_password
from app.db.models import User
from app.db.session import SessionLocal
from app.users.repository import UserRepository


def create_admin(qq_number: str, nickname: str, password: str | None) -> None:
    chosen_password = password or getpass("管理员密码：")
    if len(chosen_password) < 8:
        raise SystemExit("密码至少需要 8 个字符")
    with SessionLocal() as db:
        repository = UserRepository(db)
        existing = repository.find_conflict(qq_number, nickname)
        if existing is not None:
            raise SystemExit("QQ 号或昵称已经存在")
        user = User(
            qq_number=qq_number,
            nickname=nickname.strip(),
            password_hash=hash_password(chosen_password),
            role=Role.TOURNAMENT_ADMIN.value,
        )
        try:
            repository.add(user)
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise SystemExit("QQ 号或昵称已经存在") from exc
        print(f"已创建管理员：{user.nickname} ({user.qq_number})")


def main() -> None:
    parser = argparse.ArgumentParser(description="栗子杯后台管理命令")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create_admin_parser = subparsers.add_parser("create-admin", help="创建初始赛事管理员")
    create_admin_parser.add_argument("--qq", required=True, dest="qq_number")
    create_admin_parser.add_argument("--nickname", required=True)
    create_admin_parser.add_argument("--password", help="省略时安全地交互输入")
    args = parser.parse_args()
    if args.command == "create-admin":
        create_admin(args.qq_number, args.nickname, args.password)


if __name__ == "__main__":
    main()
