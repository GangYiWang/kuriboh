from app.tournament_accounts.crypto import CredentialCipher


def test_tournament_account_credentials_round_trip_without_plaintext_storage() -> None:
    cipher = CredentialCipher("test-only-tournament-account-secret")
    encrypted = cipher.encrypt("Sensitive-Password")

    assert encrypted != "Sensitive-Password"
    assert cipher.decrypt(encrypted) == "Sensitive-Password"


def test_tournament_account_digest_is_case_sensitive() -> None:
    cipher = CredentialCipher("test-only-tournament-account-secret")

    assert cipher.account_digest("CaseUser") != cipher.account_digest("caseuser")
