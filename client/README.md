# client

The browser side: React + TypeScript, built with Vite. It draws the games and
sends player input. The server decides every outcome
(see [../docs/architecture.md](../docs/architecture.md)).

## Setup

Requires Node.js; the version is in `.node-version`. Then:

```sh
npm install
```

## Development

Run the Python server (see [../server/README.md](../server/README.md)) and,
in another terminal:

```sh
npm run dev
```

Open http://localhost:5173. Vite serves the client with hot reload and
forwards server paths (`/login`, `/logout`, `/healthz`, `/api`) to the Python server
on port 8000; the list is in `vite.config.ts`.

The password gate applies in development too: before Vite serves anything, it
asks the Python server's gate whether the request may go through, and passes on
its answer if not (`dev/passwordGate.ts`). So you're sent to `/login` as in
production, and the Python server has to be running.

## Common tasks

| Task       | Command                                   |
| ---------- | ----------------------------------------- |
| Dev server | `npm run dev`                             |
| Tests      | `npm test`                                |
| Lint       | `npm run lint`                            |
| Format     | `npm run format` (CI runs `format:check`) |
| Type-check | `npm run typecheck`                       |
| Build      | `npm run build`, output in `dist/`        |

CI runs lint, format check, type check, tests and build on every pull request.

## Production

`npm run build` writes static files to `dist/`. The Python server serves them
when its `CLIENT_DIR` setting points there, behind the same password as
everything else.

## Layout

```
index.html        page shell; Vite injects the built script
src/main.tsx      entry point: mounts <App /> into #root
src/App.tsx       the site's header, and the page for the current path
src/navigation.ts the site's pages, and moving between them
src/pages/        one component per page: the lobby, and a room
src/rooms/        the rooms API, live room connections, and saved seats
src/games.ts      the list of games shown in the lobby
src/styles.css    site-wide styles; colors match the login page
src/*.test.tsx    tests, next to the code they cover
dev/              development-only Vite plugins
```
