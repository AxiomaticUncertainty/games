"""The battlefield, and what a shot fired across it hits.

The battlefield is a rectangle, `width` wide and `height` tall, with (0, 0) at
its bottom-left corner. Players and obstacles are circles on it. Obstacles
never change: a shot that hits one just stops.

A shot is traced from the shooter (see `shot`), moved onto the battlefield,
and then checked against everything on it in order along the path. It stops at
the first player or obstacle it touches. The shooter can't hit themself: the
shot starts inside them.

Between samples, the path is drawn as a straight line, and hits are judged
against the path as drawn, so a shot hits exactly what players see it hit.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from itertools import pairwise
from typing import NamedTuple

from games_server.games import PlayerId
from games_server.games.graph_artillery import shot
from games_server.games.graph_artillery.expression import Expression
from games_server.games.graph_artillery.shot import Direction, Point

PLAYER_RADIUS = 0.5


class Circle(NamedTuple):
    center: Point
    radius: float


@dataclass(frozen=True)
class Battlefield:
    width: float
    height: float
    # Where each player still in the game stands: the center of their circle.
    players: Mapping[PlayerId, Point]
    obstacles: tuple[Circle, ...]

    def __post_init__(self) -> None:
        for player, position in self.players.items():
            if not self.contains(position):
                raise ValueError(f"Player {player!r} at {position} is off the battlefield.")

    def contains(self, point: Point) -> bool:
        """Whether `point` is on the battlefield, edges included."""
        return 0 <= point.x <= self.width and 0 <= point.y <= self.height


class Ending(Enum):
    """Why a fired shot stopped."""

    HIT_PLAYER = "hit_player"  # see `FiredShot.hit`
    HIT_OBSTACLE = "hit_obstacle"
    EDGE = "edge"  # it left the battlefield
    UNDEFINED = "undefined"  # the function has no value beyond this point
    BREAK = "break"  # the function jumps, has a pole, or misses a point here


@dataclass(frozen=True)
class FiredShot:
    # In battlefield coordinates, from the shooter to where the shot stopped.
    path: tuple[Point, ...]
    ending: Ending
    hit: PlayerId | None = None  # the player hit, when `ending` is HIT_PLAYER


def fire(
    battlefield: Battlefield, shooter: PlayerId, f: Expression, direction: Direction
) -> FiredShot:
    """Fire `f` from `shooter` in `direction`, and find what it hits.

    Raises `shot.InvalidShot` if `f` can't be fired (see `shot.trace_shot`).
    """
    origin = battlefield.players[shooter]
    traced = shot.trace_shot(
        f,
        direction,
        max_distance=battlefield.width - origin.x if direction is Direction.RIGHT else origin.x,
        min_height=-origin.y,
        max_height=battlefield.height - origin.y,
    )
    path = [Point(origin.x + x, origin.y + y) for x, y in traced.points]
    _end_at_the_edge(path, battlefield)

    targets = [_Target(obstacle) for obstacle in battlefield.obstacles] + [
        _Target(Circle(position, PLAYER_RADIUS), player)
        for player, position in battlefield.players.items()
        if player != shooter
    ]
    for index, (start, end) in enumerate(pairwise(path)):
        entries = [
            (t, target)
            for target in targets
            if (t := _entry(start, end, target.circle)) is not None
        ]
        if entries:
            t, target = min(entries, key=lambda entry: entry[0])
            impact = Point(start.x + t * (end.x - start.x), start.y + t * (end.y - start.y))
            path_to_impact = (*path[: index + 1], impact)
            if target.player is None:
                return FiredShot(path_to_impact, Ending.HIT_OBSTACLE)
            return FiredShot(path_to_impact, Ending.HIT_PLAYER, target.player)

    return FiredShot(tuple(path), _ENDINGS[traced.ending])


_ENDINGS = {
    shot.Ending.LIMIT: Ending.EDGE,
    shot.Ending.UNDEFINED: Ending.UNDEFINED,
    shot.Ending.BREAK: Ending.BREAK,
}


class _Target(NamedTuple):
    circle: Circle
    player: PlayerId | None = None  # None for an obstacle


def _end_at_the_edge(path: list[Point], battlefield: Battlefield) -> None:
    """Cut the last step short where it crosses the top or bottom edge.

    A traced shot ends just after it crosses one, possibly far beyond it.
    Only the last point can be off the battlefield.
    """
    if len(path) < 2 or battlefield.contains(path[-1]):
        return
    end = path.pop()
    start = path[-1]
    edge = battlefield.height if end.y > battlefield.height else 0.0
    t = (edge - start.y) / (end.y - start.y)
    crossing = Point(start.x + t * (end.x - start.x), edge)
    # Exactly equal when `start` was already on the edge. Adding `crossing`
    # then would make a step of length zero, which has no direction to test
    # for hits. Any other crossing, however close, is a real step.
    if crossing != start:
        path.append(crossing)


def _entry(start: Point, end: Point, circle: Circle) -> float | None:
    """How far along the segment from `start` to `end` it first touches
    `circle`, from 0 at `start` to 1 at `end`, or None if it doesn't."""
    # Points on the segment are start + t*(end - start). Solving
    # |start + t*(end - start) - center|^2 = radius^2 gives a*t^2 + b*t + c = 0.
    dx, dy = end.x - start.x, end.y - start.y
    fx, fy = start.x - circle.center.x, start.y - circle.center.y
    a = dx * dx + dy * dy
    b = 2 * (fx * dx + fy * dy)
    c = fx * fx + fy * fy - circle.radius * circle.radius
    if c <= 0:
        return 0.0  # it starts inside
    discriminant = b * b - 4 * a * c
    if discriminant < 0:
        return None  # the line misses the circle
    t = (-b - math.sqrt(discriminant)) / (2 * a)  # the first of the two crossings
    return t if 0 <= t <= 1 else None
