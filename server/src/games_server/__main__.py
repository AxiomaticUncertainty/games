"""Production entry point: `games-server` or `python -m games_server`."""

import os

import uvicorn

from games_server.app import create_app
from games_server.config import Settings


def main() -> None:
    settings = Settings.from_env(os.environ)
    uvicorn.run(create_app(), host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
