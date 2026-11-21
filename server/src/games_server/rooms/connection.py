"""A player's live connection to their room: a WebSocket, seen from the registry.

The registry is synchronous (see `registry`), but writing to a WebSocket means
awaiting. So the registry never writes directly: it puts messages in a
connection's outbox, and `deliver` writes them out in order.
"""

import asyncio
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

from starlette.websockets import WebSocket

type Message = dict[str, Any]


class CloseCode(IntEnum):
    """Why the server closed a connection. 4000-4999 are free for apps to use;
    these mirror the HTTP statuses with the same meaning."""

    BAD_HELLO = 4400  # the first message wasn't a valid hello
    NOT_SEATED = 4403  # the token has no seat in the room
    NO_SUCH_ROOM = 4404
    REPLACED = 4409  # the same seat connected again, from elsewhere
    GONE = 4410  # the player left, or the room closed


@dataclass(frozen=True)
class _Close:
    code: CloseCode
    reason: str


class Connection:
    def __init__(self) -> None:
        self._outbox: asyncio.Queue[Message | _Close] = asyncio.Queue()
        self.closed = False

    def send(self, message: Message) -> None:
        """Queue `message` to be sent, unless the connection is closing."""
        if not self.closed:
            self._outbox.put_nowait(message)

    def close(self, code: CloseCode, reason: str) -> None:
        """Queue the connection to be closed, after what's already queued."""
        if not self.closed:
            self.closed = True
            self._outbox.put_nowait(_Close(code, reason))

    async def deliver(self, websocket: WebSocket) -> None:
        """Send queued messages until the connection is closed."""
        while True:
            item = await self._outbox.get()
            if isinstance(item, _Close):
                await websocket.close(item.code, item.reason)
                return
            await websocket.send_json(item)
