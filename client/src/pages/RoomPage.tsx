import { type SubmitEvent, useEffect, useState } from "react";

import { GAMES } from "../games";
import { goTo } from "../navigation";
import { getRoom, joinRoom, leaveRoom, messageFor, type Room } from "../rooms/api";
import {
  forgetSeat,
  type SavedSeat,
  saveName,
  saveSeat,
  savedName,
  savedSeat,
} from "../rooms/saved";
import { CloseCode, useRoomConnection } from "../rooms/useRoomConnection";

/** One room: a way to join it, or, once seated, who's in it, live. */
export function RoomPage({ roomId }: { roomId: string }) {
  const [seat, setSeat] = useState<SavedSeat | null>(() => savedSeat(roomId));

  if (seat === null) {
    return <JoinRoom roomId={roomId} onJoined={setSeat} />;
  }
  return (
    <SeatedRoom
      roomId={roomId}
      seat={seat}
      onSeatLost={() => {
        forgetSeat(roomId);
        setSeat(null);
      }}
    />
  );
}

function JoinRoom({ roomId, onJoined }: { roomId: string; onJoined: (seat: SavedSeat) => void }) {
  const [room, setRoom] = useState<Room | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState(savedName);
  const [joining, setJoining] = useState(false);

  useEffect(() => {
    getRoom(roomId).then(setRoom, (failure: unknown) => {
      setError(messageFor(failure));
    });
  }, [roomId]);

  async function join(event: SubmitEvent) {
    event.preventDefault();
    setJoining(true);
    setError(null);
    try {
      const seat = await joinRoom(roomId, name);
      const saved = { playerId: seat.player_id, token: seat.token };
      saveName(name);
      saveSeat(roomId, saved);
      onJoined(saved);
    } catch (failure) {
      setError(messageFor(failure));
      setJoining(false);
    }
  }

  return (
    <main className="page">
      <h1>{room ? `${gameName(room)} room` : "Room"}</h1>
      {room && <PlayerList room={room} />}
      <form onSubmit={(event) => void join(event)}>
        <label className="field">
          Your name
          <input
            value={name}
            maxLength={20}
            onChange={(event) => {
              setName(event.target.value);
            }}
          />
        </label>
        <button type="submit" disabled={joining}>
          Join
        </button>
      </form>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <p>
        <a href="/">Back to the games</a>
      </p>
    </main>
  );
}

function SeatedRoom({
  roomId,
  seat,
  onSeatLost,
}: {
  roomId: string;
  seat: SavedSeat;
  onSeatLost: () => void;
}) {
  // Bumped to connect again, which remounts the connection.
  const [attempt, setAttempt] = useState(0);
  return (
    <LiveRoom
      key={attempt}
      roomId={roomId}
      seat={seat}
      onSeatLost={onSeatLost}
      onReconnect={() => {
        setAttempt((n) => n + 1);
      }}
    />
  );
}

function LiveRoom({
  roomId,
  seat,
  onSeatLost,
  onReconnect,
}: {
  roomId: string;
  seat: SavedSeat;
  onSeatLost: () => void;
  onReconnect: () => void;
}) {
  const connection = useRoomConnection(roomId, seat.token);
  const [leaveError, setLeaveError] = useState<string | null>(null);

  useEffect(() => {
    // The seat is no longer this player's: offer to join again.
    if (connection.status === "closed" && connection.code === CloseCode.NOT_SEATED) {
      onSeatLost();
    }
  }, [connection, onSeatLost]);

  async function leave() {
    try {
      await leaveRoom(roomId, seat.token);
      forgetSeat(roomId);
      goTo("/");
    } catch (failure) {
      setLeaveError(messageFor(failure));
    }
  }

  if (connection.status === "connecting") {
    return (
      <main className="page">
        <p className="muted">Connecting…</p>
      </main>
    );
  }

  if (connection.status === "closed") {
    return (
      <main className="page">
        <p role="alert">{connection.reason || "The connection to this room closed."}</p>
        {connection.code === CloseCode.REPLACED && (
          <button type="button" onClick={onReconnect}>
            Use it here instead
          </button>
        )}
        <p>
          <a href="/">Back to the games</a>
        </p>
      </main>
    );
  }

  const { room } = connection;
  return (
    <main className="page">
      <h1>{gameName(room)} room</h1>
      <p>
        Invite others with this page's link: <code>{location.href}</code>
      </p>
      <PlayerList room={room} you={seat.playerId} />
      <p className="muted">The game itself is coming soon.</p>
      <button type="button" onClick={() => void leave()}>
        Leave room
      </button>
      {leaveError && (
        <p className="error" role="alert">
          {leaveError}
        </p>
      )}
    </main>
  );
}

function PlayerList({ room, you }: { room: Room; you?: string }) {
  return (
    <>
      <h2>
        Players ({room.players.length}/{room.max_players})
      </h2>
      <ul className="player-list" aria-label="Players">
        {room.players.map((player) => (
          <li key={player.id}>
            {player.name}
            {player.id === you && " (you)"}
            {!player.connected && <span className="muted"> away</span>}
          </li>
        ))}
      </ul>
    </>
  );
}

function gameName(room: Room): string {
  return GAMES.find((game) => game.id === room.game)?.name ?? room.game;
}
