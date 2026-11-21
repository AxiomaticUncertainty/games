import { useEffect, useState } from "react";

import { type Game, GAMES } from "../games";
import { goTo, roomPath } from "../navigation";
import { createRoom, listRooms, messageFor, type Room } from "../rooms/api";
import { saveName, saveSeat, savedName } from "../rooms/saved";

/** How often the list of open rooms is refreshed. */
export const LOBBY_REFRESH_MS = 5000;

/** The home page: every game, with its open rooms and a way to start one. */
export function Lobby() {
  const [rooms, setRooms] = useState<Room[] | null>(null);
  const [listError, setListError] = useState<string | null>(null);
  const [name, setName] = useState(savedName);
  const [createError, setCreateError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    let stopped = false;
    function refresh() {
      listRooms().then(
        (open) => {
          if (!stopped) {
            setRooms(open);
            setListError(null);
          }
        },
        (error: unknown) => {
          if (!stopped) {
            setListError(messageFor(error));
          }
        },
      );
    }
    refresh();
    const timer = setInterval(refresh, LOBBY_REFRESH_MS);
    return () => {
      stopped = true;
      clearInterval(timer);
    };
  }, []);

  async function create(game: Game) {
    setCreating(true);
    setCreateError(null);
    try {
      const seat = await createRoom(game.id, name);
      saveName(name);
      saveSeat(seat.room.id, { playerId: seat.player_id, token: seat.token });
      goTo(roomPath(seat.room.id));
    } catch (error) {
      setCreateError(messageFor(error));
      setCreating(false);
    }
  }

  return (
    <main className="page">
      <h1>Games</h1>

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
      {createError && (
        <p className="error" role="alert">
          {createError}
        </p>
      )}
      {listError && (
        <p className="error" role="alert">
          {listError}
        </p>
      )}

      <ul className="game-list">
        {GAMES.map((game) => (
          <li key={game.id} className="game-card">
            <h2>{game.name}</h2>
            <p>{game.description}</p>
            <OpenRooms rooms={rooms?.filter((room) => room.game === game.id) ?? null} />
            <button type="button" disabled={creating} onClick={() => void create(game)}>
              New room
            </button>
          </li>
        ))}
      </ul>
    </main>
  );
}

function OpenRooms({ rooms }: { rooms: Room[] | null }) {
  if (rooms === null) {
    return <p className="muted">Loading rooms…</p>;
  }
  if (rooms.length === 0) {
    return <p className="muted">No open rooms yet.</p>;
  }
  return (
    <ul className="room-list" aria-label="Open rooms">
      {rooms.map((room) => (
        <li key={room.id}>
          <a href={roomPath(room.id)}>{room.players.map((player) => player.name).join(", ")}</a>{" "}
          <span className="muted">
            {room.players.length}/{room.max_players}
          </span>
        </li>
      ))}
    </ul>
  );
}
