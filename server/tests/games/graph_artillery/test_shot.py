import math

import pytest

from games_server.games.graph_artillery.expression import parse
from games_server.games.graph_artillery.shot import (
    BREAK_PRECISION,
    MAX_SLOPE,
    SAMPLE_STEP,
    Direction,
    Ending,
    Function,
    InvalidShot,
    Point,
    ShotPath,
    trace_shot,
)

# Large enough that these tests are never cut short by the limits, unless a
# test sets its own.
FAR = 20.0
HIGH = 1e9


def trace(
    shot: str | Function,
    direction: Direction = Direction.RIGHT,
    max_distance: float = FAR,
    max_height: float = HIGH,
) -> ShotPath:
    f = parse(shot) if isinstance(shot, str) else shot
    return trace_shot(f, direction, max_distance=max_distance, max_height=max_height)


def last(path: ShotPath) -> Point:
    return path.points[-1]


class TestStartsAtTheShooter:
    @pytest.mark.parametrize("source", ["x - 5", "x^2 + 1", "cos(x)"])
    def test_rejects_functions_that_miss_the_origin(self, source: str) -> None:
        with pytest.raises(InvalidShot, match=r"\(0, 0\)"):
            trace(source)

    def test_says_where_the_function_is_at_zero(self) -> None:
        with pytest.raises(InvalidShot, match="it is -5"):
            trace("x - 5")

    def test_rejects_functions_undefined_at_zero(self) -> None:
        with pytest.raises(InvalidShot, match="no value at x = 0"):
            trace("x / abs(x)")

    def test_tolerates_floating_point_noise_at_zero(self) -> None:
        trace("x + 0.1 + 0.2 - 0.3")  # about 5.6e-17 at 0, not exactly 0

    def test_path_begins_at_the_shooter(self) -> None:
        assert trace("sin(x)").points[0] == Point(0.0, 0.0)


class TestDirection:
    def test_firing_right_follows_the_graph(self) -> None:
        point = trace("x^3").points[100]

        assert point.x == pytest.approx(1.0)
        assert point.y == pytest.approx(1.0)

    def test_firing_left_mirrors_the_graph(self) -> None:
        right = trace("x^3", Direction.RIGHT)
        left = trace("x^3", Direction.LEFT)

        # Same heights, opposite side: x^3 rises on the left too, rather than
        # falling as it would if evaluated at negative x.
        assert [p.y for p in left.points] == [p.y for p in right.points]
        assert [p.x for p in left.points] == [-p.x for p in right.points]

    def test_mirrored_shot_breaks_at_the_mirrored_point(self) -> None:
        source = "abs(x - 3.003)/(x - 3.003) + 1"

        assert last(trace(source, Direction.LEFT)).x == -last(trace(source)).x


class TestLimits:
    def test_continuous_shot_runs_to_the_distance_limit(self) -> None:
        path = trace("sin(x)", max_distance=10)

        assert path.ending is Ending.LIMIT
        assert last(path).x == 10
        assert len(path.points) == round(10 / SAMPLE_STEP) + 1

    def test_stops_just_after_leaving_the_height_limit(self) -> None:
        path = trace("x^2", max_height=4)

        assert path.ending is Ending.LIMIT
        assert abs(last(path).y) > 4
        assert abs(path.points[-2].y) <= 4

    def test_steep_but_continuous_curve_is_not_a_break(self) -> None:
        # Changes by up to 0.5 between samples, ten times the jump threshold,
        # but never steeper than 50:1.
        path = trace("50sin(x)", max_distance=10)

        assert path.ending is Ending.LIMIT
        assert last(path).x == 10


class TestBreaks:
    def test_stops_where_the_function_becomes_undefined(self) -> None:
        path = trace("sqrt(5 - x) - sqrt(5)")

        assert path.ending is Ending.UNDEFINED
        assert last(path).x == pytest.approx(5, abs=1e-6)

    def test_stops_at_a_jump(self) -> None:
        # 0 before 3.003, 2 after it. The jump falls between samples, so plain
        # sampling would step straight over it. (3.003 is never a midpoint the
        # search tries, so it finds the jump rather than landing on the one
        # point where 0/0 makes the function undefined.)
        path = trace("abs(x - 3.003)/(x - 3.003) + 1")

        assert path.ending is Ending.BREAK
        assert 3.003 - BREAK_PRECISION <= last(path).x < 3.003
        assert last(path).y == pytest.approx(0)

    def test_stops_where_a_pole_turns_vertical(self) -> None:
        # 1/(x - c) is steeper than MAX_SLOPE within 1/sqrt(MAX_SLOPE) of c.
        pole = 5.005
        path = trace(f"1/(x - {pole}) + 1/{pole}")

        assert path.ending is Ending.BREAK
        assert pole - 1.5 / math.sqrt(MAX_SLOPE) < last(path).x < pole

    def test_stops_before_a_pole_that_lands_exactly_on_a_sample(self) -> None:
        path = trace("1/(x - 5) + 1/5")

        assert path.ending is Ending.BREAK
        assert 4.8 < last(path).x < 5

    def test_curve_steeper_than_the_limit_is_a_break(self) -> None:
        path = trace(f"{MAX_SLOPE * 2}x")

        assert path.ending is Ending.BREAK
        assert last(path) == Point(0.0, 0.0)

    def test_finds_the_first_of_two_jumps(self) -> None:
        path = trace("abs(x - 2.003)/(x - 2.003) + abs(x - 4.003)/(x - 4.003) + 2")

        assert last(path).x == pytest.approx(2.003, abs=1e-6)

    def test_finds_a_jump_hidden_behind_a_steep_stretch(self) -> None:
        # Within one sample interval, a 50:1 climb and then a jump of 2. The
        # interval as a whole is steep, so the search must look past the
        # first half, which is steep but continuous.
        path = trace("50x + abs(x - 0.0073)/(x - 0.0073) + 1")

        assert path.ending is Ending.BREAK
        assert last(path).x == pytest.approx(0.0073, abs=1e-6)


class TestWorkIsBounded:
    def test_a_wildly_oscillating_function_costs_a_bounded_number_of_evaluations(self) -> None:
        # Changes visibly within every sample but stays just under MAX_SLOPE,
        # the worst case for splitting intervals.
        f = parse(f"0.2 * sin({MAX_SLOPE * 0.99 / 0.2}x)")
        calls = 0

        def counting(x: float) -> float:
            nonlocal calls
            calls += 1
            return f(x)

        path = trace(counting, max_distance=FAR)

        assert path.ending is Ending.LIMIT
        samples = round(FAR / SAMPLE_STEP)
        assert calls < 50 * samples
