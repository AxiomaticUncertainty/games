"""The rooms API, through the real app."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

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
