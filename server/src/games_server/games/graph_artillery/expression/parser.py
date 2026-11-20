"""Turns tokens into a tree, using recursive descent.

The grammar, from lowest precedence to highest. Each rule is one method below.

    sum      := product (("+" | "-") product)*
    product  := unary (("*" | "/") unary | <implicit> power)*
    unary    := ("+" | "-") unary | power
    power    := primary ("^" unary)?
    primary  := NUMBER | "x" | CONSTANT | FUNCTION "(" sum ")" | "(" sum ")"

Some consequences worth knowing:

- Implicit multiplication: a name or "(" right after a value multiplies it,
  so `2x`, `3sin(x)` and `(x+1)(x-1)` work. A number right after a value does
  not (`x2` is an error), because that is more often a typo than intended.
- `-x^2` means `-(x^2)`, and `2^-x` is allowed, as in ordinary maths notation.
- `^` groups to the right: `2^3^2` means `2^(3^2)`.
- Names are case-insensitive: `Sin(X)` is the same as `sin(x)`.
"""

from games_server.games.graph_artillery.expression import vocabulary
from games_server.games.graph_artillery.expression.errors import ParseError
from games_server.games.graph_artillery.expression.evaluator import Expression
from games_server.games.graph_artillery.expression.nodes import (
    BinaryOp,
    Call,
    Negate,
    Node,
    Number,
    Operator,
    Variable,
)
from games_server.games.graph_artillery.expression.tokenizer import Kind, Token, tokenize

# Long enough for any reasonable shot. The limit also bounds how deeply the
# parser can recurse, so no input can exhaust Python's recursion limit.
MAX_LENGTH = 200

_SUM_OPERATORS = {Kind.PLUS: Operator.ADD, Kind.MINUS: Operator.SUBTRACT}
_PRODUCT_OPERATORS = {Kind.STAR: Operator.MULTIPLY, Kind.SLASH: Operator.DIVIDE}
# Tokens that start an implicitly multiplied factor, as in `2x` or `2(x+1)`.
_IMPLICIT_PRODUCT_STARTS = {Kind.NAME, Kind.LEFT_PAREN}


def parse(source: str) -> Expression:
    """Parse a player's function of x. Raises `ParseError` if it isn't valid."""
    if len(source) > MAX_LENGTH:
        raise ParseError(f"Keep it to {MAX_LENGTH} characters or fewer.", MAX_LENGTH)
    parser = _Parser(tokenize(source))
    tree = parser.sum()
    parser.expect_end()
    return Expression(source, tree)


class _Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._index = 0

    def sum(self) -> Node:
        node = self.product()
        while (operator := _SUM_OPERATORS.get(self._current.kind)) is not None:
            self._advance()
            node = BinaryOp(operator, node, self.product())
        return node

    def product(self) -> Node:
        node = self.unary()
        while True:
            if (operator := _PRODUCT_OPERATORS.get(self._current.kind)) is not None:
                self._advance()
                node = BinaryOp(operator, node, self.unary())
            elif self._current.kind in _IMPLICIT_PRODUCT_STARTS:
                node = BinaryOp(Operator.MULTIPLY, node, self.power())
            else:
                return node

    def unary(self) -> Node:
        if self._current.kind is Kind.MINUS:
            self._advance()
            return Negate(self.unary())
        if self._current.kind is Kind.PLUS:
            self._advance()
            return self.unary()
        return self.power()

    def power(self) -> Node:
        base = self.primary()
        if self._current.kind is not Kind.CARET:
            return base
        self._advance()
        # unary, not power: allows `2^-x`, and makes ^ group to the right.
        return BinaryOp(Operator.POWER, base, self.unary())

    def primary(self) -> Node:
        token = self._advance()
        if token.kind is Kind.NUMBER:
            return Number(float(token.text))
        if token.kind is Kind.NAME:
            return self._name(token)
        if token.kind is Kind.LEFT_PAREN:
            inner = self.sum()
            self._expect(Kind.RIGHT_PAREN, "Missing ')'.")
            return inner
        if token.kind is Kind.END:
            raise ParseError("The function ends too early.", token.position)
        raise ParseError(f"Expected a number, x, or '(' but found {token.text!r}.", token.position)

    def expect_end(self) -> None:
        token = self._current
        if token.kind is not Kind.END:
            raise ParseError(f"Unexpected {token.text!r}.", token.position)

    def _name(self, token: Token) -> Node:
        name = token.text.lower()
        if name == vocabulary.VARIABLE:
            return Variable()
        if name in vocabulary.CONSTANTS:
            return Number(vocabulary.CONSTANTS[name])
        if name in vocabulary.FUNCTIONS:
            self._expect(Kind.LEFT_PAREN, f"Expected '(' after {token.text!r}.")
            argument = self.sum()
            self._expect(Kind.RIGHT_PAREN, "Missing ')'.")
            return Call(name, argument)
        raise ParseError(f"Unknown name {token.text!r}.", token.position)

    @property
    def _current(self) -> Token:
        return self._tokens[self._index]

    def _advance(self) -> Token:
        token = self._current
        # Never step past END, so _current is always a real token.
        if token.kind is not Kind.END:
            self._index += 1
        return token

    def _expect(self, kind: Kind, message: str) -> None:
        if self._current.kind is not kind:
            raise ParseError(message, self._current.position)
        self._advance()
