import type { InventoryItem, SupportedFoodLabel } from "../../api/types";

const now = "2026-06-03T12:00:00.000Z";

const fruitNames: Record<SupportedFoodLabel, string> = {
  apple: "Apple",
  banana: "Banana",
  litchi: "Litchi",
  pear: "Pear",
};

export const mvpFruitLabels: SupportedFoodLabel[] = ["apple", "banana", "litchi", "pear"];

export function buildInventoryItem(
  label: SupportedFoodLabel | string,
  overrides: Partial<InventoryItem> = {},
): InventoryItem {
  const index = mvpFruitLabels.indexOf(label as SupportedFoodLabel);
  const id = index >= 0 ? index + 1 : 100;

  return {
    id,
    evidence_id: `evidence-${label}`,
    user_id: 1,
    camera_id: "camera-demo",
    food: {
      id,
      model_label: label,
      display_name: fruitNames[label as SupportedFoodLabel] ?? label,
    },
    detected_quantity: 2,
    confirmed_quantity: 2,
    unit: "piece",
    storage_location: "refrigerate",
    first_seen_at: now,
    last_seen_at: now,
    days_stored: 1,
    safe_days: 3,
    remaining_days: 2,
    storage_state: "fresh",
    eat_priority_rank: null,
    status: "available",
    source_event_id: null,
    pending_change_type: "none",
    pending_detected_quantity: null,
    message: null,
    ...overrides,
  };
}

export const inventoryFixtures = {
  mvpFruits: [
    buildInventoryItem("apple", { eat_priority_rank: 1, remaining_days: 1, storage_state: "eat_soon" }),
    buildInventoryItem("banana", { storage_location: "pantry", safe_days: 2, remaining_days: 1 }),
    buildInventoryItem("litchi", { remaining_days: 0, storage_state: "check_required" }),
    buildInventoryItem("pear", { remaining_days: 4, safe_days: 5 }),
  ],
  nonMvpIngredients: [
    buildInventoryItem("strawberry", { id: 101, food: { id: 101, model_label: "strawberry", display_name: "Strawberry" } }),
    buildInventoryItem("milk", { id: 102, food: { id: 102, model_label: "milk", display_name: "Milk" } }),
  ],
} as const;
