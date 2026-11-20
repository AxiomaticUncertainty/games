"""Rate limiting for failed login attempts.

With one shared password, the main threat is someone guessing it. Allowing only
a few failures per client per window makes guessing impractically slow.

State lives in memory, so it resets when the server restarts. That is fine for
a single-process deployment. If the server ever runs as several processes, this
needs a shared store.
"""

import time
from collections import defaultdict, deque
from collections.abc import Callable
from datetime import timedelta


class LoginThrottle:
    """Blocks a client after `max_failures` failed logins within `window`."""

    def __init__(
        self,
        max_failures: int,
        window: timedelta,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max_failures = max_failures
        self._window_seconds = window.total_seconds()
        self._clock = clock
        self._failures: defaultdict[str, deque[float]] = defaultdict(deque)

    def is_blocked(self, client: str) -> bool:
        self._forget_expired(client)
        return len(self._failures.get(client, ())) >= self._max_failures

    def record_failure(self, client: str) -> None:
        self._failures[client].append(self._clock())

    def _forget_expired(self, client: str) -> None:
        # `failures` is None for a client with no recorded failures; the loop
        # and the cleanup below both treat that the same as an empty deque.
        failures = self._failures.get(client)
        cutoff = self._clock() - self._window_seconds
        while failures and failures[0] <= cutoff:
            failures.popleft()
        if not failures:
            self._failures.pop(client, None)
