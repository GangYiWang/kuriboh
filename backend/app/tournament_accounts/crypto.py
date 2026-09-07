import base64
import hashlib
import hmac

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings
from app.core.errors import AppError


class CredentialCipher:
    def __init__(self, root_secret: str | None = None) -> None:
        configured_secret = (root_secret or get_settings().auth_secret_key).encode("utf-8")
        encryption_key = hmac.new(
            configured_secret,
            b"kuriboh:tournament-accounts:encryption:v1",
            hashlib.sha256,
        ).digest()
        self._fernet = Fernet(base64.urlsafe_b64encode(encryption_key))
        self._digest_key = hmac.new(
            configured_secret,
            b"kuriboh:tournament-accounts:deduplication:v1",
            hashlib.sha256,
        ).digest()

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode("utf-8")).decode("ascii")

    def decrypt(self, value: str) -> str:
        try:
            return self._fernet.decrypt(value.encode("ascii")).decode("utf-8")
        except (InvalidToken, UnicodeDecodeError, ValueError) as exc:
            raise AppError(
                "ACCOUNT_CREDENTIAL_DECRYPTION_FAILED",
                "赛事账号数据无法读取，请联系平台管理员",
                status_code=500,
            ) from exc

    def account_digest(self, account: str) -> str:
        return hmac.new(self._digest_key, account.encode("utf-8"), hashlib.sha256).hexdigest()
