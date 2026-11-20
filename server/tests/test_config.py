import pytest

from games_server.config import Settings


def test_defaults_apply_when_environment_is_empty() -> None:
    assert Settings.from_env({}) == Settings(host="127.0.0.1", port=8000)


def test_reads_host_and_port_from_environment() -> None:
    settings = Settings.from_env({"HOST": "0.0.0.0", "PORT": "9000"})

    assert settings == Settings(host="0.0.0.0", port=9000)


def test_rejects_non_numeric_port() -> None:
    with pytest.raises(ValueError):
        Settings.from_env({"PORT": "eighty"})
