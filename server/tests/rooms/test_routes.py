"""The rooms API, through the real app: over HTTP, then live connections."""

import time
from contextlib import AbstractContextManager
from typing import Any

import pytest
from fastapi.testclient import TestClient
from starlette.testclient import WebSocketTestSession
from starlette.websockets import WebSocketDisconnect

from games_server.auth.tokens import SESSION_COOKIE
from games_server.rooms import routes
from games_server.rooms.connection import CloseCode
from games_server.rooms.registry import ROOM_ID_LENGTH
from tests.conftest import log_in

GAME = "graph-artillery"
# No room ever has this id: room ids never use 0 (see ROOM_ID_ALPHABET).
NO_SUCH_ROOM = "0" * ROOM_ID_LENGTH


@pytest.fixture
def player(client: TestClient) -> TestClient:
    """A client past the password gate."""
    log_in(client)
    return client


def create(client: TestClient, name: str = "Ada", game: str = GAME) -> Any:
    response = client.post("/api/rooms", json={"game": game, "name": name})
    assert response.status_code == 201, response.text
    return response.json()


def join(client: TestClient, room_id: str, name: str) -> Any:
    response = client.post(f"/api/rooms/{room_id}/seats", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


# Over HTTP


def test_needs_the_password(client: TestClient) -> None:
    response = client.post("/api/rooms", json={"game": GAME, "name": "Ada"})

    assert response.status_code == 401


def test_creating_a_room_seats_its_creator(player: TestClient) -> None:
    seat = create(player)

    assert seat["room"]["game"] == GAME
    assert seat["room"]["players"] == [{"id": seat["player_id"], "name": "Ada", "connected": False}]
    assert seat["token"]


def test_open_rooms_are_listed(player: TestClient) -> None:
    seat = create(player)

    assert player.get("/api/rooms").json() == [seat["room"]]


def test_a_room_can_be_fetched(player: TestClient) -> None:
    seat = create(player)

    assert player.get(f"/api/rooms/{seat['room']['id']}").json() == seat["room"]


def test_listing_never_shows_tokens(player: TestClient) -> None:
    seat = create(player)

    assert seat["token"] not in player.get("/api/rooms").text
    assert seat["token"] not in player.get(f"/api/rooms/{seat['room']['id']}").text


def test_joining_takes_a_seat(player: TestClient) -> None:
    room_id = create(player)["room"]["id"]

    response = player.post(f"/api/rooms/{room_id}/seats", json={"name": "Bo"})

    assert response.status_code == 201
    names = sorted(p["name"] for p in response.json()["room"]["players"])
    assert names == ["Ada", "Bo"]  # in any order


def test_leaving_gives_up_the_seat(player: TestClient) -> None:
    seat = create(player)
    room_id = seat["room"]["id"]

    response = player.post(f"/api/rooms/{room_id}/leave", json={"token": seat["token"]})

    assert response.status_code == 204
    assert player.get(f"/api/rooms/{room_id}").status_code == 404


@pytest.mark.parametrize(
    ("method", "path", "body", "status", "message"),
    [
        ("POST", "/api/rooms", {"game": "chess", "name": "Bo"}, 404, "chess"),
        ("GET", f"/api/rooms/{NO_SUCH_ROOM}", None, 404, "no room"),
        ("POST", "/api/rooms/{room}/seats", {"name": "ada"}, 409, "already"),
        ("POST", "/api/rooms/{room}/seats", {"name": " "}, 422, "Choose"),
        ("POST", "/api/rooms/{room}/leave", {"token": "nope"}, 403, "seat"),
    ],
    ids=["unknown game", "unknown room", "name taken", "bad name", "not seated"],
)
def test_errors_say_what_went_wrong(
    player: TestClient,
    method: str,
    path: str,
    body: dict[str, str] | None,
    status: int,
    message: str,
) -> None:
    room_id = create(player)["room"]["id"]  # Ada's room

    response = player.request(method, path.format(room=room_id), json=body)

    assert response.status_code == status
    assert message in response.json()["detail"]


# Live connections


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


def test_connecting_needs_the_password(client: TestClient) -> None:
    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(f"/api/rooms/{NO_SUCH_ROOM}/connection"),
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

    with connect(player, NO_SUCH_ROOM) as websocket:
        websocket.send_json({"type": "hello", "token": seat["token"]})

        assert closed_with(websocket).code == CloseCode.NO_SUCH_ROOM


def test_closes_a_connection_that_never_says_hello(
    player: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    timeout = 0.2
    monkeypatch.setattr(routes, "HELLO_TIMEOUT_SECONDS", timeout)
    room_id = create(player)["room"]["id"]
    started = time.monotonic()

    with connect(player, room_id) as websocket:
        # This waits for the server to close the connection, so there's
        # nothing to sleep for.
        assert closed_with(websocket).code == CloseCode.BAD_HELLO

    # It was the timeout that closed it, not something sooner. Timers can go
    # off up to a clock tick early (about 16 ms on Windows), so allow for that.
    assert time.monotonic() - started >= timeout - 0.05
