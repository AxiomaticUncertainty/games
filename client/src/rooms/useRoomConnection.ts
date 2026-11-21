import { useEffect, useState } from "react";

import type { Room } from "./api";

/**
 * A live connection to a room the player has a seat in, following the protocol
 * in server/src/games_server/rooms/routes.py.
 */
export type Connection =
  | { status: "connecting" }
  | { status: "open"; room: Room }
  | {
      status: "closed";
      /** The server's code, from rooms/connection.py's CloseCode. */
      code: number;
      /** Written for players. */
      reason: string;
    };

/** Close codes the server uses to end a connection for good. */
export const CloseCode = {
  BAD_HELLO: 4400,
  NOT_SEATED: 4403,
  NO_SUCH_ROOM: 4404,
  REPLACED: 4409,
  GONE: 4410,
} as const;

/** How long to wait before reconnecting after the connection drops. */
export const RECONNECT_DELAY_MS = 2000;

/**
 * Connects to the room, and keeps the room up to date as the server announces
 * changes. If the connection drops, it reconnects, unless the server closed it
 * on purpose (codes 4000 and up), which is final.
 */
export function useRoomConnection(roomId: string, token: string): Connection {
  const [connection, setConnection] = useState<Connection>({ status: "connecting" });

  useEffect(() => {
    let socket: WebSocket;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
    let stopped = false;

    function connect() {
      const scheme = location.protocol === "https:" ? "wss:" : "ws:";
      socket = new WebSocket(
        `${scheme}//${location.host}/api/rooms/${encodeURIComponent(roomId)}/connection`,
      );
      socket.onopen = () => {
        socket.send(JSON.stringify({ type: "hello", token }));
      };
      socket.onmessage = (event: MessageEvent<string>) => {
        const message = JSON.parse(event.data) as { type: string; room?: Room };
        if (message.type === "room" && message.room) {
          setConnection({ status: "open", room: message.room });
        }
      };
      socket.onclose = (event) => {
        if (stopped) {
          return;
        }
        if (event.code >= 4000) {
          setConnection({ status: "closed", code: event.code, reason: event.reason });
          return;
        }
        setConnection({ status: "connecting" });
        reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS);
      };
    }

    connect();
    return () => {
      stopped = true;
      clearTimeout(reconnectTimer);
      socket.close();
    };
  }, [roomId, token]);

  return connection;
}
