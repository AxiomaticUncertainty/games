/**
 * The site's pages, and moving between them.
 *
 * Moving between pages is an ordinary page load. The server answers each
 * page's path with the client (see server/src/games_server/app.py), so links
 * can be shared and refreshes work, without needing a client-side router.
 */

export type Page = { name: "lobby" } | { name: "room"; roomId: string } | { name: "not found" };

export function pageAt(path: string): Page {
  if (path === "/") {
    return { name: "lobby" };
  }
  const roomId = /^\/rooms\/([A-Za-z0-9]+)\/?$/.exec(path)?.[1];
  if (roomId !== undefined) {
    return { name: "room", roomId: roomId.toUpperCase() };
  }
  return { name: "not found" };
}

export function roomPath(roomId: string): string {
  return `/rooms/${roomId}`;
}

export function goTo(path: string): void {
  window.location.assign(path);
}
