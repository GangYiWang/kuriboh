from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "栗子杯 API"
    app_version: str = "0.1.0"
    environment: str = "development"
    api_prefix: str = "/api"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://lizibei:lizibei@127.0.0.1:5432/lizibei"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])
    auth_secret_key: str = "development-only-change-this-secret"
    access_token_expire_minutes: int = 60 * 24
    qq_oauth_app_id: str | None = None
    qq_oauth_app_key: str | None = None
    qq_oauth_redirect_uri: str | None = None
    upload_dir: Path = Path("uploads")
    upload_max_bytes: int = 5 * 1024 * 1024

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        """Accept conventional PostgreSQL URLs while using the installed psycopg v3 driver."""
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
