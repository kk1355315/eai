import { useState } from "react";
import {
  useConfirmInventoryChange,
  useInventory,
  usePatchInventory,
} from "../api/inventory";
import { useCreateUserFoodEvent } from "../api/userEvents";
import type { InventoryItem as ApiInventoryItem } from "../api/types";
import {
  InventoryPanel,
  type ConfirmInventoryChange,
  type InventoryItem,
  type InventoryPatch,
  type UserFoodEvent,
} from "../components/inventory/InventoryPanel";

export default function InventoryPage() {
  const inventoryQuery = useInventory();
  const patchInventory = usePatchInventory();
  const confirmChange = useConfirmInventoryChange();
  const createEvent = useCreateUserFoodEvent();
  const [busyItemId, setBusyItemId] = useState<number | null>(null);
  const inventoryItems = inventoryQuery.data ?? [];

  async function handlePatchInventory(itemId: number, patch: InventoryPatch) {
    setBusyItemId(itemId);
    try {
      await patchInventory.mutateAsync({ itemId, patch });
    } finally {
      setBusyItemId(null);
    }
  }

  async function handleConfirmChange(itemId: number, payload: ConfirmInventoryChange) {
    setBusyItemId(itemId);
    try {
      await confirmChange.mutateAsync({ itemId, payload });
    } finally {
      setBusyItemId(null);
    }
  }

  async function handleCreateEvent(payload: UserFoodEvent) {
    setBusyItemId(payload.inventory_id ?? null);
    try {
      await createEvent.mutateAsync(payload);
    } finally {
      setBusyItemId(null);
    }
  }

  const error = inventoryQuery.error instanceof Error ? inventoryQuery.error.message : null;

  return (
    <InventoryPanel
      busyItemId={busyItemId}
      error={error}
      items={inventoryItems.map(toPanelItem)}
      loading={inventoryQuery.isLoading}
      onConfirmChange={handleConfirmChange}
      onCreateUserFoodEvent={handleCreateEvent}
      onPatchInventory={handlePatchInventory}
      onRetry={() => void inventoryQuery.refetch()}
    />
  );
}

function toPanelItem(item: ApiInventoryItem): InventoryItem {
  return {
    id: item.id,
    food: item.food,
    confirmed_quantity: item.confirmed_quantity,
    detected_quantity: item.detected_quantity,
    unit: item.unit,
    storage_location: item.storage_location,
    days_stored: item.days_stored,
    remaining_days: item.remaining_days,
    safe_days: item.safe_days,
    eat_priority_rank: item.eat_priority_rank,
    last_seen_at: item.last_seen_at,
    created_at: item.created_at ?? item.first_seen_at,
    storage_state: normalizeStorageState(item.storage_state),
    pending_change_type: normalizePendingChange(item.pending_change_type),
    pending_detected_quantity: item.pending_detected_quantity,
    status: normalizeInventoryStatus(item.status),
    message: item.message,
  };
}

function normalizeStorageState(value: string | null): InventoryItem["storage_state"] {
  if (
    value === "fresh" ||
    value === "eat_soon" ||
    value === "check_required" ||
    value === "not_recommended"
  ) {
    return value;
  }
  return null;
}

function normalizePendingChange(value: string): InventoryItem["pending_change_type"] {
  if (
    value === "new_quantity" ||
    value === "possible_added" ||
    value === "possible_consumed"
  ) {
    return value;
  }
  return "none";
}

function normalizeInventoryStatus(value: string): InventoryItem["status"] {
  if (
    value === "pending_confirm" ||
    value === "available" ||
    value === "consumed" ||
    value === "discarded" ||
    value === "unknown"
  ) {
    return value;
  }
  return "unknown";
}
