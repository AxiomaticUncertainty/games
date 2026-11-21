"""Live connections to rooms, through the real app."""

from contextlib import AbstractContextManager
from typing import Any

import pytest
from fastapi.testclient import TestClient
from starlette.testclient import WebSocketTestSession
from starlette.websockets import WebSocketDisconnect

from games_server.auth.tokens import SESSION_COOKIE
from games_server.rooms import routes
from games_server.rooms.connection import CloseCode
from tests.conftest import log_in

GAME = "graph-artillery"


@pytest.fixture
def player(client: TestClient) -> TestClient:
    """A client past the password gate."""
    log_in(client)
    return client


def create(client: TestClient, name: str = "Ada") -> Any:
    return client.post("/api/rooms", json={"game": GAME, "name": name}).json()


def join(client: TestClient, room_id: str, name: str) -> Any:
    return client.post(f"/api/rooms/{room_id}/seats", json={"name": name}).json()


def connect(client: TestClient, room_id: str) -> AbstractContextManager[WebSocketTestSession]:
    # The test client always connects WebSockets over plain ws://, where a
    # Secure cookie is never sent, so pass the cookie by hand. Browsers send it
    # automatically over wss://.
    cookie = f"{SESSION_COOKIE}={client.cookies[SESSION_COOKIE]}"
    return client.websocket_connect(f"/api/rooms/{room_id}/connection", headers={"cookie": cookie})


def say_hello(websocket: WebSocketTestSession, token: str) -> Any:
    """Say hello, and return the room as first announced."""
    websocket.send_json({"type": "hello", "token": token})
    assert websocket.receive_json()["type"] == "welcome"
    return websocket.receive_json()["room"]


def closed_with(websocket: WebSocketTestSession) -> WebSocketDisconnect:
    with pytest.raises(WebSocketDisconnect) as closed:
        websocket.receive_json()
    return closed.value


def is_connected(announcement: dict[str, Any], player_id: str) -> bool:
    """Whether a room announcement shows `player_id` as connected."""
    (player,) = (p for p in announcement["room"]["players"] if p["id"] == player_id)
    return bool(player["connected"])


def test_needs_the_password(client: TestClient) -> None:
    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect("/api/rooms/ZZZZZ/connection"),
    ):
        pass


def test_hello_is_welcomed_with_the_room(player: TestClient) -> None:
    seat = create(player)

    with connect(player, seat["room"]["id"]) as websocket:
        websocket.send_json({"type": "hello", "token": seat["token"]})

        assert websocket.receive_json() == {"type": "welcome", "player_id": seat["player_id"]}
        announced = websocket.receive_json()
        assert announced["type"] == "room"
        assert announced["room"]["players"] == [
            {"id": seat["player_id"], "name": "Ada", "connected": True}
        ]


def test_hears_when_someone_joins(player: TestClient) -> None:
    seat = create(player)
    room_id = seat["room"]["id"]

    with connect(player, room_id) as websocket:
        say_hello(websocket, seat["token"])
        join(player, room_id, "Bo")

        names = sorted(p["name"] for p in websocket.receive_json()["room"]["players"])
        assert names == ["Ada", "Bo"]  # in any order


def test_hears_when_someone_connects_and_disconnects(player: TestClient) -> None:
    ada = create(player)
    room_id = ada["room"]["id"]
    bo = join(player, room_id, "Bo")

    with connect(player, room_id) as ada_socket:
        say_hello(ada_socket, ada["token"])
        with connect(player, room_id) as bo_socket:
            say_hello(bo_socket, bo["token"])
            assert is_connected(ada_socket.receive_json(), bo["player_id"])

        assert not is_connected(ada_socket.receive_json(), bo["player_id"])


def test_connecting_again_closes_the_first_connection(player: TestClient) -> None:
    seat = create(player)
    room_id = seat["room"]["id"]

    with connect(player, room_id) as first:
        say_hello(first, seat["token"])
        with connect(player, room_id) as second:
            say_hello(second, seat["token"])

            assert closed_with(first).code == CloseCode.REPLACED


def test_leaving_closes_the_connection(player: TestClient) -> None:
    seat = create(player)
    room_id = seat["room"]["id"]
    join(player, room_id, "Bo")  # so the room stays open

    with connect(player, room_id) as websocket:
        say_hello(websocket, seat["token"])
        player.post(f"/api/rooms/{room_id}/leave", json={"token": seat["token"]})

        closed = closed_with(websocket)
        assert closed.code == CloseCode.GONE
        assert closed.reason == "You left the room."


@pytest.mark.parametrize(
    ("hello", "code"),
    [
        ('{"type": "hello", "token": "not a token"}', CloseCode.NOT_SEATED),
        ('{"type": "hi", "token": "whatever"}', CloseCode.BAD_HELLO),
        ('{"token": "whatever"}', CloseCode.BAD_HELLO),
        ("not json", CloseCode.BAD_HELLO),
    ],
    ids=["wrong token", "wrong type", "no type", "not json"],
)
def test_rejects_a_bad_hello(player: TestClient, hello: str, code: CloseCode) -> None:
    room_id = create(player)["room"]["id"]

    with connect(player, room_id) as websocket:
        websocket.send_text(hello)

        assert closed_with(websocket).code == code


def test_rejects_a_binary_hello(player: TestClient) -> None:
    room_id = create(player)["room"]["id"]

    with connect(player, room_id) as websocket:
        websocket.send_bytes(b"\x00")

        assert closed_with(websocket).code == CloseCode.BAD_HELLO


def test_rejects_an_unknown_room(player: TestClient) -> None:
    seat = create(player)

    with connect(player, "ZZZZZ") as websocket:
        websocket.send_json({"type": "hello", "token": seat["token"]})

        assert closed_with(websocket).code == CloseCode.NO_SUCH_ROOM


def test_closes_a_connection_that_never_says_hello(
    player: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(routes, "HELLO_TIMEOUT_SECONDS", 0.01)
    room_id = create(player)["room"]["id"]

    with connect(player, room_id) as websocket:
        assert closed_with(websocket).code == CloseCode.BAD_HELLO
