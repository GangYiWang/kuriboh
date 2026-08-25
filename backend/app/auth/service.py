import json
import re
from urllib.parse import parse_qs, urlencode

import httpx
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.roles import Role
from app.auth.schemas import ChangePasswordRequest, LoginRequest, RegisterRequest, TokenResponse
from app.auth.security import DUMMY_PASSWORD_HASH, create_token, decode_token, hash_password, verify_password
from app.core.config import get_settings
from app.core.errors import AppError
from app.users.models import User
from app.users.repository import UserRepository
from app.users.schemas import user_response


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    def register(self, request: RegisterRequest) -> TokenResponse:
        conflict = self.users.find_registration_conflict(request.identifier, request.nickname)
        if conflict is not None:
            if request.identifier_type == "PHONE" and (
                conflict.phone_number == request.identifier or conflict.qq_number == request.identifier
            ):
                raise AppError("PHONE_NUMBER_EXISTS", "该手机号已经注册", status_code=409)
            if conflict.phone_number == request.identifier or conflict.qq_number == request.identifier:
                raise AppError("QQ_NUMBER_EXISTS", "该 QQ 号已经注册", status_code=409)
            raise AppError("NICKNAME_EXISTS", "该昵称已经使用", status_code=409)

        user = User(
            phone_number=request.identifier if request.identifier_type == "PHONE" else None,
            qq_number=request.identifier if request.identifier_type == "QQ" else None,
            nickname=request.nickname,
            password_hash=hash_password(request.password),
            role=Role.PLAYER.value,
        )
        try:
            self.users.add(user)
            self.db.commit()
            self.db.refresh(user)
        except IntegrityError as exc:
            self.db.rollback()
            raise AppError("ACCOUNT_EXISTS", "手机号、QQ 号或昵称已经使用", status_code=409) from exc
        return self._token_response(user)

    def login(self, request: LoginRequest) -> TokenResponse:
        user = self.users.get_by_identifier(request.identifier)
        password_hash = user.password_hash if user else DUMMY_PASSWORD_HASH
        valid = verify_password(request.password, password_hash)
        if user is None or not valid:
            raise AppError("INVALID_CREDENTIALS", "手机号、QQ 号或密码错误", status_code=401)
        return self._token_response(user)

    def change_password(self, user: User, request: ChangePasswordRequest) -> None:
        if not verify_password(request.current_password, user.password_hash):
            raise AppError("INVALID_CURRENT_PASSWORD", "当前密码错误", status_code=400)
        user.password_hash = hash_password(request.new_password)
        self.db.commit()

    def bind_qq(self, user: User, binding_token: str) -> User:
        payload = decode_token(binding_token, expected_type="qq_binding")
        openid = payload["sub"]
        bound = self.users.get_by_qq_openid(openid)
        if bound is not None and bound.id != user.id:
            raise AppError("QQ_ALREADY_BOUND", "该 QQ 授权已绑定其他账号", status_code=409)
        if user.qq_openid is not None and user.qq_openid != openid:
            raise AppError("ACCOUNT_ALREADY_BOUND", "当前账号已绑定其他 QQ 授权", status_code=409)
        user.qq_openid = openid
        try:
            self.db.commit()
            self.db.refresh(user)
        except IntegrityError as exc:
            self.db.rollback()
            raise AppError("QQ_ALREADY_BOUND", "该 QQ 授权已绑定其他账号", status_code=409) from exc
        return user

    def _token_response(self, user: User) -> TokenResponse:
        return TokenResponse(access_token=create_token(str(user.id)), user=user_response(user))


class QqOAuthService:
    authorize_url = "https://graph.qq.com/oauth2.0/authorize"
    token_url = "https://graph.qq.com/oauth2.0/token"
    openid_url = "https://graph.qq.com/oauth2.0/me"

    @staticmethod
    def is_configured() -> bool:
        settings = get_settings()
        return bool(settings.qq_oauth_app_id and settings.qq_oauth_app_key and settings.qq_oauth_redirect_uri)

    def authorization(self) -> tuple[str, str]:
        settings = get_settings()
        if not self.is_configured():
            raise AppError("QQ_OAUTH_NOT_CONFIGURED", "QQ 登录尚未配置", status_code=503)
        state = create_token("qq_oauth", token_type="qq_state", expires_minutes=10)
        query = urlencode({
            "response_type": "code",
            "client_id": settings.qq_oauth_app_id,
            "redirect_uri": settings.qq_oauth_redirect_uri,
            "state": state,
        })
        return f"{self.authorize_url}?{query}", state

    async def exchange_openid(self, code: str, state: str) -> str:
        decode_token(state, expected_type="qq_state")
        settings = get_settings()
        if not self.is_configured():
            raise AppError("QQ_OAUTH_NOT_CONFIGURED", "QQ 登录尚未配置", status_code=503)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                token_response = await client.get(self.token_url, params={
                    "grant_type": "authorization_code",
                    "client_id": settings.qq_oauth_app_id,
                    "client_secret": settings.qq_oauth_app_key,
                    "code": code,
                    "redirect_uri": settings.qq_oauth_redirect_uri,
                    "fmt": "json",
                })
                token_response.raise_for_status()
                try:
                    token_data = token_response.json()
                except json.JSONDecodeError:
                    token_data = {key: values[0] for key, values in parse_qs(token_response.text).items()}
                access_token = token_data.get("access_token")
                if not access_token:
                    raise AppError("QQ_OAUTH_FAILED", "QQ 授权失败", status_code=400)
                openid_response = await client.get(self.openid_url, params={
                    "access_token": access_token,
                    "fmt": "json",
                })
                openid_response.raise_for_status()
                try:
                    openid_data = openid_response.json()
                except json.JSONDecodeError:
                    match = re.search(r"callback\(\s*(\{.*\})\s*\);", openid_response.text)
                    if not match:
                        raise AppError("QQ_OAUTH_FAILED", "QQ 身份响应无法识别", status_code=400)
                    openid_data = json.loads(match.group(1))
                openid = openid_data.get("openid")
                if not openid:
                    raise AppError("QQ_OAUTH_FAILED", "QQ 身份获取失败", status_code=400)
                return str(openid)
        except httpx.HTTPError as exc:
            raise AppError("QQ_OAUTH_UNAVAILABLE", "QQ 授权服务暂时不可用", status_code=502) from exc
