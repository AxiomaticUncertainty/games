"""Computes the value of a parsed expression at a given x."""

import math
from dataclasses import dataclass

from games_server.games.graph_artillery.expression import continuity, vocabulary
from games_server.games.graph_artillery.expression.nodes import (
    BinaryOp,
    Call,
    Negate,
    Node,
    Number,
    Operator,
    Variable,
)


@dataclass(frozen=True)
class Expression:
    """A parsed function of x. Call it to evaluate: `f(1.5)`."""

    source: str  # the text the player typed
    tree: Node

    def __call__(self, x: float) -> float:
        return evaluate(self.tree, x)

    def first_break(self, low: float, high: float) -> float | None:
        """Where this stops being continuous in [low, high], or None if it doesn't.

        See `continuity.first_break`, which this is.
        """
        return continuity.first_break(self.tree, low, high)


def evaluate(node: Node, x: float) -> float:
    """The value of `node` at `x`: always a finite float, or NaN where undefined.

    "Undefined" covers dividing by zero, leaving a function's domain (`sqrt(-1)`,
    `ln(0)`), and results too large to represent. Returning NaN rather than
    raising lets callers test one thing: `math.isnan(value)`.

    Only the result has to be representable. Along the way, a value too large
    to represent becomes an infinity, so `1/(1 + exp(-1000x))`, a steep step,
    is 0 at x = -1, as it should be. Where infinities meet in a way that has no
    answer, such as `exp(1000) - exp(1000)`, the result is undefined.
    """
    try:
        value = _evaluate(node, x)
    except ArithmeticError, ValueError:
        # math raises ValueError outside a function's domain, and dividing by
        # zero raises ZeroDivisionError.
        return math.nan
    return value if math.isfinite(value) else math.nan


def _evaluate(node: Node, x: float) -> float:
    match node:
        case Number(value):
            return value
        case Variable():
            return x
        case Negate(operand):
            return -_evaluate(operand, x)
        case BinaryOp(operator, left, right):
            return _apply(operator, _evaluate(left, x), _evaluate(right, x))
        case Call(function, argument):
            return vocabulary.FUNCTIONS[function](_evaluate(argument, x))


def _apply(operator: Operator, left: float, right: float) -> float:
    match operator:
        case Operator.ADD:
            return left + right
        case Operator.SUBTRACT:
            return left - right
        case Operator.MULTIPLY:
            return left * right
        case Operator.DIVIDE:
            return left / right
        case Operator.POWER:
            return vocabulary.power(left, right)
