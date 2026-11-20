import pytest

from games_server.auth.passwords import hash_password
from games_server.config import ConfigError, Settings

HASH = hash_password("hunter2")
REQUIRED = {"SITE_PASSWORD_HASH": HASH, "SESSION_SECRET": "s" * 32}


def test_optional_settings_have_defaults() -> None:
    settings = Settings.from_env(REQUIRED)

    assert settings.host == "127.0.0.1"
    assert settings.port == 8000


def test_reads_every_setting_from_environment() -> None:
    settings = Settings.from_env({**REQUIRED, "HOST": "0.0.0.0", "PORT": "9000"})

    assert settings == Settings(
        site_password_hash=HASH, session_secret="s" * 32, host="0.0.0.0", port=9000
    )


@pytest.mark.parametrize("missing", ["SITE_PASSWORD_HASH", "SESSION_SECRET"])
def test_required_settings_must_be_present(missing: str) -> None:
    env = {name: value for name, value in REQUIRED.items() if name != missing}

    with pytest.raises(ConfigError, match=missing):
        Settings.from_env(env)


@pytest.mark.parametrize("value", ["", "hunter2", "$argon2id$not-really"])
def test_password_hash_must_be_an_argon2_hash(value: str) -> None:
    # Catches the likely mistake of putting the plain password here.
    with pytest.raises(ConfigError, match="SITE_PASSWORD_HASH"):
        Settings.from_env({**REQUIRED, "SITE_PASSWORD_HASH": value})


def test_session_secret_must_be_long_enough() -> None:
    with pytest.raises(ConfigError, match="SESSION_SECRET"):
        Settings.from_env({**REQUIRED, "SESSION_SECRET": "too-short"})


def test_rejects_non_numeric_port() -> None:
    with pytest.raises(ConfigError, match="PORT"):
        Settings.from_env({**REQUIRED, "PORT": "eighty"})


def test_secrets_are_hidden_from_repr() -> None:
    text = repr(Settings.from_env(REQUIRED))

    assert HASH not in text
    assert "s" * 32 not in text
