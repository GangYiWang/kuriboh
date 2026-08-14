from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: str
    service: str
    database: str
    version: str


@router.get("/health", response_model=HealthResponse)
def health_check(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    db.execute(text("SELECT 1"))
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        database="ok",
        version=settings.app_version,
    )

