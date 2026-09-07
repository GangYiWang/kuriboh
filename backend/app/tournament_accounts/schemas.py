from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.tournament_accounts.models import AccountReplacementStatus, AccountType, TournamentAccountStatus


class AccountCredentialResponse(BaseModel):
    account_type: AccountType
    account: str
    password: str
    claimed_at: datetime


class MyTournamentAccountsResponse(BaseModel):
    items: list[AccountCredentialResponse]
    replacement_requests: list["AccountReplacementRequestResponse"]


class AccountReplacementReasonRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("原因不能为空")
        return normalized


class AccountReplacementRequestResponse(BaseModel):
    id: UUID
    account_type: AccountType
    status: AccountReplacementStatus
    reason: str
    rejection_reason: str | None
    created_at: datetime
    reviewed_at: datetime | None
    completed_at: datetime | None


class AdminAccountReplacementRequestResponse(AccountReplacementRequestResponse):
    user_id: UUID
    nickname: str
    original_account: str
    replacement_account: str | None


class AdminAccountReplacementRequestListResponse(BaseModel):
    items: list[AdminAccountReplacementRequestResponse]
    total: int
    pending_count: int


class AccountInventorySummary(BaseModel):
    account_type: AccountType
    total: int
    available: int
    reserved: int
    claimed: int
    invalid: int


class AdminTournamentAccountResponse(BaseModel):
    id: UUID
    account_type: AccountType
    account: str
    status: TournamentAccountStatus
    claimed_by_user_id: UUID | None
    claimed_by_nickname: str | None
    claimed_at: datetime | None
    created_at: datetime


class AdminTournamentAccountListResponse(BaseModel):
    items: list[AdminTournamentAccountResponse]
    summaries: list[AccountInventorySummary]
    total: int


class AccountImportResponse(BaseModel):
    batch_id: UUID
    account_type: AccountType
    imported_count: int
    available_count: int
