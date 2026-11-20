"""Middleware that keeps unauthenticated visitors out of the whole site.

It runs before routing, so a new page, asset, or WebSocket endpoint is
protected by default without anyone needing to remember to protect it.

This is plain ASGI middleware rather than Starlette's `BaseHTTPMiddleware`
because it must also cover WebSocket connections, which that helper skips.
"""

from starlette import status
from starlette.requests import HTTPConnection
from starlette.responses import PlainTextResponse, RedirectResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.websockets import WebSocketClose

from games_server.auth.tokens import SESSION_COOKIE, SessionTokens

LOGIN_PATH = "/login"


class PasswordGate:
    def __init__(self, app: ASGIApp, tokens: SessionTokens, public_paths: frozenset[str]) -> None:
        self._app = app
        self._tokens = tokens
        self._public_paths = public_paths

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self._requires_login(scope):
            await self._app(scope, receive, send)
            return

        if scope["type"] == "websocket":
            # Closing before accepting makes the server answer the handshake with 403.
            await WebSocketClose(code=status.WS_1008_POLICY_VIOLATION)(scope, receive, send)
            return

        await _login_required_response(scope)(scope, receive, send)

    def _requires_login(self, scope: Scope) -> bool:
        if scope["type"] not in ("http", "websocket"):
            return False  # e.g. ASGI lifespan events
        if scope["path"] in self._public_paths:
            return False
        cookie = HTTPConnection(scope).cookies.get(SESSION_COOKIE)
        return not self._tokens.is_valid(cookie)


def _login_required_response(scope: Scope) -> Response:
    # Browsers navigating to a page get sent to the login form. Anything else
    # (form posts, API calls) gets a plain 401 instead of a redirect it can't use.
    if scope["method"] in ("GET", "HEAD"):
        return RedirectResponse(LOGIN_PATH, status_code=status.HTTP_303_SEE_OTHER)
    return PlainTextResponse("Login required.", status_code=status.HTTP_401_UNAUTHORIZED)
