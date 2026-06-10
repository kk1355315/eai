import { screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useTodayAdvice } from "../api/advice";
import { useInventory } from "../api/inventory";
import { renderWithProviders } from "../test/test-utils";
import HomePage from "./HomePage";

vi.mock("../api/advice", () => ({
  useTodayAdvice: vi.fn(),
}));

vi.mock("../api/inventory", () => ({
  useInventory: vi.fn(),
}));

const mockUseTodayAdvice = vi.mocked(useTodayAdvice);
const mockUseInventory = vi.mocked(useInventory);

function queryResult(data: unknown) {
  return {
    data,
    error: null,
    isError: false,
    isLoading: false,
    refetch: vi.fn(),
  } as never;
}

function errorResult() {
  return {
    data: undefined,
    error: new Error("backend offline"),
    isError: true,
    isLoading: false,
    refetch: vi.fn(),
  } as never;
}

describe("HomePage", () => {
  beforeEach(() => {
    mockUseTodayAdvice.mockReturnValue(
      queryResult({
        today_priority: [
          {
            food: "banana",
            display_name: "Banana",
            storage_state: "fresh",
            days_stored: 1,
            safe_days: 3,
            remaining_days: 1,
            eat_priority_rank: 1,
            basis: ["Banana is ready first."],
            evidence_ids: ["inventory_1"],
          },
          {
            food: "pear",
            display_name: "Pear",
            storage_state: "check_required",
            days_stored: 4,
            safe_days: 3,
            remaining_days: null,
            eat_priority_rank: null,
            basis: ["Pear needs checking."],
            evidence_ids: ["inventory_2"],
          },
          {
            food: "mango",
            display_name: "Mango",
            storage_state: "fresh",
            days_stored: 1,
            safe_days: 3,
            remaining_days: 1,
            eat_priority_rank: 2,
            basis: ["Mango is not supported."],
            evidence_ids: ["inventory_3"],
          },
        ],
        check_required: [
          {
            food: "pear",
            display_name: "Pear",
            storage_state: "check_required",
            days_stored: 4,
            safe_days: 3,
            remaining_days: null,
            eat_priority_rank: null,
            basis: ["Inspect before eating."],
            evidence_ids: ["inventory_2"],
          },
        ],
      }),
    );
    mockUseInventory.mockReturnValue(
      queryResult([
          {
            id: 1,
            food: { model_label: "banana", display_name: "Banana" },
            confirmed_quantity: 2,
            unit: "piece",
            remaining_days: 1,
            storage_state: "fresh",
            status: "available",
            pending_change_type: "none",
          },
          {
            id: 2,
            food: { model_label: "mango", display_name: "Mango" },
            confirmed_quantity: 1,
            unit: "piece",
            remaining_days: 1,
            storage_state: "fresh",
            status: "available",
            pending_change_type: "none",
          },
        ]),
    );
  });

  it("hides non-MVP foods and keeps check_required fruit out of Priority", () => {
    renderWithProviders(<HomePage />);

    const priority = screen.getByRole("heading", { name: "Today's priority" }).closest("section");
    const needCheck = screen.getByRole("heading", { name: "Need Check" }).closest("section");

    expect(priority).toBeTruthy();
    expect(needCheck).toBeTruthy();
    expect(screen.queryByText("Mango")).toBeNull();
    expect(within(priority as HTMLElement).getByText("Banana")).toBeTruthy();
    expect(within(priority as HTMLElement).queryByText("Pear")).toBeNull();
    expect(within(needCheck as HTMLElement).queryByText("Banana")).toBeNull();
    expect(within(needCheck as HTMLElement).getByText("Pear")).toBeTruthy();
  });

  it("shows an error instead of static preview fruit when API calls fail", () => {
    mockUseTodayAdvice.mockReturnValue(errorResult());
    mockUseInventory.mockReturnValue(errorResult());

    renderWithProviders(<HomePage />);

    expect(screen.getByRole("alert")).toBeTruthy();
    expect(screen.queryByText("Banana")).toBeNull();
    expect(screen.queryByText("Apple")).toBeNull();
  });
});
