from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.users.schemas import UserResponse


class RegisterRequest(BaseModel):
    identifier_type: Literal["PHONE", "QQ"]
    identifier: str = Field(min_length=5, max_length=20, pattern=r"^[1-9][0-9]+$")
    nickname: str = Field(min_length=2, max_length=30)
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @field_validator("nickname")
    @classmethod
    def normalize_nickname(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("昵称不能为空")
        return normalized

    @model_validator(mode="after")
    def identifier_matches_type(self) -> "RegisterRequest":
        if self.identifier_type == "PHONE" and not (
            len(self.identifier) == 11
            and self.identifier.startswith("1")
            and self.identifier[1] in "3456789"
        ):
            raise ValueError("请输入有效的中国大陆手机号")
        return self

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterRequest":
        if self.password != self.confirm_password:
            raise ValueError("两次输入的密码不一致")
        return self


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=5, max_length=20, pattern=r"^[1-9][0-9]+$")
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def passwords_match(self) -> "ChangePasswordRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("两次输入的新密码不一致")
        if self.new_password == self.current_password:
            raise ValueError("新密码不能与当前密码相同")
        return self


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class QqOAuthStatus(BaseModel):
    configured: bool
    authorization_url: str | None = None
    state: str | None = None


class QqCallbackResponse(BaseModel):
    requires_binding: bool
    access_token: str | None = None
    binding_token: str | None = None
    token_type: str = "bearer"
    user: UserResponse | None = None


class QqBindRequest(BaseModel):
    binding_token: str
