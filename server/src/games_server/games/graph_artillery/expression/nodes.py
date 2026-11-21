"""The tree a parsed expression becomes.

For example, `2sin(x) + 1` parses to:

    BinaryOp(ADD,
        BinaryOp(MULTIPLY, Number(2.0), Call("sin", Variable())),
        Number(1.0))

Constants such as `pi` are replaced by their value while parsing, so they
appear here as plain `Number`s.
"""

from dataclasses import dataclass
from enum import Enum


class Operator(Enum):
    ADD = "+"
    SUBTRACT = "-"
    MULTIPLY = "*"
    DIVIDE = "/"
    POWER = "^"


@dataclass(frozen=True)
class Number:
    value: float


@dataclass(frozen=True)
class Variable:
    """The function's input, x."""


@dataclass(frozen=True)
class Negate:
    operand: Node


@dataclass(frozen=True)
class BinaryOp:
    operator: Operator
    left: Node
    right: Node


@dataclass(frozen=True)
class Call:
    function: str  # a key of vocabulary.FUNCTIONS
    argument: Node


type Node = Number | Variable | Negate | BinaryOp | Call
