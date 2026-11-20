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

How: the path is sampled every SAMPLE_STEP, and each stretch between samples
is proven continuous with `Expression.is_continuous`, which catches breaks
that no sample lands on. Where a stretch can't be proven, it is split in half
and the halves are checked in turn, left first, down to BREAK_PRECISION, to
find where the trouble starts. Splitting is capped at MAX_SEARCH_CHECKS per
shot; the cap is only reached by functions written so that the proof is
unusually rough (see `continuity`), and those are rejected.
"""

import math
from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple

from games_server.games.graph_artillery.expression import Expression

SAMPLE_STEP = 0.01
BREAK_PRECISION = 1e-9
# Allows for floating-point noise: `x + 0.1 + 0.2 - 0.3` is about 5.6e-17 at 0.
ORIGIN_TOLERANCE = 1e-9
# Finding one break takes about 60 checks, so this allows for plenty, while
# keeping the slowest possible search to a fraction of a second.
MAX_SEARCH_CHECKS = 5_000


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
    current = Point(0.0, f(0.0))
    _check_starts_at_origin(current.y)
    samples = [current]
    ending = Ending.LIMIT
    search = _BreakSearch(f)
    for step in range(1, math.ceil(max_distance / SAMPLE_STEP) + 1):
        # Multiplying, rather than adding SAMPLE_STEP each time, keeps
        # rounding errors from accumulating along the path.
        distance = min(step * SAMPLE_STEP, max_distance)
        found = search.first_break(current.x, distance)
        if found is not None:
            last, ending = found
            samples.append(last)
            if not on_battlefield(last):
                ending = Ending.LIMIT  # it left the battlefield before the break
            break
        current = Point(distance, f(distance))
        samples.append(current)
        if not on_battlefield(current):
            break

    points = tuple(Point(direction.value * x, y) for x, y in samples)
    return ShotPath(points, ending)


def _check_starts_at_origin(start: float) -> None:
    if math.isnan(start):
        raise InvalidShot("Your function has no value at x = 0, so the shot can't start from you.")
    if abs(start) > ORIGIN_TOLERANCE:
        raise InvalidShot(f"Your function must pass through (0, 0), but at x = 0 it is {start:g}.")


class _BreakSearch:
    """Finds where a function stops being provably continuous, within a budget."""

    def __init__(self, f: Expression) -> None:
        self._f = f
        self._checks_left = MAX_SEARCH_CHECKS

    def first_break(self, low: float, high: float) -> tuple[Point, Ending] | None:
        """The first break in [low, high], or None if it's continuous throughout.

        On a break, returns the last point before it, and how the curve ended.
        """
        if self._f.is_continuous(low, high):
            return None
        start = self._start_of_trouble(low, high)
        if start is None:
            return None
        # Just past the break: undefined there means the function has no value
        # beyond it, rather than jumping or missing a point.
        after = self._f(start + 2 * BREAK_PRECISION)
        return Point(start, self._f(start)), Ending.UNDEFINED if math.isnan(after) else Ending.BREAK

    def _start_of_trouble(self, low: float, high: float) -> float | None:
        """Where the first part of [low, high] that can't be proven continuous
        starts, or None if it all can be when split up.

        Splitting up can succeed where the whole failed, because the proof is
        rougher over wider stretches.
        """
        if high - low <= BREAK_PRECISION:
            return low
        middle = (low + high) / 2
        for half in ((low, middle), (middle, high)):
            if not self._check(*half) and (start := self._start_of_trouble(*half)) is not None:
                return start
        return None

    def _check(self, low: float, high: float) -> bool:
        self._checks_left -= 1
        if self._checks_left < 0:
            raise InvalidShot("Your function is too complicated to trace. Try writing it simply.")
        return self._f.is_continuous(low, high)
