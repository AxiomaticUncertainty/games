import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { forgetSeat, saveName, saveSeat, savedName, savedSeat } from "./saved";

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("seats", () => {
  it("remembers a seat per room", () => {
    saveSeat("K7QXM", { playerId: "p1", token: "secret" });

    expect(savedSeat("K7QXM")).toEqual({ playerId: "p1", token: "secret" });
    expect(savedSeat("OTHER")).toBeNull();
  });

  it("ignores the case of room ids", () => {
    saveSeat("k7qxm", { playerId: "p1", token: "secret" });

    expect(savedSeat("K7QXM")).not.toBeNull();
  });

  it("forgets a seat", () => {
    saveSeat("K7QXM", { playerId: "p1", token: "secret" });
    forgetSeat("K7QXM");

    expect(savedSeat("K7QXM")).toBeNull();
  });

  it("treats an unreadable seat as none", () => {
    localStorage.setItem("seat:K7QXM", "{not json");

    expect(savedSeat("K7QXM")).toBeNull();
  });
});

describe("name", () => {
  it("is empty until saved", () => {
    expect(savedName()).toBe("");
  });

  it("remembers the last name used", () => {
    saveName("Ada");

    expect(savedName()).toBe("Ada");
  });
});

describe("when storage is unavailable", () => {
  beforeEach(() => {
    const unavailable = () => {
      throw new DOMException("Storage is disabled", "SecurityError");
    };
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(unavailable);
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(unavailable);
    vi.spyOn(Storage.prototype, "removeItem").mockImplementation(unavailable);
  });

  it("forgets rather than failing", () => {
    saveName("Ada");
    saveSeat("K7QXM", { playerId: "p1", token: "secret" });
    forgetSeat("K7QXM");

    expect(savedName()).toBe("");
    expect(savedSeat("K7QXM")).toBeNull();
  });
});
