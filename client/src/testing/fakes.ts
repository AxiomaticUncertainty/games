/** Stand-ins for the server, for tests. */

import { act } from "@testing-library/react";
import { vi } from "vitest";

import type { Player, Room, Seat } from "../rooms/api";

type Answer = { status: number; body?: unknown };
type Handler = (body: unknown) => Answer;

/**
 * Replaces `fetch` with a server that answers "METHOD /path" from `routes`,
 * and 404s anything else. Returns the mock, to check what was requested.
 */
export function fakeServer(routes: Record<string, Handler>) {
  const fetch = vi.fn((path: string, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    const handler = routes[`${method} ${path}`];
    const body: unknown = typeof init?.body === "string" ? JSON.parse(init.body) : undefined;
    const answer = handler ? handler(body) : { status: 404, body: { detail: "Not found." } };
    return Promise.resolve(
      new Response(answer.body === undefined ? null : JSON.stringify(answer.body), {
        status: answer.status,
        headers: { "Content-Type": "application/json" },
      }),
    );
  });
  vi.stubGlobal("fetch", fetch);
  return fetch;
}

/** A WebSocket that tests drive by hand, playing the server's part. */
export class FakeWebSocket {
  static instances: FakeWebSocket[] = [];

  static latest(): FakeWebSocket {
    const socket = FakeWebSocket.instances.at(-1);
    if (!socket) {
      throw new Error("No WebSocket was opened.");
    }
    return socket;
  }

  static install() {
    FakeWebSocket.instances = [];
    vi.stubGlobal("WebSocket", FakeWebSocket);
  }

  readonly sent: unknown[] = [];
  closed = false;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: ((event: { code: number; reason: string }) => void) | null = null;

  constructor(readonly url: string) {
    FakeWebSocket.instances.push(this);
  }

  send(data: string) {
    this.sent.push(JSON.parse(data));
  }

  close() {
    this.closed = true;
  }

  // The server's side:

  accept() {
    act(() => this.onopen?.());
  }

  deliver(message: unknown) {
    act(() => this.onmessage?.({ data: JSON.stringify(message) }));
  }

  end(code: number, reason = "") {
    act(() => this.onclose?.({ code, reason }));
  }
}

export function player(id: string, name: string, connected = true): Player {
  return { id, name, connected };
}

export function room(id: string, players: Player[]): Room {
  return { id, game: "graph-artillery", max_players: 8, players };
}

export function seat(of: Room, playerId: string, token: string): Seat {
  return { room: of, player_id: playerId, token };
}
