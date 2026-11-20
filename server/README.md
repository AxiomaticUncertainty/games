# server

Python backend: serves the site, enforces the password gate, and runs game
rooms. Game rules are decided here, not in the browser.

## Setup

Requires [uv](https://docs.astral.sh/uv/), which installs the right Python
version and the locked dependencies:

```sh
uv sync
```

## Common tasks

| Task                          | Command                                                       |
| ----------------------------- | ------------------------------------------------------------- |
| Run with auto-reload          | `uv run uvicorn games_server.app:create_app --factory --reload --env-file .env` |
| Run as in production          | `uv run games-server`                                         |
| Hash a new site password      | `uv run hash-password`                                        |
| Tests                         | `uv run pytest`                                               |
| Lint                          | `uv run ruff check`                                           |
| Format                        | `uv run ruff format`                                          |
| Type-check                    | `uv run mypy`                                                 |

CI runs the lint, format check, type check, and tests on every pull request.

## Configuration

Read from environment variables at startup (see `src/games_server/config.py`).
The server refuses to start if a required one is missing or invalid.

| Variable         | Default     | Meaning                                                     |
| ---------------- | ----------- | ----------------------------------------------------------- |
| `SITE_PASSWORD_HASH` | (required) | Argon2 hash of the shared site password (never the password itself) |
| `SESSION_SECRET` | (required)  | Key for signing session cookies; at least 32 characters     |
| `HOST`           | `127.0.0.1` | Interface to bind to                                        |
| `PORT`           | `8000`      | Port to listen on                                           |

For local development, copy `.env.example` to `.env` (which git ignores), fill
it in, and use the auto-reload command above.

The server only ever sees a hash of the password, so a leaked environment
doesn't reveal it. To set or change the password, run `uv run hash-password`
and use its output as `SITE_PASSWORD_HASH`. The hash contains `$` characters,
so wrap it in single quotes in `.env` files and shell commands.

Changing `SESSION_SECRET` logs everyone out. Session cookies are `Secure`,
so outside localhost the site must be served over HTTPS.

## Access control

Everything except `/login` and `/healthz` requires the password. The check is
middleware (`auth/gate.py`) that runs before routing, so new pages, assets, and
WebSocket endpoints are protected without any extra code. Five wrong passwords
from one IP within ten minutes locks that IP out until the window passes.

## Layout

```
src/games_server/
  __main__.py   entry point: reads settings, starts uvicorn
  app.py        create_app(): assembles routers and middleware
  config.py     Settings, the only place that reads the environment
  health.py     GET /healthz
  auth/         password gate: session tokens, middleware, throttle, login routes
tests/          pytest suite, one file per module
```
