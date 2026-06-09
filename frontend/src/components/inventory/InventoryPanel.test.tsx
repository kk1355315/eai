import { screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "../../test/test-utils";
import { InventoryPanel, type InventoryItem } from "./InventoryPanel";

function inventoryItem(overrides: Partial<InventoryItem> = {}): InventoryItem {
  return {
    id: 1,
    food: {
      id: 1,
      model_label: "apple",
      display_name: "Apple",
    },
    confirmed_quantity: 2,
    detected_quantity: 2,
    unit: "piece",
    storage_location: "pantry",
    remaining_days: 3,
    safe_days: 5,
    storage_state: "fresh",
    pending_change_type: "none",
    pending_detected_quantity: null,
    status: "available",
    message: null,
    ...overrides,
  };
}

function renderInventory(items: InventoryItem[], overrides = {}) {
  return renderWithProviders(
    <InventoryPanel
      items={items}
      onConfirmChange={vi.fn()}
      onCreateUserFoodEvent={vi.fn()}
      onPatchInventory={vi.fn()}
      {...overrides}
    />,
  );
}

describe("InventoryPanel", () => {
  it("renders the summary and continuous inventory rows", () => {
    renderInventory([inventoryItem()]);

    const summary = screen.getByLabelText("Inventory summary");
    expect(within(summary).getByText("2")).toBeTruthy();
    expect(within(summary).getByText("1")).toBeTruthy();
    expect(within(summary).getByText("0")).toBeTruthy();
    expect(within(summary).getByText("Fresh")).toBeTruthy();
    expect(within(summary).getByText("Expiring")).toBeTruthy();

    const list = screen.getByLabelText("Inventory");
    expect(within(list).getByText("苹果")).toBeTruthy();
    expect(within(list).getByText("2 piece")).toBeTruthy();
    expect(within(list).queryByText("Vegetables")).toBeNull();
  });

  it("does not render row editing controls or quick action buttons", () => {
    renderInventory([
      inventoryItem({
        id: 11,
        pending_change_type: "possible_added",
        pending_detected_quantity: 5,
        status: "pending_confirm",
      }),
    ]);

    expect(screen.queryByRole("button", { name: /confirm change/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /ate/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /tossed/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /bought/i })).toBeNull();
    expect(screen.queryByRole("spinbutton")).toBeNull();
    expect(screen.queryByRole("combobox")).toBeNull();
  });
});
