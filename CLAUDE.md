# Working on this repository

Start with [README.md](README.md), then [docs/architecture.md](docs/architecture.md)
for the design, the roadmap, and what's been left for later. Each game's own
design and roadmap are in [docs/games/](docs/games/).

## How the work is done

- **Small pull requests, one roadmap step at a time.** Each should be easy to
  review on its own. A big step is split into stacked pull requests.
- **Readable over clever.** Write code a careful senior engineer would be glad
  to maintain: clear names, comments that explain why, and no speculative
  design. Leave out what isn't needed yet, and note it under "Later" in
  `docs/architecture.md` if it's worth remembering.
- **Keep the docs true.** When a decision changes, update `docs/architecture.md`
  or the game's doc in the same pull request.
- **Games are original.** A game can share a genre or mechanics with an
  existing one, but never its name, characters, art, music, or look.

## Checks

The same as CI (`.github/workflows/ci.yml`). Run them before every push.

- **Server**, from `server/`: `uv run ruff format`, `uv run ruff check`,
  `uv run mypy`, `uv run pytest`.
- **Client**, from `client/`: `npm run lint`, `npm run format:check`,
  `npm run typecheck`, `npm test`, `npm run build`.

## Pull requests

- **Use `gh stack`** for every pull request, not hand-set base branches:
  - `gh stack init <branch>` starts a stack;
  - `gh stack add <branch>`, from the top branch, adds a branch above it;
  - `gh stack submit` opens the pull requests, and `gh stack push` updates
    them;
  - `gh stack rebase` brings the branches above up to date after a change
    lower down.
- **Never commit to `main`**, and never merge: the owner reviews and merges
  every pull request.
- **Answer review with new commits**, named "Address review: ...", so the
  reviewer can see what changed.
- **Never comment or reply on GitHub** (pull requests, reviews, issues)
  without asking first.
- **Stage files by name**, never with `git add -A` or `git add .`.
- **Descriptions** say what the change is, how it fits together, what's worth
  a close look, and how it was tested.
- **Attribution:** end commit messages and pull request descriptions with the
  attribution lines Claude Code provides.

## Secrets and privacy

- **Secrets come from the environment**, through `server/.env` locally, which
  git ignores (see `server/README.md`). Never commit a password hash, session
  secret, or `.env` file. The password hash never goes into session tokens.
- **Commits use the owner's GitHub noreply address**, never a personal email.

## The machine

- **Ask before installing system software**, and never accept a license or
  agreement on the owner's behalf.
