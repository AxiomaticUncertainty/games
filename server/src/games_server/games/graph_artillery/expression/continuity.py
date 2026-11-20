"""Proves that an expression is continuous over a whole stretch of x.

Sampling can't show continuity: `sin(x - pi)/(x - pi)` is undefined at exactly
one number, and no sample will ever land on it. But every function in the
vocabulary, and every operator, is continuous wherever it is defined. So an
expression is continuous on [low, high] if every step of it stays inside its
domain for every x in [low, high]: no divisor can be 0, no `sqrt` argument
negative, no `tan` argument at a pole, and so on.

That is checked with interval arithmetic: instead of evaluating each step at
one x, it is evaluated over all of them at once, giving a range of values that
contains every value it could take. `x - pi` over [3, 4] is [3 - pi, 4 - pi],
which contains 0, so `1/(x - pi)` is not provably defined there.

Two limits, both on the cautious side:

- Ranges can come out wider than the truth when x appears more than once.
  `(x - 3)*(x - 3)` over [2, 4] is treated as [-1, 1], since each factor could
  be anywhere in [-1, 1] independently, though it is really [0, 1]. So
  `sqrt((x - 3)*(x - 3))` can't be proven defined around 3. `(x - 3)^2` can:
  powers are handled exactly.
- Ranges are computed with ordinary floating-point rounding, not rounded
  outward, so they are as precise as evaluating the expression at a point, no
  more.
"""

import math
from collections.abc import Callable, Mapping
from types import MappingProxyType
from typing import NamedTuple

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


class Interval(NamedTuple):
    """Every number from `low` to `high`, inclusive. Either may be infinite."""

    low: float
    high: float

    def contains_zero(self) -> bool:
        return self.low <= 0 <= self.high


def value_range(tree: Node, low: float, high: float) -> Interval | None:
    """The values `tree` takes over [low, high], or None if it isn't provably
    defined on all of it."""
    try:
        return _range(tree, Interval(low, high))
    except _Unproven, ValueError, ArithmeticError:
        # ValueError and ArithmeticError: math refused an endpoint, as with
        # sin(inf). The point evaluator treats those as undefined too.
        return None


class _Unproven(Exception):
    """Some step can't be shown to stay inside its domain."""


def _require(condition: bool) -> None:
    if not condition:
        raise _Unproven


def _range(node: Node, x: Interval) -> Interval:
    match node:
        case Number(value):
            result = Interval(value, value)
        case Variable():
            result = x
        case Negate(operand):
            inner = _range(operand, x)
            result = Interval(-inner.high, -inner.low)
        case BinaryOp(operator, left, right):
            result = _OPERATORS[operator](_range(left, x), _range(right, x))
        case Call(function, argument):
            result = _FUNCTIONS[function](_range(argument, x))
    # NaN means infinities met with no answer, as in inf - inf, which the
    # point evaluator treats as undefined.
    _require(not math.isnan(result.low) and not math.isnan(result.high))
    return result


def _spanning(*values: float) -> Interval:
    return Interval(min(values), max(values))


# Operators


def _add(a: Interval, b: Interval) -> Interval:
    return Interval(a.low + b.low, a.high + b.high)


def _subtract(a: Interval, b: Interval) -> Interval:
    return Interval(a.low - b.high, a.high - b.low)


def _multiply(a: Interval, b: Interval) -> Interval:
    return _spanning(a.low * b.low, a.low * b.high, a.high * b.low, a.high * b.high)


def _divide(a: Interval, b: Interval) -> Interval:
    _require(not b.contains_zero())
    return _multiply(a, Interval(1 / b.high, 1 / b.low))


def _power(base: Interval, exponent: Interval) -> Interval:
    if exponent.low == exponent.high:
        return _constant_power(base, exponent.low)
    # A varying exponent needs a positive base: a negative base only has a
    # value at whole-number exponents, and 0 only at positive ones.
    _require(base.low > 0 or (base.low >= 0 and exponent.low > 0))
    # For a positive base, base^exponent rises or falls steadily in each, so
    # its extremes are at the corners.
    return _spanning(*(vocabulary.power(b, e) for b in (base.low, base.high) for e in exponent))


