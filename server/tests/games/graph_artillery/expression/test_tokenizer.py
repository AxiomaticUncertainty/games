import pytest

from games_server.games.graph_artillery.expression.errors import ParseError
from games_server.games.graph_artillery.expression.tokenizer import Kind, tokenize


def kinds(source: str) -> list[Kind]:
    return [token.kind for token in tokenize(source)]


def test_splits_numbers_names_and_symbols() -> None:
    assert kinds("2*sin(x)-1.5") == [
        Kind.NUMBER,
        Kind.STAR,
        Kind.NAME,
        Kind.LEFT_PAREN,
        Kind.NAME,
        Kind.RIGHT_PAREN,
        Kind.MINUS,
        Kind.NUMBER,
        Kind.END,
    ]


def test_records_where_each_token_starts() -> None:
    assert [token.position for token in tokenize(" x +  12")] == [1, 3, 6, 8]


def test_ignores_whitespace() -> None:
    assert kinds("x+1") == kinds("  x \t+\n 1  ")


def test_double_star_means_power() -> None:
    assert kinds("x**2") == kinds("x^2")


@pytest.mark.parametrize("number", ["7", "3.25", "3.", ".5"])
def test_reads_number_forms(number: str) -> None:
    assert [token.text for token in tokenize(number)] == [number, ""]


def test_always_ends_with_end_token() -> None:
    assert kinds("") == [Kind.END]


@pytest.mark.parametrize(
    ("source", "position"),
    [
        ("x # 2", 2),
        ("x²", 1),  # superscript two: str.isdigit() would accept it
        ("π", 0),  # pi as a Greek letter: str.isalpha() would accept it
        ("x_1", 1),
        ("'x'", 0),
    ],
)
def test_rejects_characters_outside_the_language(source: str, position: int) -> None:
    with pytest.raises(ParseError) as error:
        tokenize(source)

    assert error.value.position == position
