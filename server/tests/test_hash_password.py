from collections.abc import Iterator

import pytest

from games_server import hash_password
from games_server.auth.passwords import verify_password


def answer_prompts(monkeypatch: pytest.MonkeyPatch, *answers: str) -> None:
    replies: Iterator[str] = iter(answers)
    monkeypatch.setattr(hash_password, "getpass", lambda prompt: next(replies))


def test_prints_a_hash_of_the_entered_password(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    answer_prompts(monkeypatch, "hunter2", "hunter2")

    hash_password.main()

    printed = capsys.readouterr().out.strip()
    assert verify_password(printed, "hunter2")


def test_refuses_mismatched_passwords(monkeypatch: pytest.MonkeyPatch) -> None:
    answer_prompts(monkeypatch, "hunter2", "hunter3")

    with pytest.raises(SystemExit, match="did not match"):
        hash_password.main()


def test_refuses_an_empty_password(monkeypatch: pytest.MonkeyPatch) -> None:
    answer_prompts(monkeypatch, "")

    with pytest.raises(SystemExit, match="empty"):
        hash_password.main()
