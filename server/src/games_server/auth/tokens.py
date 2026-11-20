"""Session tokens: proof that a browser has entered the site password.

A token is a fixed marker plus a timestamp, signed with a key built from
SESSION_SECRET and the site password hash. It holds no user data, since
everyone shares one password. The signature means it can't be forged without
the key. The timestamp makes it expire.

Changing either SESSION_SECRET or the password changes the key, so every
existing token stops verifying and everyone has to log in again.
"""

from datetime import timedelta

from itsdangerous import BadSignature, TimestampSigner

SESSION_COOKIE = "games_session"
SESSION_LIFETIME = timedelta(days=30)

_MARKER = "authenticated"


class SessionTokens:
    def __init__(
        self, *, secret: str, password_hash: str, lifetime: timedelta = SESSION_LIFETIME
    ) -> None:
        # The salt separates these signatures from anything else that might be
        # signed with the same secret in future.
        self._signer = TimestampSigner(_signing_key(secret, password_hash), salt="games.session")
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


def _signing_key(secret: str, password_hash: str) -> str:
    # The password hash goes into the key, never into the token: tokens are
    # readable by the browser, and a leaked hash would allow offline guessing.
    # The NUL separator keeps the boundary between the two parts unambiguous.
    return f"{secret}\0{password_hash}"
