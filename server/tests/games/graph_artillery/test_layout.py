import math
import random
from collections.abc import Iterator

import pytest

from games_server.games.graph_artillery.battlefield import PLAYER_RADIUS, Battlefield
from games_server.games.graph_artillery.layout import (
    EDGE_MARGIN,
    HEIGHT,
    MAX_OBSTACLE_RADIUS,
    MAX_OBSTACLES,
    MIN_OBSTACLE_RADIUS,
    MIN_OBSTACLES,
    OBSTACLE_CLEARANCE,
    PLAYER_SPACING,
    WIDTH,
    NoRoom,
    random_battlefield,
)

PLAYERS = ["ada", "bo", "cy", "di"]
SEEDS = range(200)


def generate(seed: int, players: list[str] = PLAYERS) -> Battlefield:
    return random_battlefield(players, random.Random(seed))


def every_battlefield() -> Iterator[tuple[int, Battlefield]]:
    """A battlefield for each of SEEDS, with its seed for failure messages."""
    for seed in SEEDS:
        yield seed, generate(seed)


class TestEveryBattlefield:
    """Rules every generated battlefield follows, checked over many seeds."""

    def test_has_the_standard_size(self) -> None:
        for seed, field in every_battlefield():
            assert (field.width, field.height) == (WIDTH, HEIGHT), f"seed {seed}"

    def test_places_every_player_once(self) -> None:
        for seed, field in every_battlefield():
            assert list(field.players) == PLAYERS, f"seed {seed}"

    def test_obstacles_are_within_limits(self) -> None:
        for seed, field in every_battlefield():
            assert MIN_OBSTACLES <= len(field.obstacles) <= MAX_OBSTACLES, f"seed {seed}"
            for obstacle in field.obstacles:
                assert MIN_OBSTACLE_RADIUS <= obstacle.radius <= MAX_OBSTACLE_RADIUS, f"seed {seed}"
                assert 0 <= obstacle.center.x <= WIDTH, f"seed {seed}"
                assert 0 <= obstacle.center.y <= HEIGHT, f"seed {seed}"

    def test_players_are_clear_of_obstacles(self) -> None:
        for seed, field in every_battlefield():
            for position in field.players.values():
                for obstacle in field.obstacles:
                    gap = math.dist(position, obstacle.center) - obstacle.radius - PLAYER_RADIUS
                    assert gap >= OBSTACLE_CLEARANCE, f"seed {seed}"

    def test_players_are_away_from_the_edges(self) -> None:
        for seed, field in every_battlefield():
            for position in field.players.values():
                assert EDGE_MARGIN <= position.x <= WIDTH - EDGE_MARGIN, f"seed {seed}"
                assert EDGE_MARGIN <= position.y <= HEIGHT - EDGE_MARGIN, f"seed {seed}"

    def test_players_are_spaced_apart(self) -> None:
        for seed, field in every_battlefield():
            positions = list(field.players.values())
            for i, position in enumerate(positions):
                for other in positions[i + 1 :]:
                    assert math.dist(position, other) >= PLAYER_SPACING, f"seed {seed}"


class TestSeeds:
    def test_same_seed_gives_the_same_battlefield(self) -> None:
        assert generate(7) == generate(7)

    def test_different_seeds_give_different_battlefields(self) -> None:
        assert generate(7) != generate(8)


class TestPlayerCounts:
    def test_eight_players_always_fit(self) -> None:
        players = [f"player {n}" for n in range(8)]

        for seed in SEEDS:
            assert len(generate(seed, players).players) == 8, f"seed {seed}"

    def test_too_many_players_dont_fit(self) -> None:
        # Spaced PLAYER_SPACING apart, a battlefield holds a couple of dozen
        # at the very most.
        players = [f"player {n}" for n in range(40)]

        with pytest.raises(NoRoom, match="40 players"):
            generate(0, players)

    def test_each_player_must_be_listed_once(self) -> None:
        with pytest.raises(ValueError, match="listed once"):
            generate(0, ["ada", "bo", "ada"])
