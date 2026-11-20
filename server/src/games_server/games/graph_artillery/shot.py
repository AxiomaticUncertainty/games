"""The path a shot takes, given the player's function.

A shot starts at the shooter, (0, 0) in shot coordinates, and follows the graph
of the player's function away from them, in the direction they chose. Firing
left mirrors the graph, so a function means the same thing whichever way the
player faces: `x^2` arcs upward on either side.

The function must pass through (0, 0); `x - 5` is rejected rather than shifted.

The shot flies until it leaves the battlefield or reaches the first point where
the function isn't continuous: where it is undefined (`sqrt(5 - x)` beyond 5),
jumps (`abs(x - 3)/(x - 3)` at 3), has a pole (`tan(x)` at pi/2), or has a
single missing point (`sin(x - pi)/(x - pi)` at pi). Steep is not broken: a
smooth curve may climb as sharply as it likes.

How: the path is sampled every SAMPLE_STEP until it leaves the battlefield.
Then `Expression.first_break` looks for a break along that stretch, including
ones no sample landed on, and the path is cut short there if it finds one.
"""

import math
from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple

from games_server.games.graph_artillery.expression import Expression
from games_server.games.graph_artillery.expression.continuity import BREAK_PRECISION, TooRough

SAMPLE_STEP = 0.01
# Allows for floating-point noise: `x + 0.1 + 0.2 - 0.3` is about 5.6e-17 at 0.
ORIGIN_TOLERANCE = 1e-9


class Direction(Enum):
    LEFT = -1
    RIGHT = 1


class Ending(Enum):
    """Why a shot's path ends."""

    LIMIT = "limit"  # it reached the edge of the battlefield
    UNDEFINED = "undefined"  # the function has no value beyond this point
    BREAK = "break"  # the function jumps, has a pole, or misses a point here


class Point(NamedTuple):
    x: float
    y: float


@dataclass(frozen=True)
class ShotPath:
    # In shot coordinates: the shooter is at (0, 0), and x is already mirrored
    # for shots fired left, so points can be drawn as they are.
    points: tuple[Point, ...]
    ending: Ending


class InvalidShot(ValueError):
    """The function can't be fired. The message is written for players."""


def trace_shot(
    f: Expression,
    direction: Direction,
    *,
    max_distance: float,
    min_height: float,
    max_height: float,
) -> ShotPath:
    """Trace the shot `f` fired in `direction`.

    The limits describe the battlefield's edges as seen from the shooter: how
    far it extends in `direction`, and the heights of its bottom and top edges
    relative to the shooter.

    The path ends at the first break in the curve, at `max_distance`, or just
    after it crosses the bottom or top edge, whichever comes first. Raises
    `InvalidShot` if `f` doesn't start at (0, 0), or can't be traced.
    """
    if not min_height <= 0 <= max_height:
        raise ValueError("The shooter must be on the battlefield.")

    def on_battlefield(point: Point) -> bool:
        # False for NaN, since every comparison with NaN is False.
        return min_height <= point.y <= max_height

    # Traced as distance from the shooter, then mirrored at the end if needed.
    start = Point(0.0, f(0.0))
    _check_starts_at_origin(start.y)
    samples = [start]
    for step in range(1, math.ceil(max_distance / SAMPLE_STEP) + 1):
        # Multiplying, rather than adding SAMPLE_STEP each time, keeps
        # rounding errors from accumulating along the path.
        distance = min(step * SAMPLE_STEP, max_distance)
        samples.append(Point(distance, f(distance)))
        if not on_battlefield(samples[-1]):
            break

    try:
        break_at = f.first_break(0.0, samples[-1].x)
    except TooRough as error:
        message = "Your function is too complicated to trace. Try writing it simply."
        raise InvalidShot(message) from error

    ending = Ending.LIMIT
    if break_at is not None:
        samples = [point for point in samples if point.x < break_at]
        samples.append(Point(break_at, f(break_at)))
        # Just past the break: undefined there means the function has no
        # value beyond it, rather than jumping or missing a point.
        is_undefined_beyond = math.isnan(f(break_at + 2 * BREAK_PRECISION))
        ending = Ending.UNDEFINED if is_undefined_beyond else Ending.BREAK
        if not on_battlefield(samples[-1]):
            ending = Ending.LIMIT  # it left the battlefield before the break
    elif math.isnan(samples[-1].y):
        # No break, but too large to represent: it shot off the battlefield
        # within one step. There's no height to draw, so end at the last one.
        samples.pop()

    points = tuple(Point(direction.value * x, y) for x, y in samples)
    return ShotPath(points, ending)


def _check_starts_at_origin(start: float) -> None:
    if math.isnan(start):
        raise InvalidShot("Your function has no value at x = 0, so the shot can't start from you.")
    if abs(start) > ORIGIN_TOLERANCE:
        raise InvalidShot(f"Your function must pass through (0, 0), but at x = 0 it is {start:g}.")
