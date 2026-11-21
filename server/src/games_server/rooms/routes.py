"""The rooms API, under /api/rooms. All of it is behind the password gate.

    GET  /api/rooms                  the open rooms, most recently active first
    POST /api/rooms                  open a room, and take a seat in it
    GET  /api/rooms/{id}             one room
    POST /api/rooms/{id}/seats       take a seat in a room
    POST /api/rooms/{id}/leave       give up your seat
    WS   /api/rooms/{id}/connection  follow a room you have a seat in, live

Taking a seat answers with the seat's secret token. The client keeps it, and
sends it to show which seat is theirs.

Errors are answered with a status and `{"detail": message}`, where the message
is written for players.

A connection starts with the client sending `{"type": "hello", "token": ...}`.
The token goes in a message rather than the URL so it stays out of server
logs. The server answers `{"type": "welcome", "player_id": ...}`, and then
`{"type": "room", "room": ...}` whenever the room changes. If the server
closes the connection, the close code (see `connection.CloseCode`) says why,
and the reason is written for players.

Every endpoint is `async`, so it runs on the event loop: see `registry` for
why that matters.
"""

from collections.abc import Coroutine, Iterator
from contextlib import contextmanager
from typing import Any, Literal

import anyio
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, ValidationError

from games_server.rooms.connection import CloseCode
from games_server.rooms.registry import (
    InvalidName,
    NameTaken,
    NotSeated,
    RoomError,
    RoomFull,
    RoomNotFound,
    RoomRegistry,
    TooManyRooms,
    UnknownGame,
)
from games_server.rooms.views import RoomView, SeatView, room_view, seat_view

# How long a new connection has to say hello before it's closed.
HELLO_TIMEOUT_SECONDS = 10

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


class Hello(BaseModel):
    type: Literal["hello"]
    token: str


def create_router(registry: RoomRegistry) -> APIRouter:
    router = APIRouter(prefix="/api/rooms")

    @router.get("")
    async def list_rooms() -> list[RoomView]:
        return [room_view(room) for room in registry.rooms()]

    @router.post("", status_code=status.HTTP_201_CREATED)
    async def create_room(request: NewRoom) -> SeatView:
        with _answering_errors():
            room, seat = registry.create(request.game, request.name)
        return seat_view(room, seat)

    @router.get("/{room_id}")
    async def get_room(room_id: str) -> RoomView:
        with _answering_errors():
            return room_view(registry.get(room_id))

    @router.post("/{room_id}/seats", status_code=status.HTTP_201_CREATED)
    async def join_room(room_id: str, request: Joining) -> SeatView:
        with _answering_errors():
            room, seat = registry.join(room_id, request.name)
        return seat_view(room, seat)

    @router.post("/{room_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
    async def leave_room(room_id: str, request: Leaving) -> None:
        with _answering_errors():
            registry.leave(room_id, request.token)

    @router.websocket("/{room_id}/connection")
    async def connect(websocket: WebSocket, room_id: str) -> None:
        await websocket.accept()
        try:
            with anyio.fail_after(HELLO_TIMEOUT_SECONDS):
                first = await websocket.receive()
            if first["type"] == "websocket.disconnect":
                return
            # A binary message has no "text", and fails validation as "".
            hello = Hello.model_validate_json(first.get("text") or "")
        except TimeoutError, ValidationError:
            await websocket.close(CloseCode.BAD_HELLO, "Start by sending your seat's token.")
            return

        try:
            room, seat, connection = registry.connect(room_id, hello.token)
        except RoomNotFound as error:
            await websocket.close(CloseCode.NO_SUCH_ROOM, str(error))
            return
        except NotSeated as error:
            await websocket.close(CloseCode.NOT_SEATED, str(error))
            return

        try:
            await _until_either_ends(connection.deliver(websocket), _until_gone(websocket))
        finally:
            registry.disconnect(room.id, seat.player_id, connection)

    return router


async def _until_gone(websocket: WebSocket) -> None:
    """Wait for the client to disconnect. Players have nothing to send after
    their hello yet, so anything else they send is ignored."""
    while (await websocket.receive())["type"] != "websocket.disconnect":
        pass


async def _until_either_ends(*jobs: Coroutine[Any, Any, None]) -> None:
    """Run `jobs` together until one finishes, then stop the rest."""

    async def run_then_stop_the_rest(job: Coroutine[Any, Any, None]) -> None:
        await job
        group.cancel_scope.cancel()

    try:
        async with anyio.create_task_group() as group:
            for job in jobs:
                group.start_soon(run_then_stop_the_rest, job)
    except* WebSocketDisconnect:
        pass  # the client vanished mid-send: an ordinary way for this to end


@contextmanager
def _answering_errors() -> Iterator[None]:
    """Turns a RoomError raised inside it into an HTTP error answer."""
    try:
        yield
    except RoomError as error:
        raise HTTPException(_STATUSES[type(error)], str(error)) from error
