from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    QqBindRequest,
    QqCallbackResponse,
    QqOAuthStatus,
    RegisterRequest,
    TokenResponse,
)
from app.auth.security import create_token
from app.auth.service import AuthService, QqOAuthService
from app.db.session import get_db
from app.users.models import User
from app.users.repository import UserRepository
from app.users.schemas import UserResponse, user_response

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    return AuthService(db).register(request)


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    return AuthService(db).login(request)


@router.get("/me", response_model=UserResponse)
def me(user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    return user_response(user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    request: ChangePasswordRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    AuthService(db).change_password(user, request)


@router.get("/qq/status", response_model=QqOAuthStatus)
def qq_status() -> QqOAuthStatus:
    service = QqOAuthService()
    if not service.is_configured():
        return QqOAuthStatus(configured=False)
    url, state_token = service.authorization()
    return QqOAuthStatus(configured=True, authorization_url=url, state=state_token)


@router.get("/qq/callback", response_model=QqCallbackResponse)
async def qq_callback(
    code: Annotated[str, Query(min_length=1)],
    state_token: Annotated[str, Query(alias="state", min_length=1)],
    db: Annotated[Session, Depends(get_db)],
) -> QqCallbackResponse:
    openid = await QqOAuthService().exchange_openid(code, state_token)
    user = UserRepository(db).get_by_qq_openid(openid)
    if user is None:
        return QqCallbackResponse(
            requires_binding=True,
            binding_token=create_token(openid, token_type="qq_binding", expires_minutes=10),
        )
    token = AuthService(db)._token_response(user)
    return QqCallbackResponse(
        requires_binding=False,
        access_token=token.access_token,
        user=token.user,
    )


@router.post("/qq/bind", response_model=UserResponse)
def bind_qq(
    request: QqBindRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    return user_response(AuthService(db).bind_qq(user, request.binding_token))
