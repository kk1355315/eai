import { describe, expect, it } from "vitest";
import type {
  AdviceItem,
  InventoryItem,
  TodayAdviceResponse,
} from "../api/types";
import {
  filterSupportedAdviceItems,
  filterSupportedInventory,
  buildHomeFruitData,
  filterSupportedTodayAdvice,
  mapAdviceItem,
  mapAdviceItems,
  mapInventory,
  mapInventoryItem,
  mapTodayAdvice,
  mapTodayAdviceItem,
} from "./mappers";

function inventoryItem(overrides: Partial<InventoryItem> = {}): InventoryItem {
  return {
    id: 1,
    evidence_id: "evidence-1",
    user_id: 1,
    camera_id: "camera-1",
    food: {
      id: 1,
      model_label: "apple",
      display_name: "Backend Apple",
    },
    detected_quantity: 2,
    confirmed_quantity: 1,
    unit: "个",
    storage_location: "refrigerate",
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

const eatFirstAdvice: AdviceItem = {
  title: "Eat the pears first",
  content: "Use pears before other fruit.",
  action_type: "eat_first",
  related_foods: ["pear", "mango", "apple"],
  basis: ["remaining days"],
  evidence_ids: ["evidence-1"],
  confidence: "high",
};

describe("mappers", () => {
  it("filters inventory to the supported four fruit labels", () => {
    const unsupported = inventoryItem({
      id: 2,
      food: { id: 2, model_label: "mango", display_name: "Mango" },
    });

    expect(filterSupportedInventory([inventoryItem(), unsupported])).toEqual([
      inventoryItem(),
    ]);
  });

  it("maps supported inventory and drops unsupported inventory", () => {
    expect(mapInventoryItem(inventoryItem())).toMatchObject({
      id: 1,
      evidenceId: "evidence-1",
      food: "apple",
      displayName: "苹果",
      quantity: 1,
      detectedQuantity: 2,
      storageLocationLabel: "冷藏",
      remainingDaysText: "还剩 3 天",
      needsConfirmation: false,
    });

    expect(
      mapInventoryItem(
        inventoryItem({
          food: { id: 9, model_label: "mango", display_name: "Mango" },
        }),
      ),
    ).toBeNull();

    expect(
      mapInventory([
        inventoryItem({ id: 1 }),
        inventoryItem({
          id: 2,
          food: { id: 2, model_label: "mango", display_name: "Mango" },
        }),
      ]),
    ).toHaveLength(1);
  });

  it("marks inventory as needing confirmation for pending status or changes", () => {
    expect(
      mapInventoryItem(inventoryItem({ status: "pending_confirm" })),
    ).toMatchObject({ needsConfirmation: true });
    expect(
      mapInventoryItem(inventoryItem({ pending_change_type: "new_quantity" })),
    ).toMatchObject({ needsConfirmation: true });
  });

  it("filters and maps today advice to supported fruit only", () => {
    const advice: TodayAdviceResponse = {
      today_priority: [
        {
          food: "banana",
          display_name: "Backend Banana",
          storage_state: "eat_soon",
          days_stored: 4,
          safe_days: 5,
          remaining_days: 1,
          eat_priority_rank: 2,
          basis: ["ripe"],
          evidence_ids: ["evidence-2"],
        },
        {
          food: "mango",
          display_name: "Mango",
          storage_state: "fresh",
          days_stored: 1,
          safe_days: 7,
          remaining_days: 6,
          basis: [],
          evidence_ids: [],
        },
      ],
      check_required: [
        {
          food: "litchi",
          display_name: "Backend Litchi",
          storage_state: "check_required",
          days_stored: 3,
          safe_days: 3,
          remaining_days: 0,
          basis: ["check surface"],
          evidence_ids: ["evidence-3"],
        },
      ],
    };

    expect(filterSupportedTodayAdvice(advice).today_priority).toHaveLength(1);
    expect(mapTodayAdviceItem(advice.today_priority[0])).toMatchObject({
      food: "banana",
      displayName: "香蕉",
      remainingDaysText: "还剩 1 天",
    });
    expect(mapTodayAdviceItem(advice.today_priority[1])).toBeNull();
    expect(mapTodayAdvice(advice)).toMatchObject({
      todayPriority: [{ food: "banana" }],
      checkRequired: [{ food: "litchi" }],
    });
  });

  it("does not synthesize home need-check items from inventory fallback", () => {
    const data = buildHomeFruitData(
      { today_priority: [], check_required: [] },
      [
        inventoryItem({
          storage_state: "check_required",
          confirmed_quantity: 1,
          status: "available",
        }),
      ],
    );

    expect(data.needCheck).toEqual([]);
  });

  it("filters advice related foods while preserving general advice", () => {
    const filtered = filterSupportedAdviceItems([
      eatFirstAdvice,
      {
        ...eatFirstAdvice,
        title: "Unsupported only",
        action_type: "eat_first",
        related_foods: ["mango"],
      },
      {
        ...eatFirstAdvice,
        title: "General",
        action_type: "general",
        related_foods: ["mango"],
      },
    ]);

    expect(filtered).toEqual([
      { ...eatFirstAdvice, related_foods: ["pear", "apple"] },
      {
        ...eatFirstAdvice,
        title: "General",
        action_type: "general",
        related_foods: [],
      },
    ]);

    expect(mapAdviceItem(eatFirstAdvice)).toMatchObject({
      relatedSupportedFoods: ["pear", "apple"],
      primaryFood: "pear",
      actionLabel: "优先吃",
    });
    expect(mapAdviceItems([eatFirstAdvice])).toHaveLength(1);
  });
});
