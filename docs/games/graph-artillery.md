# Graph artillery

Working title. A turn-based artillery game for two or more players. On your
turn you type a function, such as `sin(x) * 2`, and your shot travels along its
graph across the battlefield. Hit an opponent to knock them out; obstacles
block shots.

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

## Roadmap

Each step is one reviewable pull request. These steps build on the site's
rooms and client scaffold (see the site roadmap).

1. Expression parser and evaluator for player-entered functions.
2. Simulation: battlefield, obstacles, shot tracing, hit detection.
3. Game rules on top of rooms: turn order, elimination, winning.
4. UI: battlefield rendering, function input, turn flow.
