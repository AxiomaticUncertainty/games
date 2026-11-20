from datetime import timedelta

import pytest
from itsdangerous import TimestampSigner

from games_server.auth.tokens import SessionTokens

SECRET = "k" * 32


def test_issued_token_is_valid() -> None:
    tokens = SessionTokens(SECRET)

    assert tokens.is_valid(tokens.issue())


@pytest.mark.parametrize("token", [None, "", "garbage", "authenticated"])
def test_missing_or_malformed_token_is_invalid(token: str | None) -> None:
    assert not SessionTokens(SECRET).is_valid(token)


def test_token_signed_with_another_secret_is_invalid() -> None:
    other = SessionTokens("o" * 32).issue()

    assert not SessionTokens(SECRET).is_valid(other)


def test_token_expires_after_its_lifetime(monkeypatch: pytest.MonkeyPatch) -> None:
    tokens = SessionTokens(SECRET, lifetime=timedelta(hours=1))
    real_now = TimestampSigner(SECRET).get_timestamp()

    # Issue the token two hours in the past.
    monkeypatch.setattr(TimestampSigner, "get_timestamp", lambda self: real_now - 2 * 3600)
    old_token = tokens.issue()
    monkeypatch.undo()

    assert not tokens.is_valid(old_token)
