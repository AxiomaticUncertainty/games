"""The rooms that are open, and who has a seat in each.

Rooms live in memory, so a server restart closes them all. That's fine for a
site this size, and keeps the state in one place.

A room closes when its last player leaves, or when nothing has happened in it
for ROOM_IDLE_TIMEOUT, so rooms people walked away from don't pile up.

The registry isn't thread-safe. The API's endpoints are `async`, so they all
run on the server's one event loop, one at a time between awaits, and the
registry never awaits.
"""

import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import timedelta
from hmac import compare_digest

from games_server.games import GAMES, Game, PlayerId

# Room ids are short enough to read out, from letters and digits that can't be
# mistaken for each other (no 0/O or 1/I).
ROOM_ID_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
ROOM_ID_LENGTH = 5
MAX_ROOMS = 100
ROOM_IDLE_TIMEOUT = timedelta(hours=2)
MAX_NAME_LENGTH = 20


class RoomError(Exception):
    """A request about rooms that can't be done. The message is for players."""


class UnknownGame(RoomError):
    pass


class RoomNotFound(RoomError):
    pass


class RoomFull(RoomError):
    pass


class TooManyRooms(RoomError):
    pass


class InvalidName(RoomError):
    pass


class NameTaken(RoomError):
    pass


class NotSeated(RoomError):
    """The token doesn't belong to a seat in the room."""


@dataclass(frozen=True)
class Seat:
    player_id: PlayerId  # public: how other players and the game refer to them
    name: str
    token: str  # secret: only the player who holds the seat knows it


@dataclass
class Room:
    id: str
    game: Game
    last_active: float  # in the registry's clock's seconds
    # Everyone with a seat, in the order they joined. Only the registry
    # changes it.
    seats: dict[PlayerId, Seat] = field(default_factory=dict)
    seats_ever: int = 0  # so player ids are never reused within a room

    def seat_for(self, token: str) -> Seat:
        """The seat `token` belongs to."""
        for seat in self.seats.values():
            if compare_digest(seat.token, token):
                return seat
        raise NotSeated("You don't have a seat in this room.")


class RoomRegistry:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._rooms: dict[str, Room] = {}

    def rooms(self) -> list[Room]:
        """The open rooms, the most recently active first."""
        self._close_idle_rooms()
        return sorted(self._rooms.values(), key=lambda room: room.last_active, reverse=True)

    def get(self, room_id: str) -> Room:
        self._close_idle_rooms()
        room = self._rooms.get(room_id.upper())
        if room is None:
            raise RoomNotFound("There's no room with that id. It may have closed.")
        return room

    def create(self, game_id: str, name: str) -> tuple[Room, Seat]:
        """Open a room for `game_id`, with a seat in it for its creator."""
        game = GAMES.get(game_id)
        if game is None:
            raise UnknownGame(f"There's no game called {game_id!r}.")
        self._close_idle_rooms()
        if len(self._rooms) >= MAX_ROOMS:
            raise TooManyRooms("Too many rooms are open right now. Try joining one instead.")
        room = Room(self._new_room_id(), game, last_active=self._clock())
        seat = self._add_seat(room, name)  # before storing the room, in case of a bad name
        self._rooms[room.id] = room
        return room, seat

    def join(self, room_id: str, name: str) -> tuple[Room, Seat]:
        room = self.get(room_id)
        seat = self._add_seat(room, name)
        room.last_active = self._clock()
        return room, seat

    def leave(self, room_id: str, token: str) -> None:
        """Give up the seat `token` belongs to. The room closes if it's empty."""
        room = self.get(room_id)
        del room.seats[room.seat_for(token).player_id]
        room.last_active = self._clock()
        if not room.seats:
            del self._rooms[room.id]

    def _add_seat(self, room: Room, name: str) -> Seat:
        game = room.game
        if len(room.seats) >= game.max_players:
            raise RoomFull(
                f"This room is full: {game.name} is for at most {game.max_players} players."
            )
        name = _clean_name(name)
        if any(seat.name.casefold() == name.casefold() for seat in room.seats.values()):
            raise NameTaken(f"Someone in this room is already called {name}.")
        room.seats_ever += 1
        seat = Seat(f"p{room.seats_ever}", name, secrets.token_urlsafe(24))
        room.seats[seat.player_id] = seat
        return seat

    def _close_idle_rooms(self) -> None:
        cutoff = self._clock() - ROOM_IDLE_TIMEOUT.total_seconds()
        for room in list(self._rooms.values()):
            if room.last_active < cutoff:
                del self._rooms[room.id]

    def _new_room_id(self) -> str:
        while True:
            room_id = "".join(secrets.choice(ROOM_ID_ALPHABET) for _ in range(ROOM_ID_LENGTH))
            if room_id not in self._rooms:
                return room_id


def _clean_name(name: str) -> str:
    """`name` with its spaces tidied, or InvalidName if it can't be used."""
    name = " ".join(name.split())
    if not name:
        raise InvalidName("Choose a name.")
    if len(name) > MAX_NAME_LENGTH:
        raise InvalidName(f"Names can be at most {MAX_NAME_LENGTH} characters.")
    if not name.isprintable():
        raise InvalidName("Names can't contain control characters.")
    return name
