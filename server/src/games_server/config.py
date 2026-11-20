"""Runtime settings, read once from environment variables at startup.

All configuration lives here so that the rest of the code receives plain
values and never reads `os.environ` directly. That keeps modules easy to test:
a test builds a `Settings` by hand instead of patching the environment.
"""

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 8000

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> Settings:
        """Build settings from an environment mapping (usually `os.environ`).

        Unset variables fall back to the defaults above.
        """
        defaults = cls()
        return cls(
            host=env.get("HOST", defaults.host),
            port=int(env.get("PORT", defaults.port)),
        )
