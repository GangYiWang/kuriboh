from app.core.config import Settings


def test_standard_postgresql_url_uses_psycopg_driver() -> None:
    settings = Settings(database_url="postgresql://user:password@db.example:5432/app")

    assert settings.database_url == "postgresql+psycopg://user:password@db.example:5432/app"


def test_explicit_sqlalchemy_driver_is_preserved() -> None:
    url = "postgresql+psycopg://user:password@db.example:5432/app"

    assert Settings(database_url=url).database_url == url
