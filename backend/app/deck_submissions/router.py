from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentPrincipal, get_current_principal
from app.db.session import get_db
from app.core.config import get_settings
from app.deck_submissions.schemas import DeckReturnRequest, DeckSubmissionListResponse, DeckSubmissionResponse
from app.deck_submissions.service import DeckSubmissionService, deck_response
from app.tournaments.ownership import require_deck_submission_owner, require_tournament_owner


router = APIRouter(tags=["deck-submissions"])
admin_router = APIRouter(prefix="/admin", tags=["admin-deck-submissions"])
Authenticated = Annotated[CurrentPrincipal, Depends(get_current_principal)]


@router.get("/tournaments/{tournament_id}/deck-submission/me", response_model=DeckSubmissionResponse)
def my_deck_submission(tournament_id: UUID, principal: Authenticated, db: Annotated[Session, Depends(get_db)]):
    return deck_response(DeckSubmissionService(db).my_submission(tournament_id, principal.user_id))


@router.post("/tournaments/{tournament_id}/deck-submission", response_model=DeckSubmissionResponse)
async def upload_deck_submission(
    tournament_id: UUID,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
    image: Annotated[UploadFile, File()],
):
    content = await image.read(get_settings().upload_max_bytes + 1)
    return deck_response(DeckSubmissionService(db).upload(tournament_id, principal.user_id, content))


@admin_router.get("/tournaments/{tournament_id}/deck-submissions", response_model=DeckSubmissionListResponse)
def admin_deck_submissions(tournament_id: UUID, principal: Authenticated, db: Annotated[Session, Depends(get_db)]):
    require_tournament_owner(db, tournament_id, principal.user_id)
    return DeckSubmissionService(db).list_for_admin(tournament_id)


@admin_router.post("/deck-submissions/{submission_id}/approve", response_model=DeckSubmissionResponse)
def approve_deck_submission(submission_id: UUID, principal: Authenticated, db: Annotated[Session, Depends(get_db)]):
    require_deck_submission_owner(db, submission_id, principal.user_id)
    return deck_response(DeckSubmissionService(db).review(submission_id, "approve", None, principal.user_id))


@admin_router.post("/deck-submissions/{submission_id}/return", response_model=DeckSubmissionResponse)
def return_deck_submission(
    submission_id: UUID,
    request: DeckReturnRequest,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
):
    require_deck_submission_owner(db, submission_id, principal.user_id)
    return deck_response(DeckSubmissionService(db).review(submission_id, "return", request.reason, principal.user_id))
