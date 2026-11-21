import pytest

from games_server.games import GAMES
from games_server.rooms.registry import (
    MAX_NAME_LENGTH,
    MAX_ROOMS,
    ROOM_ID_ALPHABET,
    ROOM_ID_LENGTH,
    ROOM_IDLE_TIMEOUT,
    InvalidName,
    NameTaken,
    NotSeated,
    RoomFull,
    RoomNotFound,
    RoomRegistry,
    TooManyRooms,
    UnknownGame,
)

GAME = "graph-artillery"
MAX_PLAYERS = GAMES[GAME].max_players
IDLE_SECONDS = ROOM_IDLE_TIMEOUT.total_seconds()


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def registry(clock: FakeClock) -> RoomRegistry:
    return RoomRegistry(clock)


class TestCreate:
    def test_creator_gets_the_first_seat(self, registry: RoomRegistry) -> None:
        room, seat = registry.create(GAME, "Ada")

        assert list(room.seats.values()) == [seat]
        assert seat.name == "Ada"

    def test_room_is_listed(self, registry: RoomRegistry) -> None:
        room, _ = registry.create(GAME, "Ada")

        assert registry.rooms() == [room]

    def test_room_ids_are_short_and_unambiguous(self, registry: RoomRegistry) -> None:
        room, _ = registry.create(GAME, "Ada")

        assert len(room.id) == ROOM_ID_LENGTH
        assert set(room.id) <= set(ROOM_ID_ALPHABET)

    def test_rejects_an_unknown_game(self, registry: RoomRegistry) -> None:
        with pytest.raises(UnknownGame):
            registry.create("chess", "Ada")

    def test_bad_name_opens_no_room(self, registry: RoomRegistry) -> None:
        with pytest.raises(InvalidName):
            registry.create(GAME, "")

        assert registry.rooms() == []

    def test_limits_how_many_rooms_are_open(self, registry: RoomRegistry) -> None:
        for _ in range(MAX_ROOMS):
            registry.create(GAME, "Ada")

        with pytest.raises(TooManyRooms):
            registry.create(GAME, "Ada")


class TestJoin:
    def test_gives_a_new_seat(self, registry: RoomRegistry) -> None:
        room, ada = registry.create(GAME, "Ada")
        _, bo = registry.join(room.id, "Bo")

        assert list(room.seats.values()) == [ada, bo]

    def test_seats_have_distinct_ids_and_tokens(self, registry: RoomRegistry) -> None:
        room, ada = registry.create(GAME, "Ada")
        _, bo = registry.join(room.id, "Bo")

        assert ada.player_id != bo.player_id
        assert ada.token != bo.token

    def test_room_ids_ignore_case(self, registry: RoomRegistry) -> None:
        room, _ = registry.create(GAME, "Ada")

        registry.join(room.id.lower(), "Bo")

    def test_rejects_an_unknown_room(self, registry: RoomRegistry) -> None:
        with pytest.raises(RoomNotFound):
            registry.join("ZZZZZ", "Bo")

    def test_rejects_a_name_already_taken_whatever_its_case(self, registry: RoomRegistry) -> None:
        room, _ = registry.create(GAME, "Ada")

        with pytest.raises(NameTaken):
            registry.join(room.id, "ADA")

    def test_rejects_joining_a_full_room(self, registry: RoomRegistry) -> None:
        room, _ = registry.create(GAME, "player 0")
        for n in range(1, MAX_PLAYERS):
            registry.join(room.id, f"player {n}")

        with pytest.raises(RoomFull):
            registry.join(room.id, "one too many")

    def test_player_ids_are_not_reused(self, registry: RoomRegistry) -> None:
        # A new player mustn't be mistaken for one who left.
        room, ada = registry.create(GAME, "Ada")
        _, bo = registry.join(room.id, "Bo")
        registry.leave(room.id, bo.token)
        _, cy = registry.join(room.id, "Cy")

        assert cy.player_id not in (ada.player_id, bo.player_id)


class TestNames:
    def test_tidies_spaces(self, registry: RoomRegistry) -> None:
        _, seat = registry.create(GAME, "  Ada \t Lovelace ")

        assert seat.name == "Ada Lovelace"

    @pytest.mark.parametrize(
        ("name", "message"),
        [
            ("", "Choose a name"),
            ("   ", "Choose a name"),
            ("x" * (MAX_NAME_LENGTH + 1), "at most"),
            ("Ada\x00", "control characters"),
            ("Ada​", "control characters"),  # zero-width space
        ],
    )
    def test_rejects_unusable_names(self, registry: RoomRegistry, name: str, message: str) -> None:
        with pytest.raises(InvalidName, match=message):
            registry.create(GAME, name)

    def test_allows_a_name_of_the_maximum_length(self, registry: RoomRegistry) -> None:
        registry.create(GAME, "x" * MAX_NAME_LENGTH)


class TestSeats:
    def test_token_finds_its_seat(self, registry: RoomRegistry) -> None:
        room, ada = registry.create(GAME, "Ada")
        registry.join(room.id, "Bo")

        assert room.seat_for(ada.token) == ada

    def test_rejects_a_token_with_no_seat(self, registry: RoomRegistry) -> None:
        room, _ = registry.create(GAME, "Ada")

        with pytest.raises(NotSeated):
            room.seat_for("not a token")

    def test_token_from_another_room_has_no_seat(self, registry: RoomRegistry) -> None:
        room, _ = registry.create(GAME, "Ada")
        _, elsewhere = registry.create(GAME, "Bo")

        with pytest.raises(NotSeated):
            room.seat_for(elsewhere.token)


