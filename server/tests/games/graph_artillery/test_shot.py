import math

import pytest

from games_server.games.graph_artillery.expression import parse
from games_server.games.graph_artillery.shot import (
    BREAK_PRECISION,
    SAMPLE_STEP,
    Direction,
    Ending,
    InvalidShot,
    Point,
    ShotPath,
    trace_shot,
)

# A battlefield of roughly the size the game will use, unless a test sets its
# own edges.
FAR = 20.0
LOW = -100.0
HIGH = 100.0


def trace(
    source: str,
    direction: Direction = Direction.RIGHT,
    max_distance: float = FAR,
    min_height: float = LOW,
    max_height: float = HIGH,
) -> ShotPath:
    return trace_shot(
        parse(source),
        direction,
        max_distance=max_distance,
        min_height=min_height,
        max_height=max_height,
    )


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

    def test_stops_just_after_crossing_the_top_edge(self) -> None:
        path = trace("x^2", max_height=4)

        assert path.ending is Ending.LIMIT
        assert last(path).y > 4
        assert path.points[-2].y <= 4

    def test_stops_just_after_crossing_the_bottom_edge(self) -> None:
        path = trace("-x^2", min_height=-1, max_height=4)

        assert path.ending is Ending.LIMIT
        assert last(path).y < -1
        assert path.points[-2].y >= -1

    def test_shooter_must_be_on_the_battlefield(self) -> None:
        with pytest.raises(ValueError, match="on the battlefield"):
            trace("x", min_height=1)

    def test_edges_need_not_be_symmetric(self) -> None:
        # Close to the floor, far from the ceiling: a rising shot isn't cut
        # short just because the bottom edge is near.
        path = trace("x", max_distance=10, min_height=-1, max_height=20)

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

    def test_a_jump_off_the_battlefield_is_still_a_break(self) -> None:
        path = trace("1000 * (abs(x - 3.003)/(x - 3.003) + 1)")

        assert path.ending is Ending.BREAK
        assert last(path).x == pytest.approx(3.003, abs=1e-6)

    def test_finds_the_first_of_two_jumps(self) -> None:
        path = trace("abs(x - 2.003)/(x - 2.003) + abs(x - 4.003)/(x - 4.003) + 2")

        assert last(path).x == pytest.approx(2.003, abs=1e-6)

    def test_finds_a_jump_hidden_behind_a_steep_stretch(self) -> None:
        # Within one sample interval, a 50:1 climb and then a jump of 2.
        path = trace("50x + abs(x - 0.0073)/(x - 0.0073) + 1")

        assert path.ending is Ending.BREAK
        assert last(path).x == pytest.approx(0.0073, abs=1e-6)

    def test_stops_at_a_single_missing_point(self) -> None:
        # Continuous on both sides of pi, but undefined at pi itself, which
        # no sample lands on.
        path = trace("sin(x - pi)/(x - pi) - sin(-pi)/(-pi)")

        assert path.ending is Ending.BREAK
        assert last(path).x == pytest.approx(math.pi, abs=1e-6)

    def test_stops_at_a_pole_inside_the_battlefield(self) -> None:
        # tan never quite reaches infinity at the float closest to pi/2, so
        # sampling alone would see a very tall but finite spike.
        path = trace("tan(x)", min_height=-1e20, max_height=1e20)

        assert path.ending is Ending.BREAK
        assert last(path).x == pytest.approx(math.pi / 2, abs=1e-6)


class TestSteepCurves:
    def test_steep_sigmoid_is_not_a_break(self) -> None:
        # Climbs from 0 to 2 within about a hundredth of a unit around 3.
        path = trace("2/(1 + exp(-1000(x - 3)))", max_distance=10)

        assert path.ending is Ending.LIMIT
        assert last(path).x == 10
        assert last(path).y == pytest.approx(2)

    def test_steeper_than_any_sample_can_follow_is_not_a_break(self) -> None:
        # The climb takes about a millionth of a unit: in one sample interval.
        path = trace("tanh(1000000(x - 3.003)) + tanh(3003000)", max_distance=10)

        assert path.ending is Ending.LIMIT
        assert last(path).y == pytest.approx(2)

    def test_fast_wiggles_are_not_a_break(self) -> None:
        path = trace("sin(1000000x)", max_distance=10)

        assert path.ending is Ending.LIMIT
        assert last(path).x == 10

    def test_pole_ends_where_the_curve_leaves_the_battlefield(self) -> None:
        # Falls toward -infinity just before 5.005.
        path = trace("1/(x - 5.005) + 1/5.005", min_height=-30)

        assert path.ending is Ending.LIMIT
        assert last(path).y < -30
        assert path.points[-2].y >= -30

    def test_pole_landing_exactly_on_a_sample(self) -> None:
        path = trace("1/(x - 5) + 1/5", min_height=-30)

        assert path.ending is Ending.LIMIT
        assert last(path).y < -30


class TestWorkIsBounded:
    def test_function_too_rough_to_prove_is_rejected(self) -> None:
        # Mathematically just 0, but each 1000x*x could be anywhere in its
        # range independently, so the proof is very rough: the divisor seems
        # to include 0 until stretches are tiny.
        with pytest.raises(InvalidShot, match="too complicated"):
            trace("1/(1000x*x - 1000x*x + 1) - 1")
