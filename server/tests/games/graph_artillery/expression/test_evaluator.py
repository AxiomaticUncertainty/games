import math

import pytest

from games_server.games.graph_artillery.expression import parse


@pytest.mark.parametrize(
    ("source", "x", "expected"),
    [
        ("x", 3, 3),
        ("2x + 1", 3, 7),
        ("x^2 - 2x", 3, 3),
        ("-x^2", 3, -9),
        ("2^3^2", 0, 512),
        ("(x + 1)(x - 1)", 3, 8),
        ("10 / 4", 0, 2.5),
        ("sin(pi / 2)", 0, 1),
        ("cos(0) + exp(0)", 0, 2),
        ("ln(e)", 0, 1),
        ("log(1000)", 0, 3),
        ("sqrt(x)", 16, 4),
        ("abs(x)", -2.5, 2.5),
        ("2^-x", 1, 0.5),
        ("x**2", 4, 16),
    ],
)
def test_computes_the_value_at_x(source: str, x: float, expected: float) -> None:
    assert parse(source)(x) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("source", "x"),
    [
        ("1 / x", 0),  # division by zero
        ("sqrt(x)", -1),  # outside the domain
        ("ln(x)", 0),
        ("log(x)", -5),
        ("asin(x)", 2),
        ("x^(1/3)", -8),  # would be a complex number
        ("0^x", -1),
        ("exp(x)", 1000),  # overflow inside a function
        ("x^x", 1000),  # overflow in an operator
        ("x * 10^308 * 10", 1),  # overflow to infinity in plain arithmetic
    ],
)
def test_undefined_points_give_nan(source: str, x: float) -> None:
    assert math.isnan(parse(source)(x))


def test_one_parse_can_be_evaluated_at_many_points() -> None:
    f = parse("x^2")

    assert [f(x) for x in (-2, 0, 2)] == [4, 0, 4]
