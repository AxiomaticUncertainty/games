from datetime import timedelta

from games_server.auth.throttle import LoginThrottle


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def make_throttle(clock: FakeClock) -> LoginThrottle:
    return LoginThrottle(max_failures=3, window=timedelta(seconds=60), clock=clock)


def test_blocks_after_max_failures() -> None:
    throttle = make_throttle(FakeClock())

    for _ in range(2):
        throttle.record_failure("a")
    assert not throttle.is_blocked("a")

    throttle.record_failure("a")
    assert throttle.is_blocked("a")


def test_clients_are_tracked_separately() -> None:
    throttle = make_throttle(FakeClock())

    for _ in range(3):
        throttle.record_failure("a")

    assert not throttle.is_blocked("b")


def test_failures_older_than_the_window_are_forgotten() -> None:
    clock = FakeClock()
    throttle = make_throttle(clock)
    for _ in range(3):
        throttle.record_failure("a")

    clock.now = 59
    assert throttle.is_blocked("a")

    clock.now = 60
    assert not throttle.is_blocked("a")
