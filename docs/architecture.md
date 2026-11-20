# Architecture

A short map of how the site fits together and why. Update it when a decision
here changes.

## Shape of the system

```
browser (React + TypeScript)  ──HTTP / WebSocket──▶  server (Python, FastAPI)
  draws the game, sends input                       password gate, rooms, game rules
```

- **One deployable.** The server serves the built client as static files, so
  production is a single process on a single origin. No CORS, and the password
  cookie covers everything.
- **The server is authoritative.** Players send what they typed (for example a
  function like `sin(x) * 2`). The server parses it, simulates the shot, and
  sends the result to everyone in the room. The client never decides outcomes,
  so cheating would take more than editing browser code, and the rules exist in
  exactly one place.
- **Function input is parsed, never executed.** Expressions go through a small
  parser that accepts a fixed grammar, never `eval`.
- **One shared password gates the whole site**, enforced in the server before
  any page, asset, or WebSocket is served. The password and the cookie-signing
  key come from environment variables and are never committed.

## Repository layout

```
server/   Python backend (see server/README.md)
client/   React frontend (added in a later PR)
docs/     design notes like this one
```

## Roadmap

Each step is one reviewable pull request.

1. Server scaffold, tooling, and CI.
2. Password gate: login page, signed session cookie, login rate limiting.
3. Client scaffold: Vite + React + TypeScript, served by the server.
4. Expression parser and evaluator for player-entered functions.
5. Game simulation: battlefield, obstacles, shot tracing, hit detection.
6. Rooms and the WebSocket protocol: create/join, turn order, broadcasts.
7. Game UI: battlefield rendering, function input, turn flow.
8. Packaging: Dockerfile and deployment notes.
