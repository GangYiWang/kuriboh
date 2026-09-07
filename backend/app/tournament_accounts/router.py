from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentPrincipal, get_current_principal
from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import get_db
from app.tournament_accounts.models import AccountType
from app.tournament_accounts.schemas import (
    AccountCredentialResponse,
    AccountImportResponse,
    AccountReplacementReasonRequest,
    AccountReplacementRequestResponse,
    AdminAccountReplacementRequestListResponse,
    AdminAccountReplacementRequestResponse,
    AdminTournamentAccountListResponse,
    MyTournamentAccountsResponse,
)
from app.tournament_accounts.service import TournamentAccountService
from app.tournaments.ownership import require_tournament_owner


router = APIRouter(tags=["tournament-accounts"])
admin_router = APIRouter(prefix="/admin", tags=["admin-tournament-accounts"])
Authenticated = Annotated[CurrentPrincipal, Depends(get_current_principal)]


@router.get("/tournaments/{tournament_id}/accounts/me", response_model=MyTournamentAccountsResponse)
def my_tournament_accounts(
    tournament_id: UUID,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
    response: Response,
) -> MyTournamentAccountsResponse:
    response.headers["Cache-Control"] = "no-store"
    return TournamentAccountService(db).my_accounts(tournament_id, principal.user_id)


@router.post(
    "/tournaments/{tournament_id}/accounts/{account_type}/claim",
    response_model=AccountCredentialResponse,
)
def claim_tournament_account(
    tournament_id: UUID,
    account_type: AccountType,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
    response: Response,
) -> AccountCredentialResponse:
    response.headers["Cache-Control"] = "no-store"
    return TournamentAccountService(db).claim(tournament_id, account_type, principal.user_id)


@router.post(
    "/tournaments/{tournament_id}/accounts/{account_type}/replacement-requests",
    response_model=AccountReplacementRequestResponse,
)
def request_account_replacement(
    tournament_id: UUID,
    account_type: AccountType,
    request: AccountReplacementReasonRequest,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> AccountReplacementRequestResponse:
    return TournamentAccountService(db).request_replacement(
        tournament_id,
        account_type,
        request.reason,
        principal.user_id,
    )


@admin_router.get(
    "/tournaments/{tournament_id}/accounts",
    response_model=AdminTournamentAccountListResponse,
)
def admin_tournament_accounts(
    tournament_id: UUID,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
    response: Response,
    account_type: Annotated[AccountType | None, Query(alias="type")] = None,
) -> AdminTournamentAccountListResponse:
    require_tournament_owner(db, tournament_id, principal.user_id)
    response.headers["Cache-Control"] = "no-store"
    return TournamentAccountService(db).list_for_admin(tournament_id, account_type)


@admin_router.get(
    "/tournaments/{tournament_id}/account-replacement-requests",
    response_model=AdminAccountReplacementRequestListResponse,
)
def admin_account_replacement_requests(
    tournament_id: UUID,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> AdminAccountReplacementRequestListResponse:
    require_tournament_owner(db, tournament_id, principal.user_id)
    return TournamentAccountService(db).replacement_requests_for_admin(tournament_id)


@admin_router.post(
    "/tournaments/{tournament_id}/account-replacement-requests/{request_id}/approve",
    response_model=AdminAccountReplacementRequestResponse,
)
def approve_account_replacement(
    tournament_id: UUID,
    request_id: UUID,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> AdminAccountReplacementRequestResponse:
    require_tournament_owner(db, tournament_id, principal.user_id)
    return TournamentAccountService(db).approve_replacement(
        tournament_id,
        request_id,
        principal.user_id,
    )


@admin_router.post(
    "/tournaments/{tournament_id}/account-replacement-requests/{request_id}/reject",
    response_model=AdminAccountReplacementRequestResponse,
)
def reject_account_replacement(
    tournament_id: UUID,
    request_id: UUID,
    request: AccountReplacementReasonRequest,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
) -> AdminAccountReplacementRequestResponse:
    require_tournament_owner(db, tournament_id, principal.user_id)
    return TournamentAccountService(db).reject_replacement(
        tournament_id,
        request_id,
        request.reason,
        principal.user_id,
    )


@admin_router.post(
    "/tournaments/{tournament_id}/accounts/{account_type}/imports",
    response_model=AccountImportResponse,
)
async def import_tournament_accounts(
    tournament_id: UUID,
    account_type: AccountType,
    principal: Authenticated,
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File()],
) -> AccountImportResponse:
    require_tournament_owner(db, tournament_id, principal.user_id)
    filename = file.filename or ""
    if not filename.lower().endswith(".txt"):
        raise AppError("ACCOUNT_IMPORT_FILE_TYPE_INVALID", "请选择 .txt 账号文件")
    limit = get_settings().account_import_max_bytes
    content = await file.read(limit + 1)
    if len(content) > limit:
        raise AppError(
            "ACCOUNT_IMPORT_FILE_TOO_LARGE",
            f"账号文件不能超过 {limit // 1024} KB",
            status_code=413,
        )
    return TournamentAccountService(db).import_accounts(
        tournament_id,
        account_type,
        filename,
        content,
        principal.user_id,
    )
