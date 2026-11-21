/**
 * What the browser remembers between visits: the player's name, and their seat
 * in each room they've joined, so a refresh puts them back in it.
 *
 * Kept in localStorage. Storage can be unavailable (some private windows) or
 * full, so every read and write is allowed to fail: the site still works, it
 * just forgets.
 */

export interface SavedSeat {
  playerId: string;
  token: string;
}

const NAME_KEY = "name";
const seatKey = (roomId: string) => `seat:${roomId.toUpperCase()}`;

export function savedName(): string {
  return read(NAME_KEY) ?? "";
}

export function saveName(name: string): void {
  write(NAME_KEY, name);
}

export function savedSeat(roomId: string): SavedSeat | null {
  const raw = read(seatKey(roomId));
  if (raw === null) {
    return null;
  }
  try {
    const seat = JSON.parse(raw) as Partial<SavedSeat>;
    if (typeof seat.playerId === "string" && typeof seat.token === "string") {
      return { playerId: seat.playerId, token: seat.token };
    }
  } catch {
    // Unreadable: treat it as no seat.
  }
  return null;
}

export function saveSeat(roomId: string, seat: SavedSeat): void {
  write(seatKey(roomId), JSON.stringify(seat));
}

export function forgetSeat(roomId: string): void {
  try {
    localStorage.removeItem(seatKey(roomId));
  } catch {
    // Nothing to forget if storage is unavailable.
  }
}

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // Unavailable or full: the site works, but won't remember this.
  }
}
