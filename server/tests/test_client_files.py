"""Serving the built client (client/dist) from the server."""

from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from games_server.app import create_app
from games_server.config import Settings
from tests.conftest import log_in


@pytest.fixture
def client_dir(tmp_path: Path) -> Path:
    """A stand-in for client/dist: an index page and one asset."""
    (tmp_path / "index.html").write_text("<p>the client</p>")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log('hi')")
    return tmp_path


@pytest.fixture
def client(settings: Settings, client_dir: Path) -> Iterator[TestClient]:
    app = create_app(replace(settings, client_dir=client_dir))
    with TestClient(app, base_url="https://testserver") as client:
        yield client


def test_serves_the_client_after_login(client: TestClient) -> None:
    log_in(client)

    assert client.get("/").text == "<p>the client</p>"
    assert client.get("/assets/app.js").text == "console.log('hi')"


def test_room_links_are_answered_with_the_client(client: TestClient) -> None:
    log_in(client)

    assert client.get("/rooms/K7QXM").text == "<p>the client</p>"


def test_client_files_are_behind_the_password(client: TestClient) -> None:
    for path in ("/", "/index.html", "/assets/app.js", "/rooms/K7QXM"):
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 303, path
        assert response.headers["location"] == "/login"


def test_server_routes_still_win_over_client_files(client: TestClient) -> None:
    assert client.get("/healthz").json() == {"status": "ok"}
    assert "<form" in client.get("/login").text


def test_unknown_paths_are_not_found(client: TestClient) -> None:
    log_in(client)

    assert client.get("/no-such-file.js").status_code == 404
