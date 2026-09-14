from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit.service import add_audit_log
from app.core.errors import AppError
from app.messages.models import MessageType
from app.messages.service import add_automatic_message
from app.registrations.models import RegistrationStatus
from app.registrations.repository import RegistrationRepository
from app.tournament_accounts.crypto import CredentialCipher
from app.tournament_accounts.models import (
    AccountImportBatch,
    AccountReplacementRequest,
    AccountReplacementStatus,
    AccountType,
    TournamentAccount,
    TournamentAccountStatus,
)
from app.tournament_accounts.repository import TournamentAccountRepository
from app.tournament_accounts.schemas import (
    AccountCredentialResponse,
    AccountImportResponse,
    AccountInventorySummary,
    AccountReplacementRequestResponse,
    AdminAccountReplacementRequestListResponse,
    AdminAccountReplacementRequestResponse,
    AdminTournamentAccountListResponse,
    AdminTournamentAccountResponse,
    MyTournamentAccountsResponse,
)
from app.tournaments.models import TournamentStatus
from app.tournaments.service import TournamentService


@dataclass(frozen=True)
class ParsedAccount:
    line_number: int
    account: str
    password: str
    digest: str


class TournamentAccountService:
    IMPORTABLE_STATUSES = {
        TournamentStatus.DRAFT.value,
        TournamentStatus.REGISTRATION.value,
        TournamentStatus.SWISS.value,
        TournamentStatus.ELIMINATION.value,
    }
    CLAIMABLE_STATUSES = {
        TournamentStatus.REGISTRATION.value,
        TournamentStatus.SWISS.value,
        TournamentStatus.ELIMINATION.value,
    }

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = TournamentAccountRepository(db)
        self.registrations = RegistrationRepository(db)
        self.cipher = CredentialCipher()

    def import_accounts(
        self,
        tournament_id: UUID,
        account_type: AccountType,
        filename: str,
        content: bytes,
        operator_id: UUID,
    ) -> AccountImportResponse:
        tournament = TournamentService(self.db).require(tournament_id)
        if tournament.status not in self.IMPORTABLE_STATUSES:
            raise AppError(
                "ACCOUNT_IMPORT_CLOSED",
                "赛事结束或取消后不能继续导入账号",
                status_code=409,
            )
        parsed = self._parse_file(content, account_type)
        existing = self.repository.existing_digests(
            tournament_id,
            account_type,
            [item.digest for item in parsed],
        )
        duplicate_errors = [
            {"line": item.line_number, "reason": "该账号已导入过本场赛事"}
            for item in parsed
            if item.digest in existing
        ]
        if duplicate_errors:
            raise AppError(
                "ACCOUNT_IMPORT_INVALID",
                "文件中包含已导入账号，本次未导入任何数据",
                details={"errors": duplicate_errors, "error_count": len(duplicate_errors)},
            )

        safe_filename = filename.replace("\\", "/").rsplit("/", 1)[-1][:255] or "accounts.txt"
        batch = AccountImportBatch(
            tournament_id=tournament_id,
            account_type=account_type.value,
            original_filename=safe_filename,
            imported_count=len(parsed),
            imported_by_id=operator_id,
        )
        self.db.add(batch)
        self.db.flush()
        for item in parsed:
            self.db.add(TournamentAccount(
                tournament_id=tournament_id,
                import_batch_id=batch.id,
                account_type=account_type.value,
                account_digest=item.digest,
                account_ciphertext=self.cipher.encrypt(item.account),
                password_ciphertext=self.cipher.encrypt(item.password),
                status=TournamentAccountStatus.AVAILABLE.value,
            ))
        add_audit_log(
            self.db,
            operator_id=operator_id,
            tournament_id=tournament_id,
            action_type="TOURNAMENT_ACCOUNTS_IMPORTED",
            target_type="account_import_batch",
            target_id=batch.id,
            after={"account_type": account_type.value, "imported_count": len(parsed)},
        )
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise AppError(
                "ACCOUNT_IMPORT_DUPLICATE",
                "导入过程中发现重复账号，请刷新后重试",
                status_code=409,
            ) from exc
        return AccountImportResponse(
            batch_id=batch.id,
            account_type=account_type,
            imported_count=len(parsed),
            available_count=self.repository.available_count(tournament_id, account_type),
        )

    def claim(
        self,
        tournament_id: UUID,
        account_type: AccountType,
        user_id: UUID,
    ) -> AccountCredentialResponse:
        tournament = TournamentService(self.db).require(tournament_id)
        if tournament.status not in self.CLAIMABLE_STATUSES:
            raise AppError(
                "ACCOUNT_CLAIM_CLOSED",
                "赛事账号当前不在可领取时间内",
                status_code=409,
            )
        registration = self.registrations.for_user(tournament_id, user_id, for_update=True)
        if registration is None or registration.status != RegistrationStatus.APPROVED.value:
            raise AppError(
                "APPROVED_REGISTRATION_REQUIRED",
                "只有报名审核通过的选手可以领取赛事账号",
                status_code=403,
            )
        existing = self.repository.claimed_for_registration(registration.id, account_type)
        if existing is not None:
            raise AppError(
                "ACCOUNT_ALREADY_CLAIMED",
                "你已经领取过该账号，不能重复领取",
                status_code=409,
            )
        reserved = self.repository.reserved_for_registration(registration.id, account_type)
        if reserved is not None:
            request = self.repository.approved_replacement_request(registration.id, account_type)
            if request is None or request.replacement_account_id != reserved.id:
                raise AppError(
                    "ACCOUNT_RESERVATION_INVALID",
                    "换号预留记录不完整，请联系赛事主办方",
                    status_code=409,
                )
            claimed_at = datetime.now(UTC)
            reserved.status = TournamentAccountStatus.CLAIMED.value
            reserved.claimed_at = claimed_at
            request.status = AccountReplacementStatus.COMPLETED.value
            request.completed_at = claimed_at
            account = reserved
            audit_action = "TOURNAMENT_ACCOUNT_REPLACEMENT_CLAIMED"
        else:
            if self.repository.has_invalid_for_registration(registration.id, account_type):
                raise AppError(
                    "ACCOUNT_REPLACEMENT_NOT_APPROVED",
                    "当前没有已通过的换号申请",
                    status_code=409,
                )
            account = self.repository.next_available(tournament_id, account_type)
            audit_action = "TOURNAMENT_ACCOUNT_CLAIMED"
        if account is None:
            raise AppError(
                "ACCOUNT_INVENTORY_EMPTY",
                "该类型账号暂时不足，请联系赛事主办方",
                status_code=409,
            )
        if account.status == TournamentAccountStatus.AVAILABLE.value:
            account.status = TournamentAccountStatus.CLAIMED.value
            account.claimed_registration_id = registration.id
            account.claimed_by_user_id = user_id
            account.claimed_at = datetime.now(UTC)
        add_audit_log(
            self.db,
            operator_id=user_id,
            tournament_id=tournament_id,
            action_type=audit_action,
            target_type="tournament_account",
            target_id=account.id,
            after={"account_type": account_type.value, "user_id": str(user_id)},
        )
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise AppError(
                "ACCOUNT_ALREADY_CLAIMED",
                "你已经领取过该账号，不能重复领取",
                status_code=409,
            ) from exc
        return self._credential_response(account)

    def my_accounts(self, tournament_id: UUID, user_id: UUID) -> MyTournamentAccountsResponse:
        TournamentService(self.db).require(tournament_id)
        registration = self.registrations.for_user(tournament_id, user_id)
        if registration is None:
            return MyTournamentAccountsResponse(items=[], replacement_requests=[])
        latest_requests: list[AccountReplacementRequest] = []
        seen_types: set[str] = set()
        for request in self.repository.replacement_requests_for_registration(registration.id):
            if request.account_type not in seen_types:
                latest_requests.append(request)
                seen_types.add(request.account_type)
        return MyTournamentAccountsResponse(
            items=[self._credential_response(item) for item in self.repository.claims_for_registration(registration.id)],
            replacement_requests=[self._replacement_response(item) for item in latest_requests],
        )

    def request_replacement(
        self,
        tournament_id: UUID,
        account_type: AccountType,
        reason: str,
        user_id: UUID,
    ) -> AccountReplacementRequestResponse:
        tournament = TournamentService(self.db).require(tournament_id)
        if tournament.status not in self.CLAIMABLE_STATUSES:
            raise AppError(
                "ACCOUNT_REPLACEMENT_CLOSED",
                "赛事账号当前不在可申请换号时间内",
                status_code=409,
            )
        registration = self.registrations.for_user(tournament_id, user_id, for_update=True)
        if registration is None or registration.status != RegistrationStatus.APPROVED.value:
            raise AppError(
                "APPROVED_REGISTRATION_REQUIRED",
                "只有报名审核通过的选手可以申请换号",
                status_code=403,
            )
        account = self.repository.claimed_for_registration(registration.id, account_type)
        if account is None:
            raise AppError(
                "CLAIMED_ACCOUNT_REQUIRED",
                "领取该类型账号后才能申请换号",
                status_code=409,
            )
        if self.repository.open_replacement_request(registration.id, account_type) is not None:
            raise AppError(
                "ACCOUNT_REPLACEMENT_EXISTS",
                "该账号已有待处理的换号申请",
                status_code=409,
            )
        request = AccountReplacementRequest(
            tournament_id=tournament_id,
            registration_id=registration.id,
            account_type=account_type.value,
            original_account_id=account.id,
            reason=reason,
            status=AccountReplacementStatus.PENDING.value,
        )
        self.db.add(request)
        self.db.flush()
        add_audit_log(
            self.db,
            operator_id=user_id,
            tournament_id=tournament_id,
            action_type="TOURNAMENT_ACCOUNT_REPLACEMENT_REQUESTED",
            target_type="account_replacement_request",
            target_id=request.id,
            after={"account_type": account_type.value, "user_id": str(user_id)},
        )
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise AppError(
                "ACCOUNT_REPLACEMENT_EXISTS",
                "该账号已有待处理的换号申请",
                status_code=409,
            ) from exc
        return self._replacement_response(request)

    def replacement_requests_for_admin(
        self,
        tournament_id: UUID,
    ) -> AdminAccountReplacementRequestListResponse:
        TournamentService(self.db).require(tournament_id)
        items = self.repository.replacement_requests_for_admin(tournament_id)
        return AdminAccountReplacementRequestListResponse(
            items=[self._admin_replacement_response(item) for item in items],
            total=len(items),
            pending_count=sum(item.status == AccountReplacementStatus.PENDING.value for item in items),
        )

    def approve_replacement(
        self,
        tournament_id: UUID,
        request_id: UUID,
        operator_id: UUID,
    ) -> AdminAccountReplacementRequestResponse:
        tournament = TournamentService(self.db).require(tournament_id)
        if tournament.status not in self.CLAIMABLE_STATUSES:
            raise AppError("ACCOUNT_REPLACEMENT_CLOSED", "赛事当前不能处理换号申请", status_code=409)
        request = self.repository.replacement_request(request_id, for_update=True)
        if request is None or request.tournament_id != tournament_id:
            raise AppError("ACCOUNT_REPLACEMENT_NOT_FOUND", "换号申请不存在", status_code=404)
        if request.status != AccountReplacementStatus.PENDING.value:
            raise AppError("ACCOUNT_REPLACEMENT_ALREADY_REVIEWED", "该换号申请已经处理", status_code=409)
        registration = self.registrations.get(request.registration_id, for_update=True)
        if registration is None or registration.status != RegistrationStatus.APPROVED.value:
            raise AppError("APPROVED_REGISTRATION_REQUIRED", "选手报名状态已不允许换号", status_code=409)
        original = self.repository.account(request.original_account_id, for_update=True)
        if original is None or original.status != TournamentAccountStatus.CLAIMED.value:
            raise AppError("ORIGINAL_ACCOUNT_NOT_CLAIMED", "原账号状态已发生变化", status_code=409)
        account_type = AccountType(request.account_type)
        replacement = self.repository.next_available(tournament_id, account_type)
        if replacement is None:
            raise AppError(
                "ACCOUNT_INVENTORY_EMPTY",
                "该类型账号库存不足，请先导入账号再通过申请",
                status_code=409,
            )
        original.status = TournamentAccountStatus.INVALID.value
        self.db.flush()
        replacement.status = TournamentAccountStatus.RESERVED.value
        replacement.claimed_registration_id = registration.id
        replacement.claimed_by_user_id = registration.user_id
        replacement.claimed_at = None
        reviewed_at = datetime.now(UTC)
        request.status = AccountReplacementStatus.APPROVED.value
        request.replacement_account_id = replacement.id
        request.reviewed_by_id = operator_id
        request.reviewed_at = reviewed_at
        request.rejection_reason = None
        add_audit_log(
            self.db,
            operator_id=operator_id,
            tournament_id=tournament_id,
            action_type="TOURNAMENT_ACCOUNT_REPLACEMENT_APPROVED",
            target_type="account_replacement_request",
            target_id=request.id,
            before={"original_account_id": str(original.id), "status": AccountReplacementStatus.PENDING.value},
            after={"replacement_account_id": str(replacement.id), "status": AccountReplacementStatus.APPROVED.value},
        )
        add_automatic_message(
            self.db,
            recipient_id=registration.user_id,
            message_type=MessageType.TOURNAMENT_NOTICE,
            title="换号申请已通过",
            body=f"你在“{tournament.name}”的{self._account_type_text(account_type)}换号申请已通过，请进入赛事账号页面重新获取。",
            action_url=f"/tournaments/{tournament_id}",
            related_type="account_replacement_request",
            related_id=request.id,
            dedupe_key=f"account-replacement:{request.id}:approved",
        )
        self.db.commit()
        return self._admin_replacement_response(request)

    def reject_replacement(
        self,
        tournament_id: UUID,
        request_id: UUID,
        rejection_reason: str,
        operator_id: UUID,
    ) -> AdminAccountReplacementRequestResponse:
        tournament = TournamentService(self.db).require(tournament_id)
        if tournament.status not in self.CLAIMABLE_STATUSES:
            raise AppError("ACCOUNT_REPLACEMENT_CLOSED", "赛事当前不能处理换号申请", status_code=409)
        request = self.repository.replacement_request(request_id, for_update=True)
        if request is None or request.tournament_id != tournament_id:
            raise AppError("ACCOUNT_REPLACEMENT_NOT_FOUND", "换号申请不存在", status_code=404)
        if request.status != AccountReplacementStatus.PENDING.value:
            raise AppError("ACCOUNT_REPLACEMENT_ALREADY_REVIEWED", "该换号申请已经处理", status_code=409)
        reviewed_at = datetime.now(UTC)
        request.status = AccountReplacementStatus.REJECTED.value
        request.reviewed_by_id = operator_id
        request.reviewed_at = reviewed_at
        request.rejection_reason = rejection_reason
        add_audit_log(
            self.db,
            operator_id=operator_id,
            tournament_id=tournament_id,
            action_type="TOURNAMENT_ACCOUNT_REPLACEMENT_REJECTED",
            target_type="account_replacement_request",
            target_id=request.id,
            before={"status": AccountReplacementStatus.PENDING.value},
            after={"status": AccountReplacementStatus.REJECTED.value, "reason": rejection_reason},
        )
        add_automatic_message(
            self.db,
            recipient_id=request.registration.user_id,
            message_type=MessageType.TOURNAMENT_NOTICE,
            title="换号申请未通过",
            body=f"你在“{tournament.name}”的换号申请未通过：{rejection_reason}",
            action_url=f"/tournaments/{tournament_id}",
            related_type="account_replacement_request",
            related_id=request.id,
            dedupe_key=f"account-replacement:{request.id}:rejected",
        )
        self.db.commit()
        return self._admin_replacement_response(request)

    def list_for_admin(
        self,
        tournament_id: UUID,
        account_type: AccountType | None,
    ) -> AdminTournamentAccountListResponse:
        TournamentService(self.db).require(tournament_id)
        items = self.repository.list_for_admin(tournament_id, account_type)
        counts = self.repository.summaries(tournament_id)
        summaries = [
            AccountInventorySummary(account_type=item, **counts[item.value])
            for item in AccountType
        ]
        return AdminTournamentAccountListResponse(
            items=[self._admin_response(item) for item in items],
            summaries=summaries,
            total=len(items),
        )

    def _parse_file(self, content: bytes, account_type: AccountType) -> list[ParsedAccount]:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise AppError(
                "ACCOUNT_IMPORT_ENCODING_INVALID",
                "账号文件必须使用 UTF-8 编码",
            ) from exc
        errors: list[dict[str, int | str]] = []
        parsed: list[ParsedAccount] = []
        seen: set[str] = set()
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            if account_type == AccountType.KONAMI and line.startswith("科乐美账号:"):
                credentials, _, _email = line.partition("------邮箱:")
                account, separator, password = credentials.removeprefix("科乐美账号:").partition(",密码:")
                if not separator:
                    errors.append({
                        "line": line_number,
                        "reason": "必须使用“科乐美账号:账号,密码:密码”格式",
                    })
                    continue
                account = account.strip()
                password = password.strip()
            else:
                if line.count("----") != 1:
                    errors.append({"line": line_number, "reason": "必须使用四个短横线分隔账号和密码"})
                    continue
                account, password = line.split("----", 1)
            if not account.strip() or not password.strip():
                errors.append({"line": line_number, "reason": "账号和密码均不能为空"})
                continue
            if len(account) > 255 or len(password) > 512:
                errors.append({"line": line_number, "reason": "账号或密码长度超过限制"})
                continue
            digest = self.cipher.account_digest(account)
            if digest in seen:
                errors.append({"line": line_number, "reason": "文件内账号重复"})
                continue
            seen.add(digest)
            parsed.append(ParsedAccount(line_number, account, password, digest))
        if not parsed and not errors:
            raise AppError("ACCOUNT_IMPORT_EMPTY", "账号文件中没有可导入的数据")
        if errors:
            raise AppError(
                "ACCOUNT_IMPORT_INVALID",
                "账号文件格式有误，本次未导入任何数据",
                details={"errors": errors, "error_count": len(errors)},
            )
        return parsed

    def _credential_response(self, item: TournamentAccount) -> AccountCredentialResponse:
        if item.claimed_at is None:
            raise AppError("ACCOUNT_CLAIM_INCOMPLETE", "赛事账号领取记录不完整", status_code=500)
        return AccountCredentialResponse(
            account_type=AccountType(item.account_type),
            account=self.cipher.decrypt(item.account_ciphertext),
            password=self.cipher.decrypt(item.password_ciphertext),
            claimed_at=item.claimed_at,
        )

    def _admin_response(self, item: TournamentAccount) -> AdminTournamentAccountResponse:
        return AdminTournamentAccountResponse(
            id=item.id,
            account_type=AccountType(item.account_type),
            account=self.cipher.decrypt(item.account_ciphertext),
            status=TournamentAccountStatus(item.status),
            claimed_by_user_id=item.claimed_by_user_id,
            claimed_by_nickname=item.claimed_by.nickname if item.claimed_by else None,
            claimed_at=item.claimed_at,
            created_at=item.created_at,
        )

    @staticmethod
    def _account_type_text(account_type: AccountType) -> str:
        return "科乐美账号" if account_type == AccountType.KONAMI else "Steam 账号"

    def _replacement_response(self, item: AccountReplacementRequest) -> AccountReplacementRequestResponse:
        return AccountReplacementRequestResponse(
            id=item.id,
            account_type=AccountType(item.account_type),
            status=AccountReplacementStatus(item.status),
            reason=item.reason,
            rejection_reason=item.rejection_reason,
            created_at=item.created_at,
            reviewed_at=item.reviewed_at,
            completed_at=item.completed_at,
        )

    def _admin_replacement_response(
        self,
        item: AccountReplacementRequest,
    ) -> AdminAccountReplacementRequestResponse:
        return AdminAccountReplacementRequestResponse(
            **self._replacement_response(item).model_dump(),
            user_id=item.registration.user_id,
            nickname=item.registration.user.nickname,
            original_account=self.cipher.decrypt(item.original_account.account_ciphertext),
            replacement_account=(
                self.cipher.decrypt(item.replacement_account.account_ciphertext)
                if item.replacement_account is not None
                else None
            ),
        )
