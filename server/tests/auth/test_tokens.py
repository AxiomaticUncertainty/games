from datetime import timedelta

import pytest
from itsdangerous import TimestampSigner

from games_server.auth.tokens import SessionTokens

SECRET = "k" * 32
# SessionTokens doesn't inspect the hash, so any string stands in for one here.
PASSWORD_HASH = "stand-in-password-hash"


def make_tokens(
    secret: str = SECRET,
    password_hash: str = PASSWORD_HASH,
    lifetime: timedelta = timedelta(days=1),
) -> SessionTokens:
    return SessionTokens(secret=secret, password_hash=password_hash, lifetime=lifetime)


def test_issued_token_is_valid() -> None:
    tokens = make_tokens()

    assert tokens.is_valid(tokens.issue())


@pytest.mark.parametrize("token", [None, "", "garbage", "authenticated"])
def test_missing_or_malformed_token_is_invalid(token: str | None) -> None:
    assert not make_tokens().is_valid(token)


def test_changing_the_secret_invalidates_existing_tokens() -> None:
    old = make_tokens(secret="o" * 32).issue()

    assert not make_tokens().is_valid(old)


def test_changing_the_password_invalidates_existing_tokens() -> None:
    old = make_tokens(password_hash="hash-of-the-old-password").issue()

    assert not make_tokens().is_valid(old)


def test_token_does_not_reveal_the_password_hash() -> None:
    assert PASSWORD_HASH not in make_tokens().issue()


def test_token_expires_after_its_lifetime(monkeypatch: pytest.MonkeyPatch) -> None:
    tokens = make_tokens(lifetime=timedelta(hours=1))
    real_now = TimestampSigner(SECRET).get_timestamp()

    # Issue the token two hours in the past.
    monkeypatch.setattr(TimestampSigner, "get_timestamp", lambda self: real_now - 2 * 3600)
    old_token = tokens.issue()
    monkeypatch.undo()

    assert not tokens.is_valid(old_token)


def test_tokens_are_signed_with_sha256() -> None:
    signature = make_tokens().issue().rsplit(".", 1)[1]

    # A SHA-256 HMAC is 32 bytes: 43 characters of unpadded base64. SHA-1's
    # would be 27.
    assert len(signature) == 43
