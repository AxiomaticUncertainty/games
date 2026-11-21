"""Random battlefields: where the obstacles and players go.

Obstacles go down first, anywhere, overlapping into blobs of terrain. Then each
player in turn is put at a random spot with room for them: clear of every
obstacle, away from the edges, and not too near another player. If some player
finds no room, the whole battlefield is thrown away and started again.

Everything random comes from the `random.Random` passed in, so the same seed
always gives the same battlefield.
"""

import math
import random
from collections.abc import Iterable, Sequence

from games_server.games import PlayerId
from games_server.games.graph_artillery.battlefield import PLAYER_RADIUS, Battlefield, Circle
from games_server.games.graph_artillery.shot import Point

WIDTH = 50.0
HEIGHT = 30.0

MIN_OBSTACLES = 10
MAX_OBSTACLES = 20
MIN_OBSTACLE_RADIUS = 1.0
MAX_OBSTACLE_RADIUS = 4.0

# The least gap between a player's circle and an obstacle, so nobody starts
# wedged against terrain.
OBSTACLE_CLEARANCE = 1.0
# How near a player's center can be to the battlefield's edges.
EDGE_MARGIN = 1.0
# How near players' centers can be to each other, so nobody starts next to an
# easy target.
PLAYER_SPACING = 10.0

# Random spots tried for each player before giving up on a battlefield, and
# battlefields tried before giving up altogether.
SPOTS_PER_PLAYER = 100
MAX_BATTLEFIELDS = 50


class NoRoom(Exception):
    """The players couldn't all be fitted onto a battlefield."""


def random_battlefield(players: Sequence[PlayerId], rng: random.Random) -> Battlefield:
    """A new battlefield with `players` placed on it.

    Raises `NoRoom` if they can't be fitted, as when there are too many.
    """
    if len(set(players)) != len(players):
        raise ValueError(f"Each player must be listed once: {players}")
    for _ in range(MAX_BATTLEFIELDS):
        obstacles = _random_obstacles(rng)
        positions = _place_players(players, obstacles, rng)
        if positions is not None:
            return Battlefield(WIDTH, HEIGHT, positions, obstacles)
    raise NoRoom(f"Couldn't fit {len(players)} players onto a battlefield.")


def _random_obstacles(rng: random.Random) -> tuple[Circle, ...]:
    return tuple(
        Circle(
            Point(rng.uniform(0, WIDTH), rng.uniform(0, HEIGHT)),
            rng.uniform(MIN_OBSTACLE_RADIUS, MAX_OBSTACLE_RADIUS),
        )
        for _ in range(rng.randint(MIN_OBSTACLES, MAX_OBSTACLES))
    )


def _place_players(
    players: Sequence[PlayerId], obstacles: tuple[Circle, ...], rng: random.Random
) -> dict[PlayerId, Point] | None:
    """Where each player stands, or None if one of them finds no room."""
    positions: dict[PlayerId, Point] = {}
    for player in players:
        spot = _find_room(obstacles, positions.values(), rng)
        if spot is None:
            return None
        positions[player] = spot
    return positions


def _find_room(
    obstacles: Sequence[Circle], others: Iterable[Point], rng: random.Random
) -> Point | None:
    """A random spot with room for a player, or None after SPOTS_PER_PLAYER tries."""
    for _ in range(SPOTS_PER_PLAYER):
        spot = Point(
            rng.uniform(EDGE_MARGIN, WIDTH - EDGE_MARGIN),
            rng.uniform(EDGE_MARGIN, HEIGHT - EDGE_MARGIN),
        )
        if _has_room(spot, obstacles, others):
            return spot
    return None


def _has_room(spot: Point, obstacles: Sequence[Circle], others: Iterable[Point]) -> bool:
    clear_of_obstacles = all(
        math.dist(spot, obstacle.center) >= obstacle.radius + PLAYER_RADIUS + OBSTACLE_CLEARANCE
        for obstacle in obstacles
    )
    apart_from_players = all(math.dist(spot, other) >= PLAYER_SPACING for other in others)
    return clear_of_obstacles and apart_from_players
