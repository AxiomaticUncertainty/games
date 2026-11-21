import { GAMES } from "./games";

export function App() {
  return (
    <>
      <header className="site-header">
        <span className="site-name">games</span>
        {/* A plain form post: the server clears the session cookie and
            redirects to the login page, so no JavaScript is involved. */}
        <form method="post" action="/logout">
          <button type="submit" className="link-button">
            Sign out
          </button>
        </form>
      </header>

      <main className="page">
        <h1>Games</h1>
        <ul className="game-list">
          {GAMES.map((game) => (
            <li key={game.id} className="game-card">
              <h2>{game.name}</h2>
              <p>{game.description}</p>
              <p className="muted">Coming soon</p>
            </li>
          ))}
        </ul>
      </main>
    </>
  );
}
