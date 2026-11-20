"""Production entry point: `games-server` or `python -m games_server`."""

import os
import sys

import uvicorn

from games_server.app import create_app
from games_server.config import ConfigError, Settings


def main() -> None:
    try:
        settings = Settings.from_env(os.environ)
    except ConfigError as error:
        sys.exit(f"Configuration error: {error}")
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
