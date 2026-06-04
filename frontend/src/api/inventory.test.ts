import { afterEach, describe, expect, it, vi } from "vitest";
import type { InventoryItem } from "./types";
import {
  confirmInventoryChange,
  fetchInventory,
  fetchStorageStates,
  patchInventoryItem,
} from "./inventory";

function inventoryItem(overrides: Partial<InventoryItem> = {}): InventoryItem {
  return {
    id: 1,
    evidence_id: "evidence-1",
    user_id: 1,
    camera_id: null,
    food: {
      id: 1,
      model_label: "apple",
      display_name: "Apple",
    },
    detected_quantity: 2,
    confirmed_quantity: 2,
    unit: "个",
    storage_location: "pantry",
    first_seen_at: "2026-06-01T00:00:00Z",
    last_seen_at: "2026-06-02T00:00:00Z",
    days_stored: 2,
    safe_days: 5,
    remaining_days: 3,
    storage_state: "fresh",
    eat_priority_rank: 1,
    status: "available",
    source_event_id: null,
    pending_change_type: "none",
    pending_detected_quantity: null,
    message: null,
    ...overrides,
  };
}

function jsonResponse(payload: unknown): Response {
  return {
    ok: true,
    status: 200,
    headers: new Headers({ "content-type": "application/json" }),
    json: vi.fn().mockResolvedValue(payload),
    text: vi.fn().mockResolvedValue(""),
  } as unknown as Response;
}

describe("inventory api", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetches inventory and filters unsupported foods", async () => {
    const items = [
      inventoryItem({ id: 1 }),
      inventoryItem({
        id: 2,
        food: { id: 2, model_label: "mango", display_name: "Mango" },
      }),
    ];
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(items));
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchInventory()).resolves.toEqual([items[0]]);
    expect(fetchMock.mock.calls[0][0]).toBe("/api/inventory");
  });

  it("fetches storage states and filters unsupported foods", async () => {
    const items = [
      inventoryItem({ id: 1, food: { id: 1, model_label: "pear", display_name: "Pear" } }),
      inventoryItem({
        id: 2,
        food: { id: 2, model_label: "grape", display_name: "Grape" },
      }),
    ];
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(items));
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchStorageStates()).resolves.toEqual([items[0]]);
    expect(fetchMock.mock.calls[0][0]).toBe("/api/inventory/storage-states");
  });

  it("patches inventory item with body", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(inventoryItem()));
    vi.stubGlobal("fetch", fetchMock);

    await patchInventoryItem(42, {
      confirmed_quantity: 3,
      storage_location: "refrigerate",
    });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/inventory/42");
    expect(init.method).toBe("PATCH");
    expect(init.body).toBe(
      JSON.stringify({
        confirmed_quantity: 3,
        storage_location: "refrigerate",
      }),
    );
  });

  it("confirms inventory change with body", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(inventoryItem()));
    vi.stubGlobal("fetch", fetchMock);

    await confirmInventoryChange(42, {
      new_quantity: 1,
      status: "available",
      as_new_batch: false,
    });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/inventory/42/confirm-change");
    expect(init.method).toBe("POST");
    expect(init.body).toBe(
      JSON.stringify({
        new_quantity: 1,
        status: "available",
        as_new_batch: false,
      }),
    );
  });
});
