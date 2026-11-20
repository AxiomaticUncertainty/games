"""Player-entered functions of x, such as `2sin(x) + x^2/10`.

Text is turned into a value in three stages, one module each:

    text --tokenizer--> tokens --parser--> tree (nodes) --evaluator--> number

Nothing here ever executes the player's text as code. The tokenizer accepts
only a handful of characters, and the parser accepts only the names listed in
`vocabulary`, so anything else is rejected before evaluation.

`continuity` evaluates the same tree over a whole range of x at once, to prove
the function has no breaks there.

Usage:

    f = parse("2sin(x)")
    f(1.5)  # 1.99498...
    f.is_continuous(0, 10)  # True
"""

from games_server.games.graph_artillery.expression.errors import ParseError
from games_server.games.graph_artillery.expression.evaluator import Expression
from games_server.games.graph_artillery.expression.parser import MAX_LENGTH, parse

__all__ = ["MAX_LENGTH", "Expression", "ParseError", "parse"]
