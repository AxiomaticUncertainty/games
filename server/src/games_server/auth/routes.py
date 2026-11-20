"""Login and logout endpoints."""

from datetime import timedelta
from html import escape
from importlib.resources import files
from string import Template
from typing import Annotated

from fastapi import APIRouter, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from games_server.auth.gate import LOGIN_PATH
from games_server.auth.passwords import verify_password
from games_server.auth.throttle import LoginThrottle
from games_server.auth.tokens import SESSION_COOKIE, SESSION_LIFETIME, SessionTokens

MAX_FAILED_LOGINS = 5
FAILED_LOGIN_WINDOW = timedelta(minutes=10)

_LOGIN_PAGE = Template(
    files("games_server.auth").joinpath("login.html").read_text(encoding="utf-8")
)


def create_router(password_hash: str, tokens: SessionTokens, throttle: LoginThrottle) -> APIRouter:
    router = APIRouter()

    @router.get(LOGIN_PATH)
    def login_page() -> HTMLResponse:
        return _render_login_page()

    @router.post(LOGIN_PATH)
    def login(request: Request, password: Annotated[str, Form()]) -> Response:
        client = request.client.host if request.client else "unknown"

        # Check the throttle before the password: hashing deliberately costs
        # real CPU time, and a locked-out client shouldn't get to spend it.
        if throttle.is_blocked(client):
            return _render_login_page(
                "Too many attempts. Try again in a few minutes.",
                status.HTTP_429_TOO_MANY_REQUESTS,
            )

        if not verify_password(password_hash, password):
            throttle.record_failure(client)
            return _render_login_page("Wrong password.", status.HTTP_401_UNAUTHORIZED)

        response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            SESSION_COOKIE,
            tokens.issue(),
            max_age=int(SESSION_LIFETIME.total_seconds()),
            httponly=True,  # page scripts can't read it
            secure=True,  # HTTPS only; browsers also accept it on http://localhost
            samesite="lax",  # not sent on cross-site form posts
        )
        return response

    @router.post("/logout")
    def logout() -> Response:
        response = RedirectResponse(LOGIN_PATH, status_code=status.HTTP_303_SEE_OTHER)
        response.delete_cookie(SESSION_COOKIE, httponly=True, secure=True, samesite="lax")
        return response

    return router


def _render_login_page(error: str = "", status_code: int = status.HTTP_200_OK) -> HTMLResponse:
    error_html = f'<p class="error" role="alert">{escape(error)}</p>' if error else ""
    return HTMLResponse(_LOGIN_PAGE.substitute(error_html=error_html), status_code=status_code)
