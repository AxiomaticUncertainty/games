"""End-to-end behaviour of the password gate, through the real app."""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from games_server.app import create_app
from games_server.auth.passwords import hash_password
from games_server.auth.tokens import SESSION_COOKIE
from games_server.config import Settings
from tests.conftest import log_in


def test_page_request_without_login_redirects_to_login_form(client: TestClient) -> None:
    response = client.get("/protected", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_non_page_request_without_login_is_unauthorized(client: TestClient) -> None:
    response = client.post("/protected")

    assert response.status_code == 401


def test_websocket_without_login_is_refused(client: TestClient) -> None:
    with pytest.raises(WebSocketDisconnect) as refused, client.websocket_connect("/protected-ws"):
        pass

    assert refused.value.code == 1008


def test_login_form_is_reachable_without_login(client: TestClient) -> None:
    response = client.get("/login")

    assert response.status_code == 200
    assert '<form method="post" action="/login">' in response.text


def test_correct_password_grants_access(client: TestClient) -> None:
    assert log_in(client) == 303

    assert client.get("/protected").json() == {"secret": "data"}

    # The test client always connects WebSockets over plain ws://, where a
    # Secure cookie is never sent, so pass the cookie by hand. Browsers send it
    # automatically over wss://.
    cookie = f"{SESSION_COOKIE}={client.cookies[SESSION_COOKIE]}"
    with client.websocket_connect("/protected-ws", headers={"cookie": cookie}) as websocket:
        assert websocket.receive_text() == "hello"


def test_session_cookie_is_locked_down(client: TestClient) -> None:
    response = client.post("/login", data={"password": "correct horse battery staple"})
    cookie = response.history[0].headers["set-cookie"].lower()

    assert "httponly" in cookie
    assert "secure" in cookie
    assert "samesite=lax" in cookie


def test_wrong_password_is_rejected(client: TestClient) -> None:
    response = client.post("/login", data={"password": "guess"})

    assert response.status_code == 401
    assert "Wrong password." in response.text
    assert client.get("/protected", follow_redirects=False).status_code == 303


def test_forged_cookie_is_rejected(client: TestClient) -> None:
    client.cookies.set(SESSION_COOKIE, "authenticated.forged.signature")

    assert client.get("/protected", follow_redirects=False).status_code == 303


def test_logout_ends_the_session(client: TestClient) -> None:
    log_in(client)

    client.post("/logout")

    assert client.get("/protected", follow_redirects=False).status_code == 303


def test_repeated_failures_lock_out_even_the_right_password(client: TestClient) -> None:
    for _ in range(5):
        assert log_in(client, "guess") == 401

    assert log_in(client) == 429


def test_changing_the_password_logs_everyone_out(client: TestClient, settings: Settings) -> None:
    log_in(client)
    cookie = client.cookies[SESSION_COOKIE]

    # Same secret, new password: as if the server restarted with a new hash.
    restarted = create_app(Settings(hash_password("a new password"), settings.session_secret))
    with TestClient(restarted, base_url="https://testserver") as after_restart:
        after_restart.cookies.set(SESSION_COOKIE, cookie)

        assert after_restart.get("/healthz").status_code == 200
        assert after_restart.get("/", follow_redirects=False).status_code == 303
