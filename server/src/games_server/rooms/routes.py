"""The rooms API, under /api/rooms. All of it is behind the password gate.

    GET  /api/rooms                  the open rooms, most recently active first
    POST /api/rooms                  open a room, and take a seat in it
    GET  /api/rooms/{id}             one room
    POST /api/rooms/{id}/seats       take a seat in a room
    POST /api/rooms/{id}/leave       give up your seat

Taking a seat answers with the seat's secret token. The client keeps it, and
sends it to show which seat is theirs.

Errors are answered with a status and `{"detail": message}`, where the message
is written for players.

Every endpoint is `async`, so it runs on the event loop: see `registry` for
why that matters.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from games_server.rooms.registry import (
    InvalidName,
    NameTaken,
    NotSeated,
    Room,
    RoomError,
    RoomFull,
    RoomNotFound,
    RoomRegistry,
    Seated,
    TooManyRooms,
    UnknownGame,
)

_STATUSES: dict[type[RoomError], int] = {
    UnknownGame: status.HTTP_404_NOT_FOUND,
    RoomNotFound: status.HTTP_404_NOT_FOUND,
    InvalidName: status.HTTP_422_UNPROCESSABLE_CONTENT,
    NameTaken: status.HTTP_409_CONFLICT,
    RoomFull: status.HTTP_409_CONFLICT,
    TooManyRooms: status.HTTP_503_SERVICE_UNAVAILABLE,
    NotSeated: status.HTTP_403_FORBIDDEN,
}


class NewRoom(BaseModel):
    game: str
    name: str  # the creator's display name


class Joining(BaseModel):
    name: str


class Leaving(BaseModel):
    token: str


class PlayerView(BaseModel):
    id: str
    name: str


class RoomView(BaseModel):
    id: str
    game: str
    max_players: int
    players: list[PlayerView]


class SeatView(BaseModel):
    room: RoomView
    player_id: str
    token: str


def create_router(registry: RoomRegistry) -> APIRouter:
    router = APIRouter(prefix="/api/rooms")

    @router.get("")
    async def list_rooms() -> list[RoomView]:
        return [_room_view(room) for room in registry.rooms()]

    @router.post("", status_code=status.HTTP_201_CREATED)
    async def create_room(request: NewRoom) -> SeatView:
        with _answering_errors():
            seated = registry.create(request.game, request.name)
        return _seat_view(seated)

    @router.get("/{room_id}")
    async def get_room(room_id: str) -> RoomView:
        with _answering_errors():
            return _room_view(registry.get(room_id))

    @router.post("/{room_id}/seats", status_code=status.HTTP_201_CREATED)
    async def join_room(room_id: str, request: Joining) -> SeatView:
        with _answering_errors():
            seated = registry.join(room_id, request.name)
        return _seat_view(seated)

    @router.post("/{room_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
    async def leave_room(room_id: str, request: Leaving) -> None:
        with _answering_errors():
            registry.leave(room_id, request.token)

    return router


@contextmanager
def _answering_errors() -> Iterator[None]:
    """Turns a RoomError raised inside it into an HTTP error answer."""
    try:
        yield
    except RoomError as error:
        raise HTTPException(_STATUSES[type(error)], str(error)) from error


def _room_view(room: Room) -> RoomView:
    return RoomView(
        id=room.id,
        game=room.game.id,
        max_players=room.game.max_players,
        players=[PlayerView(id=seat.player_id, name=seat.name) for seat in room.seats.values()],
    )


def _seat_view(seated: Seated) -> SeatView:
    return SeatView(
        room=_room_view(seated.room), player_id=seated.seat.player_id, token=seated.token
    )
