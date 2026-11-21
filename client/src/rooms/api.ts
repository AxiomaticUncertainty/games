/**
 * The server's rooms API (server/src/games_server/rooms/routes.py).
 *
 * Each function resolves with the server's answer, or rejects with an
 * `ApiError` whose message is written for players.
 */

export interface Player {
  id: string;
  name: string;
  /** Whether they have the room open right now. */
  connected: boolean;
}

export interface Room {
  id: string;
  game: string;
  max_players: number;
  /** In the order they joined. */
  players: Player[];
}

/** A seat in a room. The token is secret: it proves the seat is yours. */
export interface Seat {
  room: Room;
  player_id: string;
  token: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** What to tell players about `error`, from a request here or anything else. */
export function messageFor(error: unknown): string {
  return error instanceof ApiError ? error.message : "Something went wrong. Try again.";
}

export function listRooms(): Promise<Room[]> {
  return request("GET", "/api/rooms");
}

export function getRoom(roomId: string): Promise<Room> {
  return request("GET", `/api/rooms/${encodeURIComponent(roomId)}`);
}

export function createRoom(game: string, name: string): Promise<Seat> {
  return request("POST", "/api/rooms", { game, name });
}

export function joinRoom(roomId: string, name: string): Promise<Seat> {
  return request("POST", `/api/rooms/${encodeURIComponent(roomId)}/seats`, { name });
}

export async function leaveRoom(roomId: string, token: string): Promise<void> {
  await request("POST", `/api/rooms/${encodeURIComponent(roomId)}/leave`, { token });
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      method,
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError("Couldn't reach the server. Check your connection and try again.", 0);
  }
  if (!response.ok) {
    throw new ApiError(await errorMessage(response), response.status);
  }
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

/** The server's message for a failed request, or a general one if it sent none. */
async function errorMessage(response: Response): Promise<string> {
  if (response.status === 401) {
    return "You've been signed out. Reload the page to sign in again.";
  }
  try {
    const { detail } = (await response.json()) as { detail?: unknown };
    if (typeof detail === "string") {
      return detail;
    }
  } catch {
    // Not JSON: fall through to the general message.
  }
  return `Something went wrong (error ${String(response.status)}). Try again.`;
}
