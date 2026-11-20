"""Application factory.

`create_app` is the single place where the web app is assembled: routers,
middleware, and (later) static files are all wired up here. Building the app in
a function rather than at import time lets each test get a fresh, isolated app.
"""

from fastapi import FastAPI

from games_server import health


def create_app() -> FastAPI:
    # The interactive API docs are disabled: this is a private site, not a
    # public API, and the docs pages would be one more thing to protect.
    app = FastAPI(title="games", docs_url=None, redoc_url=None, openapi_url=None)
    app.include_router(health.router)
    return app
