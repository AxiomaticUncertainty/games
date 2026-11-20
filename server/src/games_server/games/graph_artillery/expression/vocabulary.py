"""Every name a player may use. Anything not listed here is rejected.

To offer a new function, add it to FUNCTIONS. It must take one float and
return a float, raising ValueError or ArithmeticError where it's undefined
(as the `math` module does), and it must be listed in the game's doc. A result
too large to represent must come back as an infinity, not an OverflowError: it
is defined, just large, and later steps may bring it back down, as in
`1/(1 + exp(1000))`.
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
