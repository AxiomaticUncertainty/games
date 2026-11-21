"""How rooms look from outside the server: in API answers and on connections."""

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:  # only for annotations: registry imports this module
    from games_server.rooms.registry import Room, Seated


class PlayerView(BaseModel):
    id: str
    name: str
    connected: bool  # whether they have the room open right now


class RoomView(BaseModel):
    id: str
    game: str
    max_players: int
    players: list[PlayerView]  # in no particular order


class SeatView(BaseModel):
    room: RoomView
    player_id: str
    token: str


def room_view(room: Room) -> RoomView:
    return RoomView(
        id=room.id,
        game=room.game.id,
        max_players=room.game.max_players,
        players=[
            PlayerView(
                id=seat.player_id, name=seat.name, connected=seat.player_id in room.connections
            )
            for seat in room.seats.values()
        ],
    )


def seat_view(seated: Seated) -> SeatView:
    return SeatView(
        room=room_view(seated.room), player_id=seated.seat.player_id, token=seated.token
    )
