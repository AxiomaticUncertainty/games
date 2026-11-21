import pytest

from games_server.games.graph_artillery.battlefield import (
    PLAYER_RADIUS,
    Battlefield,
    Circle,
    Ending,
    FiredShot,
    fire,
)
from games_server.games.graph_artillery.expression import parse
from games_server.games.graph_artillery.shot import Direction, InvalidShot, Point

WIDTH = 40.0
HEIGHT = 20.0


def battlefield(
    players: dict[str, Point] | None = None, obstacles: tuple[Circle, ...] = ()
) -> Battlefield:
    if players is None:
        players = {"ada": Point(5, 10), "bo": Point(35, 10)}
    return Battlefield(WIDTH, HEIGHT, players, obstacles)


def fire_at(
    field: Battlefield, source: str, direction: Direction = Direction.RIGHT, shooter: str = "ada"
) -> FiredShot:
    return fire(field, shooter, parse(source), direction)


def last(fired: FiredShot) -> Point:
    return fired.path[-1]


class TestBattlefield:
    def test_players_must_be_on_the_battlefield(self) -> None:
        with pytest.raises(ValueError, match=r"'ada'.*off the battlefield"):
            battlefield({"ada": Point(-1, 10)})


class TestPath:
    def test_starts_at_the_shooter(self) -> None:
        assert fire_at(battlefield(), "0").path[0] == Point(5, 10)

    def test_follows_the_graph_from_the_shooter(self) -> None:
        point = fire_at(battlefield(), "x^2/10").path[100]  # 1 unit along

        assert point.x == pytest.approx(6)
        assert point.y == pytest.approx(10.1)

    def test_firing_left_mirrors_the_graph(self) -> None:
        point = fire_at(battlefield(), "x^2/10", Direction.LEFT).path[100]

        assert point.x == pytest.approx(4)
        assert point.y == pytest.approx(10.1)

    def test_rejects_functions_that_cannot_be_fired(self) -> None:
        with pytest.raises(InvalidShot):
            fire_at(battlefield(), "x - 5")


class TestEdges:
    def test_runs_to_the_far_side(self) -> None:
        # Fired at a height where it passes over the other player.
        fired = fire_at(battlefield(), "x/10")

        assert fired.ending is Ending.EDGE
        assert last(fired) == pytest.approx(Point(WIDTH, 13.5))

    def test_runs_to_the_near_side_when_fired_left(self) -> None:
        fired = fire_at(battlefield(), "0", Direction.LEFT)

        assert fired.ending is Ending.EDGE
        assert last(fired) == pytest.approx(Point(0, 10))

    @pytest.mark.parametrize(("source", "edge"), [("x", HEIGHT), ("-x", 0.0)])
    def test_ends_on_the_top_or_bottom_edge(self, source: str, edge: float) -> None:
        fired = fire_at(battlefield(), source)

        assert fired.ending is Ending.EDGE
        assert last(fired).x == pytest.approx(15)
        assert last(fired).y == edge

    def test_ends_on_the_edge_however_far_past_it_the_last_step_went(self) -> None:
        # Climbs from 0 to 2e30 within one step, 3 units from the shooter.
        big = 10**30
        fired = fire_at(battlefield(), f"{big}(tanh(1000000(x - 3.005)) + tanh(3005000))")

        assert last(fired).y == HEIGHT
        assert 8 <= last(fired).x <= 8.01


class TestBreaks:
    def test_stops_where_the_function_becomes_undefined(self) -> None:
        fired = fire_at(battlefield(), "sqrt(5 - x) - sqrt(5)")

        assert fired.ending is Ending.UNDEFINED
        assert last(fired).x == pytest.approx(10, abs=1e-6)

    def test_stops_at_a_break(self) -> None:
        fired = fire_at(battlefield(), "abs(x - 3.003)/(x - 3.003) + 1")

        assert fired.ending is Ending.BREAK
        assert last(fired).x == pytest.approx(8.003, abs=1e-6)


class TestHits:
    def test_hits_a_player_in_its_path(self) -> None:
        fired = fire_at(battlefield(), "0")

        assert fired.ending is Ending.HIT_PLAYER
        assert fired.hit == "bo"
        # Where it first touches them.
        assert last(fired) == pytest.approx(Point(35 - PLAYER_RADIUS, 10))

    def test_hits_a_player_when_fired_left(self) -> None:
        fired = fire_at(battlefield(), "0", Direction.LEFT, shooter="bo")

        assert fired.hit == "ada"
        assert last(fired) == pytest.approx(Point(5 + PLAYER_RADIUS, 10))

    @pytest.mark.parametrize(("height", "hits"), [("0.499999", True), ("0.500001", False)])
    def test_grazing_a_player_hits_them(self, height: str, hits: bool) -> None:
        # Steps up to `height` well before bo, then passes over their top, at
        # PLAYER_RADIUS, a whisker inside or outside their circle.
        step_up = f"{height}(tanh(1000000(x - 15.005)) + tanh(15005000))/2"

        assert (fire_at(battlefield(), step_up).hit == "bo") is hits

    def test_misses_a_player_it_passes_over(self) -> None:
        fired = fire_at(battlefield(), "x/10")

        assert fired.hit is None

    def test_does_not_hit_the_shooter(self) -> None:
        # Drops straight down through the shooter's own circle.
        fired = fire_at(battlefield(), "-1000x")

        assert fired.ending is Ending.EDGE
        assert last(fired).y == 0

    def test_hits_the_first_player_along_the_path(self) -> None:
        players = {"ada": Point(5, 10), "bo": Point(35, 10), "cy": Point(20, 10)}

        assert fire_at(battlefield(players), "0").hit == "cy"

    def test_stops_at_an_obstacle(self) -> None:
        wall = Circle(Point(20, 10), 2)
        fired = fire_at(battlefield(obstacles=(wall,)), "0")

        assert fired.ending is Ending.HIT_OBSTACLE
        assert fired.hit is None
        assert last(fired) == pytest.approx(Point(18, 10))

    def test_obstacle_shields_a_player_behind_it(self) -> None:
        wall = Circle(Point(34, 10), 2)  # overlaps bo, on the near side

        assert fire_at(battlefield(obstacles=(wall,)), "0").ending is Ending.HIT_OBSTACLE

    def test_player_in_front_of_an_obstacle_is_hit(self) -> None:
        wall = Circle(Point(37.5, 10), 2)  # touches bo, on the far side

        assert fire_at(battlefield(obstacles=(wall,)), "0").hit == "bo"

    def test_hits_are_judged_along_the_path_not_by_list_order(self) -> None:
        near = Circle(Point(10, 10), 1)
        far = Circle(Point(20, 10), 1)
        fired = fire_at(battlefield(obstacles=(far, near)), "0")

        assert last(fired) == pytest.approx(Point(9, 10))

    def test_hits_what_a_steep_step_passes_through(self) -> None:
        # Climbs 9 units within one sample step, straight through an obstacle
        # that no sample lands in.
        wall = Circle(Point(8.005, 14), 0.1)
        step_up = "4.5(tanh(100000(x - 3.005)) + tanh(300500))"
        fired = fire_at(battlefield(obstacles=(wall,)), step_up)

        assert fired.ending is Ending.HIT_OBSTACLE

    def test_a_break_comes_before_anything_beyond_it(self) -> None:
        fired = fire_at(battlefield(), "sqrt(5 - x) - sqrt(5)")

        assert fired.hit is None
