import math

import pytest

from games_server.games.graph_artillery.expression import parse, vocabulary
from games_server.games.graph_artillery.expression.continuity import (
    BREAK_PRECISION,
    Interval,
    TooRough,
    value_range,
)


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


class TestFirstBreak:
    def test_none_for_a_continuous_function(self) -> None:
        assert parse("sin(1000000x) + exp(x)").first_break(0, 10) is None

    def test_finds_a_divisor_reaching_zero(self) -> None:
        found = parse("1/(x - 3.003)").first_break(0, 10)

        assert found is not None
        assert 3.003 - BREAK_PRECISION <= found < 3.003

    def test_finds_a_single_missing_point(self) -> None:
        found = parse("sin(x - pi)/(x - pi)").first_break(0, 10)

        assert found == pytest.approx(math.pi, abs=BREAK_PRECISION)

    def test_finds_the_first_of_several(self) -> None:
        found = parse("tan(x)").first_break(0, 10)

        assert found == pytest.approx(math.pi / 2, abs=BREAK_PRECISION)

    def test_function_is_defined_at_the_answer(self) -> None:
        f = parse("sqrt(5 - x)")
        found = f.first_break(0, 10)

        assert found is not None
        assert not math.isnan(f(found))

    def test_rough_over_the_whole_but_fine_in_parts_is_no_break(self) -> None:
        # Over [0, 6] the repeated (x - 3) makes the sqrt argument look
        # possibly negative; over each half, it can't be.
        source = "sqrt((x - 3)*(x - 3) + 0.5)"
        assert range_of(source, 0, 6) is None

        assert parse(source).first_break(0, 6) is None

    def test_gives_up_when_the_ranges_stay_too_rough(self) -> None:
        # Mathematically just 1, but each 1000x*x could be anywhere in its
        # range independently, so the divisor seems to include 0 until
        # stretches are tiny.
        with pytest.raises(TooRough):
            parse("1/(1000x*x - 1000x*x + 1)").first_break(0, 20)
