import { describe, expect, it } from "vitest";

import { pageAt, roomPath } from "./navigation";

describe("pageAt", () => {
  it.each([
    ["/", { name: "lobby" }],
    ["/rooms/K7QXM", { name: "room", roomId: "K7QXM" }],
    ["/rooms/k7qxm/", { name: "room", roomId: "K7QXM" }],
    ["/rooms/", { name: "not found" }],
    ["/rooms/K7QXM/extra", { name: "not found" }],
    ["/elsewhere", { name: "not found" }],
  ])("reads %s", (path, page) => {
    expect(pageAt(path)).toEqual(page);
  });

  it("reads back a room's own path", () => {
    expect(pageAt(roomPath("K7QXM"))).toEqual({ name: "room", roomId: "K7QXM" });
  });
});
