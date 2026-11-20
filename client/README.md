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
forwards server paths (`/login`, `/logout`, `/healthz`) to the Python server
on port 8000; the list is in `vite.config.ts`. Visit `/login` to sign in.

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
src/App.tsx       the home page
src/games.ts      the list of games shown on the home page
src/styles.css    site-wide styles; colors match the login page
src/*.test.tsx    tests, next to the code they cover
```
