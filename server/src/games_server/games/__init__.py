"""The games. Each subpackage is one self-contained game.

A game's design notes live in `docs/games/`, one file per game. `GAMES` lists
what the rest of the site needs to know about each one, such as how many
players a room for it can hold.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class Game:
    id: str  # as used in URLs and the API; matches the client's games.ts
    name: str
    max_players: int


GAMES: Mapping[str, Game] = MappingProxyType(
    {
        game.id: game
        for game in (
            # layout.py fits 8 players on every battlefield it generates.
            Game("graph-artillery", "Graph artillery", max_players=8),
        )
    }
)