class TestLeave:
    def test_frees_the_seat(self, registry: RoomRegistry) -> None:
        room, ada = registry.create(GAME, "Ada")
        _, bo = registry.join(room.id, "Bo")

        registry.leave(room.id, bo.token)

        assert list(room.seats.values()) == [ada]

    def test_frees_the_name(self, registry: RoomRegistry) -> None:
        room, _ = registry.create(GAME, "Ada")
        _, bo = registry.join(room.id, "Bo")
        registry.leave(room.id, bo.token)

        registry.join(room.id, "Bo")

    def test_last_player_leaving_closes_the_room(self, registry: RoomRegistry) -> None:
        room, ada = registry.create(GAME, "Ada")

        registry.leave(room.id, ada.token)

        assert registry.rooms() == []
        with pytest.raises(RoomNotFound):
            registry.get(room.id)

    def test_rejects_a_token_with_no_seat(self, registry: RoomRegistry) -> None:
        room, _ = registry.create(GAME, "Ada")

        with pytest.raises(NotSeated):
            registry.leave(room.id, "not a token")


class TestIdleRooms:
    def test_idle_room_closes(self, registry: RoomRegistry, clock: FakeClock) -> None:
        registry.create(GAME, "Ada")

        clock.now += IDLE_SECONDS + 1

        assert registry.rooms() == []

    def test_room_stays_open_until_the_timeout(
        self, registry: RoomRegistry, clock: FakeClock
    ) -> None:
        room, _ = registry.create(GAME, "Ada")

        clock.now += IDLE_SECONDS

        assert registry.rooms() == [room]

    def test_joining_keeps_a_room_open(self, registry: RoomRegistry, clock: FakeClock) -> None:
        room, _ = registry.create(GAME, "Ada")
        clock.now += IDLE_SECONDS - 1
        registry.join(room.id, "Bo")

        clock.now += IDLE_SECONDS - 1

        assert registry.rooms() == [room]

    def test_closed_rooms_free_up_room_for_more(
        self, registry: RoomRegistry, clock: FakeClock
    ) -> None:
        for _ in range(MAX_ROOMS):
            registry.create(GAME, "Ada")
        clock.now += IDLE_SECONDS + 1

        registry.create(GAME, "Ada")

    def test_most_recently_active_rooms_are_listed_first(
        self, registry: RoomRegistry, clock: FakeClock
    ) -> None:
        older, _ = registry.create(GAME, "Ada")
        clock.now += 1
        newer, _ = registry.create(GAME, "Bo")
        clock.now += 1
        registry.join(older.id, "Cy")

        assert registry.rooms() == [older, newer]


class TestConnections:
    def test_connecting_marks_the_player_connected(self, registry: RoomRegistry) -> None:
        room, ada = registry.create(GAME, "Ada")

        _, seat, connection = registry.connect(room.id, ada.token)

        assert seat == ada
        assert room.connections == {ada.player_id: connection}

    def test_rejects_a_token_with_no_seat(self, registry: RoomRegistry) -> None:
        room, _ = registry.create(GAME, "Ada")

        with pytest.raises(NotSeated):
            registry.connect(room.id, "not a token")

    def test_connecting_again_closes_the_old_connection(self, registry: RoomRegistry) -> None:
        room, ada = registry.create(GAME, "Ada")
        _, _, old = registry.connect(room.id, ada.token)

        _, _, new = registry.connect(room.id, ada.token)

        assert old.closed
        assert room.connections == {ada.player_id: new}

    def test_disconnecting_marks_the_player_disconnected(self, registry: RoomRegistry) -> None:
        room, ada = registry.create(GAME, "Ada")
        _, _, connection = registry.connect(room.id, ada.token)

        registry.disconnect(room.id, ada.player_id, connection)

        assert room.connections == {}

    def test_a_replaced_connection_ending_changes_nothing(self, registry: RoomRegistry) -> None:
        room, ada = registry.create(GAME, "Ada")
        _, _, old = registry.connect(room.id, ada.token)
        _, _, new = registry.connect(room.id, ada.token)

        registry.disconnect(room.id, ada.player_id, old)

        assert room.connections == {ada.player_id: new}

    def test_a_connection_ending_after_its_room_closed_changes_nothing(
        self, registry: RoomRegistry
    ) -> None:
        room, ada = registry.create(GAME, "Ada")
        _, _, connection = registry.connect(room.id, ada.token)
        registry.leave(room.id, ada.token)

        registry.disconnect(room.id, ada.player_id, connection)

        assert registry.rooms() == []

    def test_leaving_closes_the_connection(self, registry: RoomRegistry) -> None:
        room, ada = registry.create(GAME, "Ada")
        registry.join(room.id, "Bo")
        _, _, connection = registry.connect(room.id, ada.token)

        registry.leave(room.id, ada.token)

        assert connection.closed
        assert room.connections == {}

    def test_a_room_with_a_connection_never_idles(
        self, registry: RoomRegistry, clock: FakeClock
    ) -> None:
        room, ada = registry.create(GAME, "Ada")
        registry.connect(room.id, ada.token)

        clock.now += 10 * IDLE_SECONDS

        assert registry.rooms() == [room]

    def test_idle_time_counts_from_the_last_disconnect(
        self, registry: RoomRegistry, clock: FakeClock
    ) -> None:
        room, ada = registry.create(GAME, "Ada")
        _, _, connection = registry.connect(room.id, ada.token)
        clock.now += 10 * IDLE_SECONDS
        registry.disconnect(room.id, ada.player_id, connection)

        clock.now += IDLE_SECONDS - 1

        assert registry.rooms() == [room]
