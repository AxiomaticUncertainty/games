"""The path a shot takes, given the player's function.

A shot starts at the shooter, (0, 0) in shot coordinates, and follows the graph
of the player's function away from them, in the direction they chose. Firing
left mirrors the graph, so a function means the same thing whichever way the
player faces: `x^2` arcs upward on either side.

The function must pass through (0, 0); `x - 5` is rejected rather than shifted.

The shot stops at the first point where its curve breaks:

- where the function is undefined (`sqrt(5 - x)` beyond 5);
- where it jumps (`abs(x - 3)/(x - 3)` at 3);
- where it gets steeper than MAX_SLOPE, which is vertical at battlefield
  scale. This covers poles: `1/(x - 5)` stops where it turns vertical,
  shortly before 5.

How breaks are found: the curve is sampled every SAMPLE_STEP, and only
intervals whose height changes by more than JUMP_THRESHOLD are examined. If
such an interval is steeper than MAX_SLOPE on average, at least one of its
halves must be too, so following those halves down to BREAK_PRECISION locates
a break without backtracking. If it isn't, it is split and both halves are
checked, left first. That can only happen while the interval is wider than
JUMP_THRESHOLD / MAX_SLOPE, which bounds the work, however wild the function.

A jump that's undone within one SAMPLE_STEP (up and straight back down) can be
missed; that's too narrow to see on the battlefield.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple

SAMPLE_STEP = 0.01
JUMP_THRESHOLD = 0.05
MAX_SLOPE = 100.0
BREAK_PRECISION = 1e-9
# Allows for floating-point noise: `x + 0.1 + 0.2 - 0.3` is about 5.6e-17 at 0.
ORIGIN_TOLERANCE = 1e-9

# A parsed Expression, or any function of x that returns NaN where undefined.
type Function = Callable[[float], float]


class Direction(Enum):
    LEFT = -1
    RIGHT = 1


class Ending(Enum):
    """Why a shot's path ends."""

    LIMIT = "limit"  # it reached the distance or height it was traced to
    UNDEFINED = "undefined"  # the function has no value beyond this point
    BREAK = "break"  # the curve jumps or turns vertical here


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
    f: Function, direction: Direction, max_distance: float, max_height: float
) -> ShotPath:
    """Trace the shot `f` fired in `direction`.

    The path ends at the first break in the curve, at `max_distance` from the
    shooter, or just after it passes `max_height` above or below them,
    whichever comes first. Raises `InvalidShot` if `f` doesn't start at (0, 0).
    """
    _check_starts_at_origin(f)

    # Traced as distance from the shooter, then mirrored at the end if needed.
    current = Point(0.0, f(0.0))
    samples = [current]
    ending = Ending.LIMIT
    for step in range(1, math.ceil(max_distance / SAMPLE_STEP) + 1):
        if abs(current.y) > max_height:
            break
        # Multiplying, rather than adding SAMPLE_STEP each time, keeps
        # rounding errors from accumulating along the path.
        distance = min(step * SAMPLE_STEP, max_distance)
        following = Point(distance, f(distance))
        found = _first_break(f, current, following)
        if found is not None:
            last_good, ending = found
            samples.append(last_good)
            break
        current = following
        samples.append(current)

    points = tuple(Point(direction.value * x, y) for x, y in samples)
    return ShotPath(points, ending)


def _check_starts_at_origin(f: Function) -> None:
    start = f(0.0)
    if math.isnan(start):
        raise InvalidShot("Your function has no value at x = 0, so the shot can't start from you.")
    if abs(start) > ORIGIN_TOLERANCE:
        raise InvalidShot(f"Your function must pass through (0, 0), but at x = 0 it is {start:g}.")


def _first_break(f: Function, a: Point, b: Point) -> tuple[Point, Ending] | None:
    """The first break in the curve between `a` and `b`, or None if there is none.

    `a` is always a point where `f` is defined. On a break, returns the last
    point before it, and why the curve ended.
    """
    if not _changes_visibly(a, b):
        return None
    if _too_steep(a, b):
        return _locate_break(f, a, b)
    # A visible change, but not steep overall: a short steep part could be
    # hiding inside, so check both halves. Reaching here means b is defined
    # and the interval is wider than JUMP_THRESHOLD / MAX_SLOPE.
    middle = _midpoint(f, a, b)
    return _first_break(f, a, middle) or _first_break(f, middle, b)


def _locate_break(f: Function, a: Point, b: Point) -> tuple[Point, Ending]:
    """Narrow down a break in an interval known to be too steep overall.

    If both halves were gentle enough, the whole couldn't be too steep, so one
    of them is always too steep as well. Prefer the left one, which is closer
    to the shooter.
    """
    while b.x - a.x > BREAK_PRECISION:
        middle = _midpoint(f, a, b)
        if _too_steep(a, middle):
            b = middle
        else:
            a = middle
    return a, Ending.UNDEFINED if math.isnan(b.y) else Ending.BREAK


def _midpoint(f: Function, a: Point, b: Point) -> Point:
    x = (a.x + b.x) / 2
    return Point(x, f(x))


def _changes_visibly(a: Point, b: Point) -> bool:
    # NaN counts as an unlimited change: the curve stops there.
    return math.isnan(b.y) or abs(b.y - a.y) > JUMP_THRESHOLD


def _too_steep(a: Point, b: Point) -> bool:
    return math.isnan(b.y) or abs(b.y - a.y) > MAX_SLOPE * (b.x - a.x)
