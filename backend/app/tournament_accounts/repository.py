from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, joinedload

from app.registrations.models import Registration
from app.tournament_accounts.models import (
    AccountReplacementRequest,
    AccountReplacementStatus,
    AccountType,
    TournamentAccount,
    TournamentAccountStatus,
)
from app.tournaments.models import Tournament, TournamentStatus


class TournamentAccountRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def existing_digests(
        self,
        tournament_id: UUID,
        account_type: AccountType,
        digests: list[str],
    ) -> set[str]:
        if not digests:
            return set()
        return set(self.db.scalars(
            select(TournamentAccount.account_digest).where(
                TournamentAccount.tournament_id == tournament_id,
                TournamentAccount.account_type == account_type.value,
                TournamentAccount.account_digest.in_(digests),
            )
        ))

    def account(self, account_id: UUID, *, for_update: bool = False) -> TournamentAccount | None:
        statement = select(TournamentAccount).where(TournamentAccount.id == account_id)
        if for_update:
            statement = statement.with_for_update()
        return self.db.scalar(statement)

    def claimed_for_registration(
        self,
        registration_id: UUID,
        account_type: AccountType,
    ) -> TournamentAccount | None:
        return self.db.scalar(select(TournamentAccount).where(
            TournamentAccount.claimed_registration_id == registration_id,
            TournamentAccount.account_type == account_type.value,
            TournamentAccount.status == TournamentAccountStatus.CLAIMED.value,
        ))

    def reserved_for_registration(
        self,
        registration_id: UUID,
        account_type: AccountType,
    ) -> TournamentAccount | None:
        return self.db.scalar(select(TournamentAccount).where(
            TournamentAccount.claimed_registration_id == registration_id,
            TournamentAccount.account_type == account_type.value,
            TournamentAccount.status == TournamentAccountStatus.RESERVED.value,
        ))

    def claims_for_registration(self, registration_id: UUID) -> list[TournamentAccount]:
        return list(self.db.scalars(
            select(TournamentAccount)
            .where(
                TournamentAccount.claimed_registration_id == registration_id,
                TournamentAccount.status == TournamentAccountStatus.CLAIMED.value,
            )
            .order_by(TournamentAccount.account_type)
        ))

    def has_invalid_for_registration(self, registration_id: UUID, account_type: AccountType) -> bool:
        return self.db.scalar(select(TournamentAccount.id).where(
            TournamentAccount.claimed_registration_id == registration_id,
            TournamentAccount.account_type == account_type.value,
            TournamentAccount.status == TournamentAccountStatus.INVALID.value,
        ).limit(1)) is not None

    def next_available(
        self,
        tournament_id: UUID,
        account_type: AccountType,
    ) -> TournamentAccount | None:
        return self.db.scalar(
            select(TournamentAccount)
            .where(
                TournamentAccount.tournament_id == tournament_id,
                TournamentAccount.account_type == account_type.value,
                TournamentAccount.status == TournamentAccountStatus.AVAILABLE.value,
            )
            .order_by(TournamentAccount.created_at, TournamentAccount.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )

    def available_count(self, tournament_id: UUID, account_type: AccountType) -> int:
        return int(self.db.scalar(
            select(func.count()).select_from(TournamentAccount).where(
                TournamentAccount.tournament_id == tournament_id,
                TournamentAccount.account_type == account_type.value,
                TournamentAccount.status == TournamentAccountStatus.AVAILABLE.value,
            )
        ) or 0)

    def carryover_candidates(
        self,
        target_tournament_id: UUID,
        owner_id: UUID,
        *,
        for_update: bool = False,
    ) -> list[TournamentAccount]:
        statement = (
            select(TournamentAccount)
            .join(Tournament, Tournament.id == TournamentAccount.tournament_id)
            .where(
                TournamentAccount.tournament_id != target_tournament_id,
                TournamentAccount.status == TournamentAccountStatus.AVAILABLE.value,
                Tournament.created_by_id == owner_id,
                Tournament.status.in_([
                    TournamentStatus.ENDED.value,
                    TournamentStatus.CANCELED.value,
                ]),
            )
            .order_by(
                TournamentAccount.account_type,
                TournamentAccount.created_at,
                TournamentAccount.id,
            )
        )
        if for_update:
            statement = statement.with_for_update(of=TournamentAccount)
        return list(self.db.scalars(statement))

    def list_for_admin(
        self,
        tournament_id: UUID,
        account_type: AccountType | None,
    ) -> list[TournamentAccount]:
        filters = [TournamentAccount.tournament_id == tournament_id]
        if account_type is not None:
            filters.append(TournamentAccount.account_type == account_type.value)
        status_priority = case(
            (TournamentAccount.status == TournamentAccountStatus.CLAIMED.value, 0),
            (TournamentAccount.status == TournamentAccountStatus.RESERVED.value, 1),
            (TournamentAccount.status == TournamentAccountStatus.AVAILABLE.value, 2),
            (TournamentAccount.status == TournamentAccountStatus.INVALID.value, 3),
            else_=4,
        )
        return list(self.db.scalars(
            select(TournamentAccount)
            .where(*filters)
            .options(joinedload(TournamentAccount.claimed_by))
            .order_by(TournamentAccount.account_type, status_priority, TournamentAccount.created_at)
        ))

    def summaries(self, tournament_id: UUID) -> dict[str, dict[str, int]]:
        rows = self.db.execute(
            select(TournamentAccount.account_type, TournamentAccount.status, func.count())
            .where(TournamentAccount.tournament_id == tournament_id)
            .group_by(TournamentAccount.account_type, TournamentAccount.status)
        ).all()
        result = {
            item.value: {
                "total": 0,
                "available": 0,
                "reserved": 0,
                "claimed": 0,
                "invalid": 0,
                "transferred": 0,
            }
            for item in AccountType
        }
        for account_type, status, count in rows:
            result[account_type]["total"] += int(count)
            result[account_type][status.lower()] = int(count)
        return result

    def replacement_request(
        self,
        request_id: UUID,
        *,
        for_update: bool = False,
    ) -> AccountReplacementRequest | None:
        statement = select(AccountReplacementRequest).where(AccountReplacementRequest.id == request_id)
        if for_update:
            statement = statement.with_for_update()
        return self.db.scalar(statement)

    def open_replacement_request(
        self,
        registration_id: UUID,
        account_type: AccountType,
    ) -> AccountReplacementRequest | None:
        return self.db.scalar(select(AccountReplacementRequest).where(
            AccountReplacementRequest.registration_id == registration_id,
            AccountReplacementRequest.account_type == account_type.value,
            AccountReplacementRequest.status.in_([
                AccountReplacementStatus.PENDING.value,
                AccountReplacementStatus.APPROVED.value,
            ]),
        ))

    def approved_replacement_request(
        self,
        registration_id: UUID,
        account_type: AccountType,
    ) -> AccountReplacementRequest | None:
        return self.db.scalar(select(AccountReplacementRequest).where(
            AccountReplacementRequest.registration_id == registration_id,
            AccountReplacementRequest.account_type == account_type.value,
            AccountReplacementRequest.status == AccountReplacementStatus.APPROVED.value,
        ))

    def replacement_requests_for_registration(
        self,
        registration_id: UUID,
    ) -> list[AccountReplacementRequest]:
        return list(self.db.scalars(
            select(AccountReplacementRequest)
            .where(AccountReplacementRequest.registration_id == registration_id)
            .order_by(AccountReplacementRequest.created_at.desc(), AccountReplacementRequest.id.desc())
        ))

    def replacement_requests_for_admin(self, tournament_id: UUID) -> list[AccountReplacementRequest]:
        status_priority = case(
            (AccountReplacementRequest.status == AccountReplacementStatus.PENDING.value, 0),
            (AccountReplacementRequest.status == AccountReplacementStatus.APPROVED.value, 1),
            else_=2,
        )
        return list(self.db.scalars(
            select(AccountReplacementRequest)
            .where(AccountReplacementRequest.tournament_id == tournament_id)
            .options(
                joinedload(AccountReplacementRequest.registration).joinedload(Registration.user),
                joinedload(AccountReplacementRequest.original_account),
                joinedload(AccountReplacementRequest.replacement_account),
            )
            .order_by(status_priority, AccountReplacementRequest.created_at.desc())
        ))
