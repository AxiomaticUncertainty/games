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
| Run with auto-reload          | `uv run uvicorn games_server.app:create_app --factory --reload` |
| Run as in production          | `uv run games-server`                                         |
| Tests                         | `uv run pytest`                                               |
| Lint                          | `uv run ruff check`                                           |
| Format                        | `uv run ruff format`                                          |
| Type-check                    | `uv run mypy`                                                 |

CI runs the lint, format check, type check, and tests on every pull request.

## Configuration

Read from environment variables at startup (see `src/games_server/config.py`):

| Variable | Default     | Meaning              |
| -------- | ----------- | -------------------- |
| `HOST`   | `127.0.0.1` | Interface to bind to |
| `PORT`   | `8000`      | Port to listen on    |

## Layout

```
src/games_server/
  __main__.py   entry point: reads settings, starts uvicorn
  app.py        create_app(): assembles routers and middleware
  config.py     Settings, the only place that reads the environment
  health.py     GET /healthz
tests/          pytest suite, one file per module
```
