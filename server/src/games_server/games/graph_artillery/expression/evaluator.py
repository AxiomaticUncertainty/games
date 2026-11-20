"""Computes the value of a parsed expression at a given x."""

import math
from dataclasses import dataclass

from games_server.games.graph_artillery.expression import vocabulary
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


def evaluate(node: Node, x: float) -> float:
    """The value of `node` at `x`: always a finite float, or NaN where undefined.

    "Undefined" covers dividing by zero, leaving a function's domain (`sqrt(-1)`,
    `ln(0)`), and results too large to represent. Returning NaN rather than
    raising lets callers test one thing: `math.isnan(value)`.
    """
    try:
        value = _evaluate(node, x)
    except ArithmeticError, ValueError:
        # math raises ValueError outside a function's domain; ZeroDivisionError
        # and OverflowError are both ArithmeticErrors.
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
            # math.pow, not **: (-8) ** (1/3) quietly returns a complex number,
            # while math.pow raises ValueError, which evaluate() turns into NaN.
            return math.pow(left, right)
