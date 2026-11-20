"""Session tokens: proof that a browser has entered the site password.

A token is a fixed marker plus a timestamp, signed with SESSION_SECRET. It
holds no user data, since everyone shares one password. The signature means it
can't be forged without the secret. The timestamp makes it expire.

To log everyone out, change SESSION_SECRET: every existing token stops
verifying.
"""

from datetime import timedelta

from itsdangerous import BadSignature, TimestampSigner

SESSION_COOKIE = "games_session"
SESSION_LIFETIME = timedelta(days=30)

_MARKER = "authenticated"


class SessionTokens:
    def __init__(self, secret: str, lifetime: timedelta = SESSION_LIFETIME) -> None:
        # The salt separates these signatures from anything else that might be
        # signed with the same secret in future.
        self._signer = TimestampSigner(secret, salt="games.session")
        self._lifetime = lifetime

    def issue(self) -> str:
        return self._signer.sign(_MARKER).decode()

    def is_valid(self, token: str | None) -> bool:
        if not token:
            return False
        try:
            value = self._signer.unsign(token, max_age=int(self._lifetime.total_seconds()))
        except BadSignature:  # Also covers SignatureExpired.
            return False
        return value.decode() == _MARKER
