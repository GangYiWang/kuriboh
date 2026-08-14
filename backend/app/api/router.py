from fastapi import APIRouter

from app.api.routes import admin_health, health
from app.auth.router import router as auth_router
from app.audit.router import router as audit_router
from app.content.router import admin_router as admin_content_router
from app.content.router import router as content_router
from app.deck_submissions.router import admin_router as admin_deck_router
from app.deck_submissions.router import router as deck_router
from app.playoffs.router import admin_router as admin_playoff_router
from app.playoffs.router import router as playoff_router
from app.reports.router import admin_router as admin_report_router
from app.reports.router import router as report_router
from app.swiss.router import admin_router as admin_swiss_router
from app.swiss.router import router as swiss_router
from app.tournaments.router import admin_router as admin_tournament_router
from app.tournaments.router import router as tournament_router
from app.messages.router import admin_router as admin_message_router
from app.messages.router import router as message_router

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(admin_health.router, prefix="/admin", tags=["admin"])
api_router.include_router(audit_router)
api_router.include_router(auth_router)
api_router.include_router(content_router)
api_router.include_router(admin_content_router)
api_router.include_router(deck_router)
api_router.include_router(admin_deck_router)
api_router.include_router(swiss_router)
api_router.include_router(admin_swiss_router)
api_router.include_router(playoff_router)
api_router.include_router(admin_playoff_router)
api_router.include_router(report_router)
api_router.include_router(admin_report_router)
api_router.include_router(message_router)
api_router.include_router(admin_message_router)
api_router.include_router(tournament_router)
api_router.include_router(admin_tournament_router)