def _constant_power(base: Interval, n: float) -> Interval:
    ends = (vocabulary.power(base.low, n), vocabulary.power(base.high, n))
    if not n.is_integer():
        # Only defined for a base of at least 0, or above 0 for n < 0.
        _require(base.low > 0 or (base.low >= 0 and n > 0))
        return _spanning(*ends)
    if n < 0:
        _require(not base.contains_zero())
    elif n % 2 == 0 and base.low < 0 < base.high:
        # An even power dips to 0 between a negative and a positive end.
        return Interval(0.0, max(ends))
    return _spanning(*ends)


_OPERATORS: Mapping[Operator, Callable[[Interval, Interval], Interval]] = MappingProxyType(
    {
        Operator.ADD: _add,
        Operator.SUBTRACT: _subtract,
        Operator.MULTIPLY: _multiply,
        Operator.DIVIDE: _divide,
        Operator.POWER: _power,
    }
)


# Functions


def _increasing(name: str) -> Callable[[Interval], Interval]:
    """For a function that rises over its whole domain."""
    f = vocabulary.FUNCTIONS[name]
    return lambda a: Interval(f(a.low), f(a.high))


def _with_domain(
    name: str, accepts: Callable[[Interval], bool], *, increasing: bool = True
) -> Callable[[Interval], Interval]:
    """For a function that rises (or falls) steadily, but only on part of the line."""
    f = vocabulary.FUNCTIONS[name]

    def range_of(a: Interval) -> Interval:
        _require(accepts(a))
        return Interval(f(a.low), f(a.high)) if increasing else Interval(f(a.high), f(a.low))

    return range_of


def _wave(name: str, peak: float) -> Callable[[Interval], Interval]:
    """For sin and cos: 1 at `peak` and -1 half a turn later, every full turn."""
    f = vocabulary.FUNCTIONS[name]

    def range_of(a: Interval) -> Interval:
        _require(math.isfinite(a.low) and math.isfinite(a.high))
        low, high = sorted((f(a.low), f(a.high)))
        if _includes_one_of(a, peak, math.tau):
            high = 1.0
        if _includes_one_of(a, peak + math.pi, math.tau):
            low = -1.0
        return Interval(low, high)

    return range_of


def _tan(a: Interval) -> Interval:
    _require(math.isfinite(a.low) and math.isfinite(a.high))
    # Poles at pi/2, and every pi either side.
    _require(not _includes_one_of(a, math.pi / 2, math.pi))
    return Interval(math.tan(a.low), math.tan(a.high))


def _cosh(a: Interval) -> Interval:
    cosh = vocabulary.FUNCTIONS["cosh"]
    ends = (cosh(a.low), cosh(a.high))
    # Lowest, at 1, where the argument is 0.
    return Interval(1.0, max(ends)) if a.contains_zero() else _spanning(*ends)


def _abs(a: Interval) -> Interval:
    ends = (abs(a.low), abs(a.high))
    return Interval(0.0, max(ends)) if a.contains_zero() else _spanning(*ends)


def _includes_one_of(a: Interval, start: float, step: float) -> bool:
    """Whether `a` includes any of start + k*step, for whole numbers k."""
    first_at_or_after_low = start + math.ceil((a.low - start) / step) * step
    return first_at_or_after_low <= a.high


def _within(low: float, high: float) -> Callable[[Interval], bool]:
    return lambda a: low <= a.low and a.high <= high


# One entry per entry in vocabulary.FUNCTIONS.
_FUNCTIONS: Mapping[str, Callable[[Interval], Interval]] = MappingProxyType(
    {
        "sin": _wave("sin", peak=math.pi / 2),
        "cos": _wave("cos", peak=0.0),
        "tan": _tan,
        "asin": _with_domain("asin", _within(-1, 1)),
        "acos": _with_domain("acos", _within(-1, 1), increasing=False),
        "atan": _increasing("atan"),
        "sinh": _increasing("sinh"),
        "cosh": _cosh,
        "tanh": _increasing("tanh"),
        "exp": _increasing("exp"),
        "ln": _with_domain("ln", lambda a: a.low > 0),
        "log": _with_domain("log", lambda a: a.low > 0),
        "sqrt": _with_domain("sqrt", lambda a: a.low >= 0),
        "abs": _abs,
    }
)
