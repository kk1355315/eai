import { ChevronRight, Package } from "lucide-react";
import { useLanguage } from "../../lib/language";
import { FRUIT_IMAGE_SRC } from "../../lib/fruitAssets";
import { getFoodDisplayName, isSupportedFoodLabel } from "../../lib/foods";
import "./inventory.css";

export type FoodLabel = "apple" | "banana" | "litchi" | "pear";

export type StorageState =
  | "fresh"
  | "eat_soon"
  | "check_required"
  | "not_recommended"
  | null;

export type PendingChangeType =
  | "none"
  | "new_quantity"
  | "possible_added"
  | "possible_consumed";

export type InventoryStatus =
  | "pending_confirm"
  | "available"
  | "consumed"
  | "discarded"
  | "unknown";

export type InventoryFood = {
  id: number;
  model_label: string;
  display_name: string;
};

export type InventoryItem = {
  id: number;
  food: InventoryFood;
  confirmed_quantity: number;
  detected_quantity?: number;
  unit: string;
  storage_location: "pantry" | "refrigerate" | "freeze" | string;
  remaining_days: number | null;
  safe_days: number | null;
  storage_state: StorageState;
  pending_change_type: PendingChangeType;
  pending_detected_quantity?: number | null;
  status: InventoryStatus;
  message?: string | null;
};

export type InventoryPatch = {
  confirmed_quantity?: number;
  storage_location?: "pantry" | "refrigerate" | "freeze";
  status?: InventoryStatus;
};

export type ConfirmInventoryChange = {
  new_quantity?: number;
  status?: InventoryStatus;
  as_new_batch?: boolean;
};

export type FoodEventType = "consumed" | "discarded" | "purchased";

export type UserFoodEvent = {
  food_id: string;
  event_type: FoodEventType;
  quantity: number;
  inventory_id?: number;
  metadata?: Record<string, unknown>;
};

type InventoryPanelProps = {
  items: InventoryItem[];
  loading?: boolean;
  error?: string | null;
  busyItemId?: number | null;
  onRetry?: () => void;
  onPatchInventory: (itemId: number, patch: InventoryPatch) => Promise<void> | void;
  onConfirmChange: (
    itemId: number,
    payload: ConfirmInventoryChange,
  ) => Promise<void> | void;
  onCreateUserFoodEvent: (event: UserFoodEvent) => Promise<void> | void;
};

type InventoryRow = {
  id: number;
  name: string;
  count: string;
  status: "fresh" | "expiring" | "low";
  progress: number;
  image?: string;
  glyph?: string;
  className?: string;
};

export function InventoryPanel({
  items,
  loading,
  error,
  onRetry,
}: InventoryPanelProps) {
  const { t } = useLanguage();

  if (loading) {
    return <StateCard title={t("loadingInventory")} copy={t("checkingLatestFruitBatches")} />;
  }

  if (error) {
    return <StateCard title={t("inventoryIsOffline")} copy={error} onRetry={onRetry} />;
  }

  const visibleItems = items.filter((item) => item.status !== "consumed" && item.status !== "discarded");
  const rows = visibleItems.map(toInventoryRow);
  const totalQuantity = visibleItems.reduce((total, item) => total + item.confirmed_quantity, 0);
  const freshCount = visibleItems.filter((item) => item.storage_state === "fresh").length;
  const expiringCount = visibleItems.filter((item) =>
    item.storage_state === "eat_soon" ||
    item.storage_state === "check_required" ||
    item.storage_state === "not_recommended",
  ).length;

  return (
    <>
      <section className="inventory-summary-card" aria-label={t("inventorySummary")}>
        <SummaryStat label="Total" value={totalQuantity} />
        <SummaryStat label="Fresh" tone="fresh" value={freshCount} />
        <SummaryStat label="Expiring" tone="expiring" value={expiringCount} />
      </section>

      <section className="inventory-list" aria-label={t("inventory")}>
        {rows.length === 0 ? (
          <StateCard title={t("noFruitBatches")} copy={t("noFruitBatchesCopy")} />
        ) : null}
        {rows.map((item) => (
          <InventoryCategoryRow item={item} key={item.id} />
        ))}
      </section>
    </>
  );
}

function SummaryStat({
  label,
  tone,
  value,
}: {
  label: string;
  tone?: "fresh" | "expiring";
  value: number;
}) {
  return (
    <div className="inventory-summary-stat">
      <strong className={tone ? `summary-${tone}` : undefined}>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function InventoryCategoryRow({ item }: { item: InventoryRow }) {
  return (
    <article className="inventory-row">
      <div className={`inventory-food-image ${item.className ?? ""}`} aria-hidden="true">
        {item.image ? <img alt="" src={item.image} /> : <span>{item.glyph}</span>}
      </div>
      <div className="inventory-row-copy">
        <h2 className="inventory-food-title">{item.name}</h2>
        <p className="inventory-food-meta">{item.count}</p>
      </div>
      <div className="inventory-progress-track" aria-hidden="true">
        <span
          className={`inventory-progress-fill state-${item.status}`}
          style={{ width: `${item.progress}%` }}
        />
      </div>
      <span className={`inventory-state-label state-text-${item.status}`}>
        {formatState(item.status)}
      </span>
      <ChevronRight className="inventory-chevron" size={30} strokeWidth={2.4} />
    </article>
  );
}

function StateCard({
  copy,
  onRetry,
  title,
}: {
  copy: string;
  onRetry?: () => void;
  title: string;
}) {
  const { t } = useLanguage();

  return (
    <section className="inventory-state-card">
      <Package size={30} />
      <h2>{title}</h2>
      <p>{copy}</p>
      {onRetry ? (
        <button onClick={onRetry} type="button">
          {t("retry")}
        </button>
      ) : null}
    </section>
  );
}

function formatState(status: InventoryRow["status"]) {
  if (status === "fresh") return "Fresh";
  if (status === "expiring") return "Expiring";
  return "Low";
}

function toInventoryRow(item: InventoryItem): InventoryRow {
  const food = item.food.model_label;
  const isKnownFruit = isSupportedFoodLabel(food);
  const quantityLabel = `${item.confirmed_quantity} ${item.unit || "items"}`;

  return {
    id: item.id,
    name: getFoodDisplayName(food, item.food.display_name),
    count: item.pending_change_type === "none"
      ? quantityLabel
      : `${quantityLabel} · ${formatPendingChange(item.pending_change_type)}`,
    status: rowStatus(item),
    progress: rowProgress(item),
    image: isKnownFruit ? FRUIT_IMAGE_SRC[food] : undefined,
    glyph: isKnownFruit ? undefined : "•",
    className: isKnownFruit ? food : undefined,
  };
}

function rowStatus(item: InventoryItem): InventoryRow["status"] {
  if (item.status === "pending_confirm" || item.storage_state === "check_required") {
    return "low";
  }
  if (item.storage_state === "eat_soon" || item.storage_state === "not_recommended") {
    return "expiring";
  }
  return "fresh";
}

function rowProgress(item: InventoryItem): number {
  if (item.remaining_days == null || item.safe_days == null || item.safe_days <= 0) {
    return rowStatus(item) === "fresh" ? 72 : 18;
  }

  return Math.max(8, Math.min(100, Math.round((item.remaining_days / item.safe_days) * 100)));
}

function formatPendingChange(change: PendingChangeType) {
  if (change === "new_quantity") return "new quantity";
  if (change === "possible_added") return "possible added";
  if (change === "possible_consumed") return "possible used";
  return "confirmed";
}
