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

## Rooms

A room is where players gather to play one game together.

- **Players find rooms in a lobby.** The home page lists the open rooms for
  each game, and each room also has a link to send to friends. The site is
  already private, so listing rooms openly gives nothing away.
- **A seat is how the server knows a player.** There are no accounts, only
  the shared password. Taking a seat gives you a display name, unique within
  the room, and a secret token, which the browser keeps. Showing the token
  takes your seat back after a refresh or a dropped connection, instead of
  joining as someone new. The server keeps only a hash of it.
- **Players follow a room live over a WebSocket**, one per seat. Whenever who
  is in the room, or who is connected, changes, everyone connected is sent the
  room as it now is. Opening a room somewhere else, as in a second tab, takes
  over the seat's connection.
- **Rooms live in memory.** A restart closes them all, which is fine at this
  size. A room closes when its last player leaves, or after two hours with
  nothing happening in it and no one connected.

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
4. Rooms and realtime connections, in three pull requests:
   1. Rooms on the server: list, create, join, and leave them over HTTP.
   2. Realtime connections: a WebSocket per player, showing who is connected.
      Passing messages between players and the room's game comes with the
      first game's rules, so it's shaped by a real game.
   3. The lobby and room pages in the client.
5. Packaging: a Docker image and deployment notes.
   - **One image.** It builds the client, and the server serves it
     (`CLIENT_DIR`), so production stays one process.
   - **HTTPS from Caddy**, in front of the server. Session cookies are
     `Secure`, so the site needs HTTPS anywhere but localhost. There's no
     purchased domain, so the site uses an [sslip.io](https://sslip.io) name,
     which points at the server's IP address (`203-0-113-5.sslip.io` is
     `203.0.113.5`). Caddy can get a certificate for it automatically.
   - **uvicorn trusts the proxy's forwarded headers**, so the server sees each
     visitor's own address and not Caddy's. Login rate limiting counts
     attempts per address, so without this everyone would share one limit.
   - **Secrets come from the host's environment**, never from the image.

## Later

Improvements that were worth noting but not yet worth doing. Each says what
would make it worth doing.

- **One list of games.** The client lists games in `client/src/games.ts`,
  repeating the server's `GAMES` in `server/src/games_server/games/__init__.py`.
  Have the client fetch the list, so a new game is added in one place.
- **A live lobby.** The lobby asks for the list of rooms every 5 seconds.
  Make it live over a WebSocket if that ever feels slow.
- **A client-side router.** Moving between pages is an ordinary page load
  (`client/src/navigation.ts`). Switch to a small router, such as wouter, once
  there's a third page, or something should stay connected between pages.
- **Room limits per person.** There's a limit of 100 rooms in total, but not
  per person, so one person could use them all. Add one if it ever happens.

## Games

- [Graph artillery](games/graph-artillery.md): the first game.
