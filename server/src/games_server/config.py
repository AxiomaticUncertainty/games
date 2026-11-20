"""Runtime settings, read once from environment variables at startup.

All configuration lives here so that the rest of the code receives plain
values and never reads `os.environ` directly. That keeps modules easy to test:
a test builds a `Settings` by hand instead of patching the environment.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field

from games_server.auth.passwords import is_password_hash

MIN_SESSION_SECRET_LENGTH = 32


class ConfigError(ValueError):
    """The environment is missing a setting or has an invalid one."""


@dataclass(frozen=True)
class Settings:
    # repr=False keeps secrets out of logs and tracebacks that print settings.
    site_password_hash: str = field(repr=False)
    session_secret: str = field(repr=False)
    host: str = "127.0.0.1"
    port: int = 8000

    def __post_init__(self) -> None:
        if not is_password_hash(self.site_password_hash):
            raise ConfigError(
                "SITE_PASSWORD_HASH must be an Argon2 hash. Generate one with: uv run hash-password"
            )
        if len(self.session_secret) < MIN_SESSION_SECRET_LENGTH:
            raise ConfigError(
                f"SESSION_SECRET must be at least {MIN_SESSION_SECRET_LENGTH} characters. "
                'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
            )

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> Settings:
        """Build settings from an environment mapping (usually `os.environ`).

        Raises `ConfigError` if a required variable is missing or invalid.
        Optional variables fall back to the defaults above.
        """
        return cls(
            site_password_hash=_require(env, "SITE_PASSWORD_HASH"),
            session_secret=_require(env, "SESSION_SECRET"),
            host=env.get("HOST", cls.host),
            port=_parse_port(env.get("PORT", str(cls.port))),
        )


def _require(env: Mapping[str, str], name: str) -> str:
    try:
        return env[name]
    except KeyError:
        raise ConfigError(f"Environment variable {name} is required.") from None


def _parse_port(raw: str) -> int:
    try:
        return int(raw)
    except ValueError:
        raise ConfigError(f"PORT must be an integer, got {raw!r}.") from None
