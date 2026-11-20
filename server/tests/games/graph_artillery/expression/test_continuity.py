import math

import pytest

from games_server.games.graph_artillery.expression import parse, vocabulary
from games_server.games.graph_artillery.expression.continuity import Interval, value_range


def range_of(source: str, low: float, high: float) -> Interval | None:
    return value_range(parse(source).tree, low, high)


@pytest.mark.parametrize(
    ("source", "low", "high"),
    [
        ("x^3 - 2x + 1", -2, 2),
        ("(x - 1)^2", 0, 3),
        ("x^-2", 0.5, 3),
        ("(-x)^3", 1, 2),
        ("x^0.5", 0, 4),
        ("x^x", 0.1, 3),
        ("2^-x", -3, 3),
        ("sin(x)", 0, 7),
        ("sin(x)", 1, 2),
        ("cos(x)", 2, 4),
        ("tan(x)", -1.5, 1.5),
        ("asin(x/2)", -1, 2),
        ("acos(x)", -0.5, 1),
        ("atan(x) + tanh(x) + sinh(x)", -3, 3),
        ("cosh(x)", -1, 2),
        ("exp(x) - ln(x) - log(x)", 0.5, 3),
        ("sqrt(x)", 0, 9),
        ("abs(x - 1)", 0, 3),
        ("1/(x + 3)", 0, 2),
        ("x / (x^2 + 1)", -2, 2),
        ("2/(1 + exp(-1000(x - 3)))", 0, 6),
    ],
)
def test_range_contains_every_value(source: str, low: float, high: float) -> None:
    f = parse(source)
    found = value_range(f.tree, low, high)

    assert found is not None
    for i in range(101):
        x = low + (high - low) * i / 100
        assert found.low <= f(x) <= found.high, f"x = {x}"


@pytest.mark.parametrize(
    ("source", "low", "high"),
    [
        ("1/(x - pi)", 3, 4),  # a divisor that passes through 0
        ("sin(x - pi)/(x - pi)", 3, 4),  # even when the gap is a single point
        ("sqrt(x)", -1, 1),
        ("ln(x)", 0, 1),  # ln needs strictly more than 0
        ("log(x)", -2, -1),
        ("asin(x)", 0, 1.5),
        ("acos(x)", -1.5, 0),
        ("tan(x)", 1, 2),  # a pole at pi/2
        ("tan(x)", 4, 5),  # and every pi further on
        ("x^-1", -1, 1),  # 0 to a negative power
        ("x^0.5", -1, 1),  # a negative base to a fractional power
        ("x^x", -1, 1),  # a negative base to a varying power
        ("exp(1000x) - exp(1000x)", 1, 2),  # infinity minus infinity
        ("sin(exp(1000x))", 1, 2),  # sin of infinity
    ],
)
def test_cannot_prove_a_step_outside_its_domain(source: str, low: float, high: float) -> None:
    assert range_of(source, low, high) is None


def test_domain_edge_itself_is_fine() -> None:
    assert range_of("sqrt(x)", 0, 1) == Interval(0, 1)


def test_even_power_of_a_range_through_zero_starts_at_zero() -> None:
    assert range_of("(x - 3)^2", 2, 4) == Interval(0, 1)


def test_repeating_x_makes_the_range_rougher() -> None:
    # The known limit: each factor is treated as free to vary on its own.
    assert range_of("(x - 3)*(x - 3)", 2, 4) == Interval(-1, 1)


def test_sin_reaches_its_peak_inside_the_range() -> None:
    assert range_of("sin(x)", 1, 2) == Interval(math.sin(1), 1)


def test_overflow_along_the_way_is_fine() -> None:
    assert range_of("1/(1 + exp(-1000x))", -2, -1) == Interval(0, 0)


@pytest.mark.parametrize("name", sorted(vocabulary.FUNCTIONS))
def test_every_function_has_an_interval_version(name: str) -> None:
    assert range_of(f"{name}(x)", 0.1, 0.2) is not None


def test_expression_reports_continuity() -> None:
    f = parse("1/(x - 2)")

    assert f.is_continuous(0, 1)
    assert not f.is_continuous(1, 3)
