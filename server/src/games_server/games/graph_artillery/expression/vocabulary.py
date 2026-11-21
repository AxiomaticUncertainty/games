"""Every name a player may use. Anything not listed here is rejected.

To offer a new function, add it to FUNCTIONS. It must take one float and
return a float, raising ValueError or ArithmeticError where it's undefined
(as the `math` module does), and it must be listed in the game's doc. A result
too large to represent must come back as an infinity, not an OverflowError: it
is defined, just large, and later steps may bring it back down, as in
`1/(1 + exp(1000))`. It also needs an interval version in `continuity`, which
can only prove continuity because every function here is continuous wherever
it is defined; a new function must be too.
"""

import math
from collections.abc import Callable, Mapping
from types import MappingProxyType


def _exp(x: float) -> float:
    try:
        return math.exp(x)
    except OverflowError:
        return math.inf


def _sinh(x: float) -> float:
    try:
        return math.sinh(x)
    except OverflowError:
        return math.copysign(math.inf, x)


def _cosh(x: float) -> float:
    try:
        return math.cosh(x)
    except OverflowError:
        return math.inf


def power(base: float, exponent: float) -> float:
    """`base ^ exponent`, which overflows to an infinity rather than raising."""
    # math.pow, not **: (-8) ** (1/3) quietly returns a complex number, while
    # math.pow raises ValueError, which the evaluator turns into NaN.
    try:
        return math.pow(base, exponent)
    except OverflowError:
        # Negative only for a negative base and an odd exponent; math.pow has
        # already rejected a negative base with a non-integer exponent.
        is_negative = base < 0 and exponent % 2 == 1
        return -math.inf if is_negative else math.inf


VARIABLE = "x"

CONSTANTS: Mapping[str, float] = MappingProxyType(
    {
        "pi": math.pi,
        "e": math.e,
    }
)

FUNCTIONS: Mapping[str, Callable[[float], float]] = MappingProxyType(
    {
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "asin": math.asin,
        "acos": math.acos,
        "atan": math.atan,
        # math raises OverflowError for these where the others can't overflow.
        "sinh": _sinh,
        "cosh": _cosh,
        "tanh": math.tanh,
        "exp": _exp,
        "ln": math.log,  # natural log
        "log": math.log10,  # base 10, as on most calculators
        "sqrt": math.sqrt,
        "abs": math.fabs,
    }
)
