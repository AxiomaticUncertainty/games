from collections.abc import Iterator

import pytest
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient

from games_server.app import create_app
from games_server.auth.passwords import hash_password
from games_server.config import Settings

PASSWORD = "correct horse battery staple"
PASSWORD_HASH = hash_password(PASSWORD)
SECRET = "x" * 32


@pytest.fixture
def settings() -> Settings:
    return Settings(site_password_hash=PASSWORD_HASH, session_secret=SECRET)


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    """The real app, plus stand-in routes for pages the gate should protect."""
    app = create_app(settings)

    @app.get("/protected")
    def protected() -> dict[str, str]:
        return {"secret": "data"}

    @app.websocket("/protected-ws")
    async def protected_ws(websocket: WebSocket) -> None:
        await websocket.accept()
        await websocket.send_text("hello")
        await websocket.close()

    return app


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    # https so the client keeps the Secure session cookie between requests.
    with TestClient(app, base_url="https://testserver") as client:
        yield client


def log_in(client: TestClient, password: str = PASSWORD) -> int:
    """Submit the login form; return the response status."""
    response = client.post("/login", data={"password": password}, follow_redirects=False)
    return response.status_code
