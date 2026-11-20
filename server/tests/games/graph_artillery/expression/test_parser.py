import math

import pytest

from games_server.games.graph_artillery.expression import MAX_LENGTH, ParseError, parse
from games_server.games.graph_artillery.expression.nodes import (
    BinaryOp,
    Call,
    Negate,
    Node,
    Number,
    Operator,
    Variable,
)

X = Variable()
ADD = Operator.ADD
SUB = Operator.SUBTRACT
MUL = Operator.MULTIPLY
DIV = Operator.DIVIDE
POW = Operator.POWER


def tree(source: str) -> Node:
    return parse(source).tree


class TestStructure:
    def test_multiplication_binds_tighter_than_addition(self) -> None:
        assert tree("1 + 2 * x") == BinaryOp(ADD, Number(1), BinaryOp(MUL, Number(2), X))

    def test_same_precedence_groups_left_to_right(self) -> None:
        assert tree("x - 1 - 2") == BinaryOp(SUB, BinaryOp(SUB, X, Number(1)), Number(2))
        assert tree("x / 2 / 4") == BinaryOp(DIV, BinaryOp(DIV, X, Number(2)), Number(4))

    def test_power_groups_right_to_left(self) -> None:
        assert tree("2^3^x") == BinaryOp(POW, Number(2), BinaryOp(POW, Number(3), X))

    def test_negation_applies_after_power(self) -> None:
        assert tree("-x^2") == Negate(BinaryOp(POW, X, Number(2)))

    def test_exponent_may_be_negative(self) -> None:
        assert tree("2^-x") == BinaryOp(POW, Number(2), Negate(X))

    def test_parentheses_override_precedence(self) -> None:
        assert tree("(1 + 2) * x") == BinaryOp(MUL, BinaryOp(ADD, Number(1), Number(2)), X)

    def test_function_call(self) -> None:
        assert tree("sin(x + 1)") == Call("sin", BinaryOp(ADD, X, Number(1)))

    def test_constants_become_numbers(self) -> None:
        assert tree("pi") == Number(math.pi)
        assert tree("e") == Number(math.e)

    def test_names_are_case_insensitive(self) -> None:
        assert tree("SIN(X) + Pi") == tree("sin(x) + pi")


class TestImplicitMultiplication:
    @pytest.mark.parametrize(
        ("implicit", "explicit"),
        [
            ("2x", "2*x"),
            ("2 x", "2*x"),
            ("3sin(x)", "3*sin(x)"),
            ("2pi", "2*pi"),
            ("x(x + 1)", "x*(x + 1)"),
            ("(x + 1)(x - 1)", "(x + 1)*(x - 1)"),
        ],
    )
    def test_value_followed_by_name_or_paren_multiplies(self, implicit: str, explicit: str) -> None:
        assert tree(implicit) == tree(explicit)

    def test_binds_like_explicit_multiplication(self) -> None:
        assert tree("2x^2") == BinaryOp(MUL, Number(2), BinaryOp(POW, X, Number(2)))
        assert tree("1 + 2x") == BinaryOp(ADD, Number(1), BinaryOp(MUL, Number(2), X))

    def test_number_after_a_value_is_an_error(self) -> None:
        with pytest.raises(ParseError, match="'2'"):
            parse("x2")


class TestErrors:
    @pytest.mark.parametrize(
        ("source", "message", "position"),
        [
            ("", "ends too early", 0),
            ("x +", "ends too early", 3),
            ("(x + 1", "Missing '\\)'", 6),
            ("x + 1)", "Unexpected '\\)'", 5),
            ("sin x", "Expected '\\(' after 'sin'", 4),
            ("sin(x", "Missing '\\)'", 5),
            ("foo(x)", "Unknown name 'foo'", 0),
            ("y + 1", "Unknown name 'y'", 0),
            ("sinx", "Unknown name 'sinx'", 0),
            ("x * * 2", "found '\\*'", 4),
            ("+x", "found '\\+'", 0),
            ("1.2.3", "Unexpected '.3'", 3),
        ],
    )
    def test_reports_what_went_wrong_and_where(
        self, source: str, message: str, position: int
    ) -> None:
        with pytest.raises(ParseError, match=message) as error:
            parse(source)

        assert error.value.position == position

    def test_rejects_input_over_the_length_limit(self) -> None:
        parse("x" + "+x" * ((MAX_LENGTH - 1) // 2))  # just under the limit: fine

        with pytest.raises(ParseError, match="characters"):
            parse("x" * (MAX_LENGTH + 1))

    def test_deepest_input_that_fits_does_not_exhaust_the_stack(self) -> None:
        depth = (MAX_LENGTH - 1) // 2
        parse("(" * depth + "x" + ")" * depth)
        parse("-" * (MAX_LENGTH - 1) + "x")
        parse("x" + "^x" * ((MAX_LENGTH - 1) // 2))


class TestSafety:
    @pytest.mark.parametrize(
        "source",
        [
            "__import__('os').system('ls')",
            "x.__class__",
            "open('/etc/passwd')",
            "exec(x)",
            "lambda: 1",
            "x if x else 1",
            "[x]",
        ],
    )
    def test_code_is_rejected_not_executed(self, source: str) -> None:
        with pytest.raises(ParseError):
            parse(source)
