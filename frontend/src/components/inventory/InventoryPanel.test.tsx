import { fireEvent, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "../../test/test-utils";
import { InventoryPanel, type InventoryItem } from "./InventoryPanel";

function inventoryItem(overrides: Partial<InventoryItem> = {}): InventoryItem {
  return {
    id: 1,
    evidence_id: "inventory_1",
    user_id: 1,
    camera_id: "camera-1",
    food: {
      id: 1,
      model_label: "apple",
      display_name: "Apple",
    },
    confirmed_quantity: 2,
    detected_quantity: 2,
    unit: "piece",
    storage_location: "pantry",
    first_seen_at: "2026-06-01T10:00:00+08:00",
    days_stored: 2,
    remaining_days: 3,
    safe_days: 5,
    eat_priority_rank: 1,
    last_seen_at: "2026-06-04T12:00:00+08:00",
    created_at: "2026-06-01T12:00:00+08:00",
    storage_state: "fresh",
    source_event_id: 9,
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

  it("renders backend inventory fields and confirm-change controls", () => {
    const onConfirmChange = vi.fn();
    renderInventory([
      inventoryItem({
        id: 11,
        pending_change_type: "possible_added",
        pending_detected_quantity: 5,
        status: "pending_confirm",
      }),
    ], { onConfirmChange });

    for (const label of [
      "id",
      "evidence_id",
      "user_id",
      "camera_id",
      "food_id",
      "food_name",
      "confirmed_quantity",
      "detected_quantity",
      "unit",
      "storage_location",
      "status",
      "storage_state",
      "days_stored",
      "safe_days",
      "remaining_days",
      "eat_priority_rank",
      "first_seen_at",
      "last_seen_at",
      "created_at",
      "source_event_id",
      "pending_change_type",
      "pending_detected_quantity",
      "message",
    ]) {
      expect(screen.getByText(label)).toBeTruthy();
    }
    expect(screen.getByRole("button", { name: /确认/i })).toBeTruthy();
    expect(screen.queryByRole("button", { name: /ate/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /tossed/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /bought/i })).toBeNull();
    expect(screen.getByRole("spinbutton")).toBeTruthy();
    expect(screen.queryByRole("combobox")).toBeNull();
  });

  it("uses pending_detected_quantity as the default confirm quantity", () => {
    const onConfirmChange = vi.fn();
    renderInventory([
      inventoryItem({
        id: 11,
        confirmed_quantity: 0,
        pending_change_type: "new_quantity",
        pending_detected_quantity: 1,
        status: "pending_confirm",
      }),
    ], { onConfirmChange });

    expect(screen.getByRole("spinbutton")).toHaveAttribute("placeholder", "1");
    fireEvent.click(screen.getByRole("button", { name: /确认/i }));

    expect(onConfirmChange).toHaveBeenCalledWith(11, {
      new_quantity: 1,
      status: "available",
      as_new_batch: false,
    });
  });

  it("does not recommend eating not_recommended inventory", () => {
    renderInventory([
      inventoryItem({
        storage_state: "not_recommended",
        remaining_days: null,
      }),
    ]);

    expect(screen.getByText("Check required")).toBeTruthy();
    expect(screen.queryByText("Eat soon")).toBeNull();
  });
});
