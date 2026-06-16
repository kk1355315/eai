import { fireEvent, screen, waitFor, within } from "@testing-library/react";
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
    expect(within(list).getByText("2 pieces")).toBeTruthy();
    expect(within(list).queryByText("Vegetables")).toBeNull();
  });

  it("hides zero-quantity inventory even when it has a pending change", () => {
    renderInventory([
      inventoryItem({ id: 11, confirmed_quantity: 0 }),
      inventoryItem({
        id: 12,
        confirmed_quantity: 0,
        pending_change_type: "possible_consumed",
        pending_detected_quantity: 0,
        status: "pending_confirm",
      }),
    ]);

    expect(screen.getByLabelText("Check")).toBeTruthy();
    expect(screen.queryByText("苹果")).toBeNull();
    expect(screen.queryByText("0 pieces")).toBeNull();
  });

  it("renders summary and controls in Chinese", () => {
    renderWithProviders(
      <InventoryPanel
        items={[inventoryItem({ unit: "piece" })]}
        onConfirmChange={vi.fn()}
        onCreateUserFoodEvent={vi.fn()}
        onPatchInventory={vi.fn()}
      />,
      { language: "zh" },
    );

    const summary = screen.getByLabelText("库存概览");
    expect(within(summary).getByText("总数")).toBeTruthy();
    expect(within(summary).getByText("新鲜")).toBeTruthy();
    expect(within(summary).getByText("临期")).toBeTruthy();
    expect(screen.getByRole("button", { name: "更改" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "确认" })).toBeNull();
    expect(screen.queryByRole("button", { name: "已食用" })).toBeNull();
    expect(screen.getByText("2 个")).toBeTruthy();
  });

  it("renders pending and check-required items expanded in the check section", () => {
    const onConfirmChange = vi.fn();
    renderInventory([
      inventoryItem({
        id: 11,
        pending_change_type: "possible_added",
        pending_detected_quantity: 5,
        status: "pending_confirm",
      }),
      inventoryItem({
        id: 12,
        food: { id: 2, model_label: "banana", display_name: "Banana" },
        pending_change_type: "none",
        storage_state: "check_required",
        remaining_days: -2,
        status: "available",
      }),
    ], { onConfirmChange });

    expect(screen.getAllByText("Pantry").length).toBeGreaterThan(0);
    expect(screen.getByText("3 days left")).toBeTruthy();
    expect(screen.getAllByText(/Seen 2026-06-04 12:00/).length).toBeGreaterThan(0);
    expect(screen.getByText("Possibly added")).toBeTruthy();
    expect(screen.queryByText("evidence_id")).toBeNull();
    expect(screen.queryByText("camera_id")).toBeNull();
    expect(screen.queryByText("pending_detected_quantity")).toBeNull();
    expect(screen.getByText("香蕉")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /edit/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /confirm/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /new batch/i })).toBeNull();
    expect(screen.getAllByRole("button", { name: /ate/i }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: /tossed/i }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: /keep a few days/i }).length).toBeGreaterThan(0);
    expect(screen.queryByRole("button", { name: /bought/i })).toBeNull();
    expect(screen.getAllByRole("spinbutton").length).toBeGreaterThan(0);
    expect(screen.queryByRole("combobox", { name: /storage location/i })).toBeNull();
  });

  it("snoozes a check item with selected days", async () => {
    const onConfirmChange = vi.fn();
    renderInventory([
      inventoryItem({
        id: 11,
        confirmed_quantity: 3,
        remaining_days: -1,
        storage_state: "check_required",
      }),
    ], { onConfirmChange });

    fireEvent.click(screen.getByRole("button", { name: /keep a few days/i }));
    fireEvent.change(screen.getByRole("combobox", { name: /remind again in/i }), {
      target: { value: "5" },
    });
    fireEvent.click(screen.getByRole("button", { name: /confirm/i }));

    expect(onConfirmChange).toHaveBeenCalledWith(11, {
      new_quantity: 3,
      status: "available",
      as_new_batch: false,
      snooze_days: 5,
    });
    await waitFor(() => {
      expect(within(screen.getByLabelText("Check")).queryByText("苹果")).toBeNull();
      expect(within(screen.getByLabelText("Inventory")).getByText("苹果")).toBeTruthy();
    });
  });

  it("creates quick user food events for ate, tossed, and bought", () => {
    const onCreateUserFoodEvent = vi.fn();
    renderInventory([inventoryItem({ id: 11 })], { onCreateUserFoodEvent });

    fireEvent.click(screen.getByRole("button", { name: /edit/i }));
    fireEvent.change(screen.getByLabelText(/event quantity/i), {
      target: { value: "2" },
    });
    fireEvent.click(screen.getByRole("button", { name: /ate/i }));
    fireEvent.click(screen.getByRole("button", { name: /tossed/i }));
    fireEvent.click(screen.getByRole("button", { name: /bought/i }));

    expect(onCreateUserFoodEvent).toHaveBeenNthCalledWith(1, {
      food_id: "apple",
      event_type: "consumed",
      quantity: 2,
      inventory_id: 11,
    });
    expect(onCreateUserFoodEvent).toHaveBeenNthCalledWith(2, {
      food_id: "apple",
      event_type: "discarded",
      quantity: 2,
      inventory_id: 11,
    });
    expect(onCreateUserFoodEvent).toHaveBeenNthCalledWith(3, {
      food_id: "apple",
      event_type: "purchased",
      quantity: 2,
      inventory_id: 11,
    });
  });

  it("uses custom event quantity in the check section", () => {
    const onCreateUserFoodEvent = vi.fn();
    renderInventory([
      inventoryItem({
        id: 11,
        confirmed_quantity: 3,
        remaining_days: -2,
        storage_state: "check_required",
      }),
    ], { onCreateUserFoodEvent });

    fireEvent.change(screen.getByLabelText(/event quantity/i), {
      target: { value: "2" },
    });
    fireEvent.click(screen.getByRole("button", { name: /ate/i }));

    expect(onCreateUserFoodEvent).toHaveBeenCalledWith({
      food_id: "apple",
      event_type: "consumed",
      quantity: 2,
      inventory_id: 11,
    });
  });

  it("patches storage location from the row selector", () => {
    const onPatchInventory = vi.fn();
    renderInventory([inventoryItem({ id: 11 })], { onPatchInventory });

    fireEvent.click(screen.getByRole("button", { name: /edit/i }));
    fireEvent.change(screen.getByRole("combobox", { name: /storage location/i }), {
      target: { value: "freeze" },
    });

    expect(onPatchInventory).toHaveBeenCalledWith(11, {
      storage_location: "freeze",
    });
  });

  it("collapses edit controls after submitting a change", async () => {
    const onCreateUserFoodEvent = vi.fn();
    renderInventory([inventoryItem({ id: 11 })], { onCreateUserFoodEvent });

    fireEvent.click(screen.getByRole("button", { name: /edit/i }));
    fireEvent.click(screen.getByRole("button", { name: /tossed/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /edit/i })).toBeTruthy();
    });
    expect(screen.queryByRole("button", { name: /tossed/i })).toBeNull();
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

  it("does not show expired inventory as use-today guidance", () => {
    renderInventory([
      inventoryItem({
        storage_state: "check_required",
        remaining_days: -2,
        message: "已超过参考保存期，系统不推荐直接食用。请检查外观、气味和实际状态后再决定。",
      }),
    ]);

    expect(screen.getByText("2 days past reference")).toBeTruthy();
    expect(screen.getByText(/系统不推荐直接食用/)).toBeTruthy();
    expect(screen.queryByText("Use today")).toBeNull();
  });

  it("shows last seen time in Beijing time", () => {
    renderInventory([
      inventoryItem({
        last_seen_at: "2026-06-04T04:00:00Z",
      }),
    ]);

    expect(screen.getByText("Seen 2026-06-04 12:00")).toBeTruthy();
  });
});
