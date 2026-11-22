import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { goTo } from "../navigation";
import { savedName, savedSeat } from "../rooms/saved";
import { fakeServer, player, room, seat } from "../testing/fakes";
import { Lobby } from "./Lobby";

vi.mock("../navigation", async (original) => ({
  ...(await original<typeof import("../navigation")>()),
  goTo: vi.fn(),
}));

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe("Lobby", () => {
  it("lists each game's open rooms, linking to them", async () => {
    fakeServer({
      "GET /api/rooms": () => ({
        status: 200,
        body: [room("K7QXM", [player("p1", "Ada"), player("p2", "Bo")])],
      }),
    });

    render(<Lobby />);

    const rooms = await screen.findByRole("list", { name: "Open rooms" });
    const link = within(rooms).getByRole("link", { name: "Ada, Bo" });
    expect(link).toHaveAttribute("href", "/rooms/K7QXM");
    expect(within(rooms).getByText("2/8")).toBeInTheDocument();
  });

  it("says when there are no open rooms", async () => {
    fakeServer({ "GET /api/rooms": () => ({ status: 200, body: [] }) });

    render(<Lobby />);

    expect(await screen.findByText("No open rooms yet.")).toBeInTheDocument();
  });

  it("creates a room, remembers the seat, and goes to it", async () => {
    const created = room("K7QXM", [player("p1", "Ada")]);
    const fetch = fakeServer({
      "GET /api/rooms": () => ({ status: 200, body: [] }),
      "POST /api/rooms": () => ({ status: 201, body: seat(created, "p1", "secret") }),
    });
    render(<Lobby />);

    await userEvent.type(screen.getByLabelText("Your name"), "Ada");
    await userEvent.click(screen.getByRole("button", { name: "New room" }));

    expect(fetch).toHaveBeenCalledWith(
      "/api/rooms",
      expect.objectContaining({ body: JSON.stringify({ game: "graph-artillery", name: "Ada" }) }),
    );
    expect(savedSeat("K7QXM")).toEqual({ playerId: "p1", token: "secret" });
    expect(savedName()).toBe("Ada");
    expect(goTo).toHaveBeenCalledWith("/rooms/K7QXM");
  });

  it("shows why a room couldn't be created", async () => {
    fakeServer({
      "GET /api/rooms": () => ({ status: 200, body: [] }),
      "POST /api/rooms": () => ({ status: 422, body: { detail: "Choose a name." } }),
    });
    render(<Lobby />);

    await userEvent.click(screen.getByRole("button", { name: "New room" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Choose a name.");
    expect(goTo).not.toHaveBeenCalled();
  });
});
