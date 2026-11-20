import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "./App";
import { GAMES } from "./games";

describe("App", () => {
  it("lists every game", () => {
    render(<App />);

    for (const game of GAMES) {
      expect(screen.getByRole("heading", { name: game.name })).toBeInTheDocument();
    }
  });

  it("signs out with a plain form post to the server", () => {
    render(<App />);

    const form = screen.getByRole("button", { name: "Sign out" }).closest("form");
    expect(form).toHaveAttribute("method", "post");
    expect(form).toHaveAttribute("action", "/logout");
  });
});
