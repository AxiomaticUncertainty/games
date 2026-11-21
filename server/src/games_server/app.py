"""Application factory.

`create_app` is the single place where the web app is assembled: routers,
middleware, and the built client's files are all wired up here. Building the app in
a function rather than at import time lets each test get a fresh, isolated app.
"""

import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from games_server import health
from games_server.auth import routes as auth_routes
from games_server.auth.gate import LOGIN_PATH, PasswordGate
from games_server.auth.throttle import LoginThrottle
from games_server.auth.tokens import SessionTokens
from games_server.config import Settings
from games_server.rooms import routes as room_routes
from games_server.rooms.registry import RoomRegistry

# Paths reachable without the password: the login form itself, and the health
# check that hosting platforms call.
PUBLIC_PATHS = frozenset({LOGIN_PATH, "/healthz"})


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the app. Settings are read from the environment unless given."""
    if settings is None:
        settings = Settings.from_env(os.environ)

    tokens = SessionTokens(
        secret=settings.session_secret, password_hash=settings.site_password_hash
    )
    throttle = LoginThrottle(
        max_failures=auth_routes.MAX_FAILED_LOGINS,
        window=auth_routes.FAILED_LOGIN_WINDOW,
    )

    # The interactive API docs are disabled: this is a private site, not a
    # public API, and the docs pages would be one more thing to protect.
    app = FastAPI(title="games", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(PasswordGate, tokens=tokens, public_paths=PUBLIC_PATHS)
    app.include_router(health.router)
    app.include_router(auth_routes.create_router(settings.site_password_hash, tokens, throttle))
    app.include_router(room_routes.create_router(RoomRegistry()))

    if settings.client_dir is not None:
        # Mounted last: "/" matches every path, so it only receives requests
        # that no route above claimed. html=True serves index.html for "/".
        app.mount("/", StaticFiles(directory=settings.client_dir, html=True), name="client")

    return app
