"""Every name a player may use. Anything not listed here is rejected.

To offer a new function, add it to FUNCTIONS. It must take one float and
return a float, raising ValueError or ArithmeticError where it's undefined
(as the `math` module does), and it must be listed in the game's doc.
"""

import math
from collections.abc import Callable, Mapping
from types import MappingProxyType

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
        "sinh": math.sinh,
        "cosh": math.cosh,
        "tanh": math.tanh,
        "exp": math.exp,
        "ln": math.log,  # natural log
        "log": math.log10,  # base 10, as on most calculators
        "sqrt": math.sqrt,
        "abs": math.fabs,
    }
)
