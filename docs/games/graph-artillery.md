# Graph artillery

Working title. A turn-based artillery game for two or more players. On your
turn you type a function, such as `sin(x) * 2`, pick a direction, and your shot
travels along its graph across the battlefield. Hit an opponent to knock them
out; obstacles block shots.

This doc covers only what is specific to this game. The site-wide design (the
password gate, rooms, and the server deciding every outcome) is in
[../architecture.md](../architecture.md).

## Design decisions

- **Functions are parsed, never executed.** What a player types goes through a
  small parser that accepts a fixed grammar (numbers, `x`, arithmetic, and a
  set list of functions like `sin` and `sqrt`), never `eval`. Anything outside
  the grammar is rejected with a message pointing to the problem.
- **The server traces every shot.** The client sends the text the player typed.
  The server parses it, traces the path, decides what was hit, and sends the
  path to everyone in the room. The client only draws it.
- **Shots start at the shooter.** Paths are relative to the shooter, so the
  function must pass through (0, 0). `x - 5` is rejected, not shifted, and so
  is anything undefined at 0.
- **The player picks a direction, and firing left mirrors the graph.** A shot
  fired left follows `y = f(t)` at horizontal distance `t` to the left, so a
  function means the same thing whichever way the player faces: `x^2` arcs
  upward on either side. The other half of the graph is never used.
- **A shot stops at the first break in its curve**: where the function is
  undefined (`sqrt(5 - x)` beyond 5), where it jumps (`abs(x - 3)/(x - 3)` at
  3), or where it turns steeper than 100:1, which is vertical at battlefield
  scale. The last rule covers poles: `1/(x - 5)` stops where it turns vertical,
  shortly before 5. It also bounds how much work any shot can cost the
  server. `shot.py` explains how breaks are found.

## Function syntax

What players can type. The code that enforces it is in
`server/src/games_server/games/graph_artillery/expression/`; the parser's
docstring has the formal grammar.

| Kind | Allowed |
| --- | --- |
| Variable | `x` |
| Numbers | `3`, `2.5`, `.5` (no scientific notation) |
| Constants | `pi`, `e` |
| Operators | `+` `-` `*` `/` `^` (`**` also works for `^`), and parentheses |
| Functions | `sin` `cos` `tan` `asin` `acos` `atan` `sinh` `cosh` `tanh` `exp` `sqrt` `abs`, `ln` (natural log), `log` (base 10) |

- Multiplication can be implicit before a name or a parenthesis: `2x`,
  `3sin(x)`, `(x+1)(x-1)`.
- `-x^2` means `-(x^2)`, and `2^3^2` means `2^(3^2)`, as in ordinary notation.
- Names ignore case. Function arguments need parentheses: `sin(x)`, not
  `sin x`.
- At most 200 characters.

## Roadmap

Each step is one reviewable pull request. Steps 1 to 3 stand alone; steps 4
and 5 build on the site's rooms and client scaffold (see the site roadmap).

1. Expression parser and evaluator for player-entered functions.
2. Shot paths: starting at the shooter, direction, stopping at breaks.
3. Battlefield: players, obstacles, and what a shot's path hits.
4. Game rules on top of rooms: turn order, elimination, winning.
5. UI: battlefield rendering, function input, turn flow.
