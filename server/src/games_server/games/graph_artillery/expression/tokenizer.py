"""Splits expression text into tokens: numbers, names, and symbols."""

import re
from dataclasses import dataclass
from enum import Enum, auto

from games_server.games.graph_artillery.expression.errors import ParseError


class Kind(Enum):
    NUMBER = auto()
    NAME = auto()
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    CARET = auto()
    LEFT_PAREN = auto()
    RIGHT_PAREN = auto()
    END = auto()  # always the last token, so the parser never runs off the end


@dataclass(frozen=True)
class Token:
    kind: Kind
    text: str
    position: int  # index of the token's first character in the source text


# ASCII only on purpose: str.isdigit() and str.isalpha() also accept characters
# like "²" and "π", which would then fail in confusing ways later on.
_NUMBER = re.compile(r"[0-9]+\.?[0-9]*|\.[0-9]+")
_NAME = re.compile(r"[A-Za-z]+")

_SYMBOLS = {
    "+": Kind.PLUS,
    "-": Kind.MINUS,
    "*": Kind.STAR,
    "/": Kind.SLASH,
    "^": Kind.CARET,
    "**": Kind.CARET,  # accepted as a synonym for ^, since programmers type it
    "(": Kind.LEFT_PAREN,
    ")": Kind.RIGHT_PAREN,
}
# Longest first, so "**" is read as one symbol rather than two "*".
_SYMBOLS_LONGEST_FIRST = sorted(_SYMBOLS.items(), key=lambda item: len(item[0]), reverse=True)


def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    position = 0
    while position < len(source):
        if source[position].isspace():
            position += 1
            continue
        token = _read_token(source, position)
        tokens.append(token)
        position += len(token.text)
    tokens.append(Token(Kind.END, "", len(source)))
    return tokens


def _read_token(source: str, position: int) -> Token:
    for symbol, kind in _SYMBOLS_LONGEST_FIRST:
        if source.startswith(symbol, position):
            return Token(kind, symbol, position)
    if number := _NUMBER.match(source, position):
        return Token(Kind.NUMBER, number.group(), position)
    if name := _NAME.match(source, position):
        return Token(Kind.NAME, name.group(), position)
    raise ParseError(f"Unexpected character {source[position]!r}.", position)
