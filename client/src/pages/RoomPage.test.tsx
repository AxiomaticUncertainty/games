import { act, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { goTo } from "../navigation";
import { savedSeat, saveSeat } from "../rooms/saved";
import { CloseCode, RECONNECT_DELAY_MS } from "../rooms/useRoomConnection";
import { FakeWebSocket, fakeServer, player, room, seat } from "../testing/fakes";
import { RoomPage } from "./RoomPage";

vi.mock("../navigation", async (original) => ({
  ...(await original<typeof import("../navigation")>()),
  goTo: vi.fn(),
}));

const ROOM_ID = "K7QXM";
const adaAlone = room(ROOM_ID, [player("p1", "Ada")]);

beforeEach(() => {
  localStorage.clear();
  FakeWebSocket.install();
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

/** Render the page as a player already seated as `playerId`, and connect. */
function renderSeated(playerId = "p1", token = "secret") {
  saveSeat(ROOM_ID, { playerId, token });
  render(<RoomPage roomId={ROOM_ID} />);
  const socket = FakeWebSocket.latest();
  socket.accept();
  return socket;
}

function players() {
  return within(screen.getByRole("list", { name: "Players" }))
    .getAllByRole("listitem")
    .map((item) => item.textContent);
}

describe("without a seat", () => {
  it("shows who's there and offers to join", async () => {
    fakeServer({ [`GET /api/rooms/${ROOM_ID}`]: () => ({ status: 200, body: adaAlone }) });

    render(<RoomPage roomId={ROOM_ID} />);

    expect(await screen.findByText("Ada")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Join" })).toBeInTheDocument();
    expect(FakeWebSocket.instances).toHaveLength(0);
  });

  it("joins, remembers the seat, and connects", async () => {
    const withBo = room(ROOM_ID, [player("p1", "Ada"), player("p2", "Bo")]);
    fakeServer({
      [`GET /api/rooms/${ROOM_ID}`]: () => ({ status: 200, body: adaAlone }),
      [`POST /api/rooms/${ROOM_ID}/seats`]: () => ({
        status: 201,
        body: seat(withBo, "p2", "bo-secret"),
      }),
    });
    render(<RoomPage roomId={ROOM_ID} />);

    await userEvent.type(screen.getByLabelText("Your name"), "Bo");
    await userEvent.click(screen.getByRole("button", { name: "Join" }));

    expect(savedSeat(ROOM_ID)).toEqual({ playerId: "p2", token: "bo-secret" });
    const socket = FakeWebSocket.latest();
    expect(socket.url).toBe(`ws://${location.host}/api/rooms/${ROOM_ID}/connection`);
    socket.accept();
    expect(socket.sent).toEqual([{ type: "hello", token: "bo-secret" }]);
  });

  it("shows why joining failed", async () => {
    fakeServer({
      [`GET /api/rooms/${ROOM_ID}`]: () => ({ status: 200, body: adaAlone }),
      [`POST /api/rooms/${ROOM_ID}/seats`]: () => ({
        status: 409,
        body: { detail: "Someone in this room is already called Ada." },
      }),
    });
    render(<RoomPage roomId={ROOM_ID} />);

    await userEvent.type(screen.getByLabelText("Your name"), "Ada");
    await userEvent.click(screen.getByRole("button", { name: "Join" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("already called Ada");
  });

  it("says when the room doesn't exist", async () => {
    fakeServer({});

    render(<RoomPage roomId={ROOM_ID} />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Not found.");
  });
});

describe("with a seat", () => {
  it("says hello with the saved token", () => {
    const socket = renderSeated("p1", "secret");

    expect(socket.sent).toEqual([{ type: "hello", token: "secret" }]);
    expect(screen.getByText("Connecting…")).toBeInTheDocument();
  });

  it("shows the players as the server announces them", () => {
    const socket = renderSeated();

    socket.deliver({
      type: "room",
      room: room(ROOM_ID, [player("p1", "Ada"), player("p2", "Bo", false)]),
    });

    expect(players()).toEqual(["Ada (you)", "Bo away"]);
  });

  it("keeps up as players come and go", () => {
    const socket = renderSeated();
    socket.deliver({ type: "room", room: adaAlone });

    socket.deliver({
      type: "room",
      room: room(ROOM_ID, [player("p1", "Ada"), player("p2", "Bo")]),
    });

    expect(players()).toEqual(["Ada (you)", "Bo"]);
  });

  it("reconnects after the connection drops", () => {
    vi.useFakeTimers();
    const first = renderSeated();
    first.deliver({ type: "room", room: adaAlone });

    first.end(1006);
    expect(screen.getByText("Connecting…")).toBeInTheDocument();
    act(() => {
      vi.advanceTimersByTime(RECONNECT_DELAY_MS);
    });

    const second = FakeWebSocket.latest();
    expect(second).not.toBe(first);
    second.accept();
    expect(second.sent).toEqual([{ type: "hello", token: "secret" }]);
  });

  it("offers to take the room back after it's opened elsewhere", async () => {
    const first = renderSeated();
    first.end(CloseCode.REPLACED, "You opened this room somewhere else.");

    expect(screen.getByRole("alert")).toHaveTextContent("somewhere else");
    await userEvent.click(screen.getByRole("button", { name: "Use it here instead" }));

    expect(FakeWebSocket.latest()).not.toBe(first);
  });

  it("offers to join again when the seat is gone", async () => {
    fakeServer({ [`GET /api/rooms/${ROOM_ID}`]: () => ({ status: 200, body: adaAlone }) });
    const socket = renderSeated();

    socket.end(CloseCode.NOT_SEATED, "You don't have a seat in this room.");

    expect(await screen.findByRole("button", { name: "Join" })).toBeInTheDocument();
    expect(savedSeat(ROOM_ID)).toBeNull();
  });

  it("says when the room has closed", () => {
    const socket = renderSeated();

    socket.end(CloseCode.NO_SUCH_ROOM, "There's no room with that id. It may have closed.");

    expect(screen.getByRole("alert")).toHaveTextContent("It may have closed.");
  });

  it("leaves, forgets the seat, and goes back to the lobby", async () => {
    const fetch = fakeServer({ [`POST /api/rooms/${ROOM_ID}/leave`]: () => ({ status: 204 }) });
    const socket = renderSeated("p1", "secret");
    socket.deliver({ type: "room", room: adaAlone });

    await userEvent.click(screen.getByRole("button", { name: "Leave room" }));

    expect(fetch).toHaveBeenCalledWith(
      `/api/rooms/${ROOM_ID}/leave`,
      expect.objectContaining({ body: JSON.stringify({ token: "secret" }) }),
    );
    expect(savedSeat(ROOM_ID)).toBeNull();
    expect(goTo).toHaveBeenCalledWith("/");
  });

  it("closes the connection, without reconnecting, when the page goes away", () => {
    vi.useFakeTimers();
    saveSeat(ROOM_ID, { playerId: "p1", token: "secret" });
    const { unmount } = render(<RoomPage roomId={ROOM_ID} />);
    const socket = FakeWebSocket.latest();

    unmount();
    socket.end(1000);
    act(() => {
      vi.advanceTimersByTime(RECONNECT_DELAY_MS);
    });

    expect(socket.closed).toBe(true);
    expect(FakeWebSocket.instances).toEqual([socket]);
  });
});
