import { pageAt } from "./navigation";
import { Lobby } from "./pages/Lobby";
import { RoomPage } from "./pages/RoomPage";

export function App() {
  const page = pageAt(window.location.pathname);
  return (
    <>
      <header className="site-header">
        <a className="site-name" href="/">
          games
        </a>
        {/* A plain form post: the server clears the session cookie and
            redirects to the login page, so no JavaScript is involved. */}
        <form method="post" action="/logout">
          <button type="submit" className="link-button">
            Sign out
          </button>
        </form>
      </header>

      {page.name === "lobby" && <Lobby />}
      {page.name === "room" && <RoomPage roomId={page.roomId} />}
      {page.name === "not found" && (
        <main className="page">
          <h1>Page not found</h1>
          <p>
            <a href="/">Back to the games</a>
          </p>
        </main>
      )}
    </>
  );
}
