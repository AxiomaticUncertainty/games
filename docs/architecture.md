# Architecture

A short map of how the site fits together and why. It covers what every game
shares. Each game has its own design notes under [games/](games/). Update this
file when a decision here changes.

## Shape of the system

```
browser (React + TypeScript)  ──HTTP / WebSocket──▶  server (Python, FastAPI)
  draws the game, sends input                       password gate, rooms, game rules
```

- **One deployable.** The server serves the built client as static files, so
  production is a single process on a single origin. No CORS, and the password
  cookie covers everything.
- **The server is authoritative.** Players send their moves; the server checks
  them against the game's rules, works out the result, and sends it to everyone
  in the room. The client never decides outcomes, so cheating would take more
  than editing browser code, and each game's rules exist in exactly one place.
- **Games are self-contained.** Each game lives in its own module on the server
  and the client, with its own doc in `docs/games/`. The site provides the
  shared pieces: the password gate, rooms, and player connections.
- **One shared password gates the whole site**, enforced in the server before
  any page, asset, or WebSocket is served. The server is given a hash of the
  password, never the password itself. The hash and the cookie-signing key come
  from environment variables and are never committed.

## Repository layout

```
server/   Python backend (see server/README.md)
client/   React frontend (see client/README.md)
docs/     design notes: this file for the site, games/ for each game
```

## Roadmap

Each step is one reviewable pull request. Game-specific work is tracked in each
game's own doc.

1. Server scaffold, tooling, and CI.
2. Password gate: login page, signed session cookie, login rate limiting.
3. Client scaffold: Vite + React + TypeScript, served by the server.
4. Rooms and realtime connections: create and join a room, track who is in it,
   and pass messages between players and the room's game.
5. Packaging: Dockerfile and deployment notes.

## Games

- [Graph artillery](games/graph-artillery.md): the first game.
