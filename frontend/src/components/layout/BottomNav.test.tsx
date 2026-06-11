import { screen, within } from "@testing-library/react";
import { MemoryRouter, useInRouterContext } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { renderWithProviders } from "../../test/test-utils";
import { BottomNav } from "./BottomNav";

function BottomNavHarness() {
  return useInRouterContext() ? (
    <BottomNav />
  ) : (
    <MemoryRouter initialEntries={["/"]}>
      <BottomNav />
    </MemoryRouter>
  );
}

describe("BottomNav", () => {
  it("renders the four MVP tabs", () => {
    renderWithProviders(<BottomNavHarness />);

    const nav = screen.getByRole("navigation", { name: /primary/i });
    const links = within(nav).getAllByRole("link");

    expect(links).toHaveLength(4);
    expect(links.map((link) => link.textContent)).toEqual([
      "Home",
      "Inventory",
      "Advice",
      "Profile",
    ]);
    expect(within(nav).getByRole("link", { name: /advice/i })).toBeTruthy();
  });
});
