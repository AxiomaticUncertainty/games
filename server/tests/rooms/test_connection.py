"""A connection's outbox, with a stand-in for the WebSocket."""

from typing import Any, cast

import pytest
from starlette.websockets import WebSocket

from games_server.rooms.connection import CloseCode, Connection

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"  # Connection's outbox is an asyncio.Queue


class FakeWebSocket:
    """Records what's written to it, in order."""

    def __init__(self) -> None:
        self.written: list[Any] = []

    async def send_json(self, message: Any) -> None:
        self.written.append(message)

    async def close(self, code: int, reason: str) -> None:
        self.written.append(("closed", code, reason))


async def deliver(connection: Connection) -> list[Any]:
    """Run `connection.deliver` to the end, and return what it wrote."""
    websocket = FakeWebSocket()
    await connection.deliver(cast(WebSocket, websocket))
    return websocket.written


async def test_delivers_messages_in_order_then_closes() -> None:
    connection = Connection()
    connection.send({"n": 1})
    connection.send({"n": 2})
    connection.close(CloseCode.GONE, "You left the room.")

    assert await deliver(connection) == [
        {"n": 1},
        {"n": 2},
        ("closed", CloseCode.GONE, "You left the room."),
    ]


async def test_sends_nothing_after_closing() -> None:
    connection = Connection()
    connection.close(CloseCode.GONE, "You left the room.")
    connection.send({"n": 1})

    assert await deliver(connection) == [("closed", CloseCode.GONE, "You left the room.")]


async def test_closes_only_once() -> None:
    connection = Connection()
    connection.close(CloseCode.REPLACED, "first")
    connection.close(CloseCode.GONE, "second")

    assert await deliver(connection) == [("closed", CloseCode.REPLACED, "first")]
    assert connection.closed
