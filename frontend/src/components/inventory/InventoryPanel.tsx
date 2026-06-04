import { ChevronRight, Package } from "lucide-react";
import { useLanguage } from "../../lib/language";
import { FRUIT_IMAGE_SRC } from "../../lib/fruitAssets";
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
  name: string;
  count: string;
  status: "fresh" | "expiring" | "low";
  progress: number;
  image?: string;
  glyph?: string;
  className?: string;
};

const TARGET_ROWS: InventoryRow[] = [
  { name: "Vegetables", count: "12 items", status: "fresh", progress: 54, glyph: "🥦", className: "vegetable" },
  { name: "Fruits", count: "8 items", status: "fresh", progress: 50, image: FRUIT_IMAGE_SRC.apple },
  { name: "Dairy", count: "6 items", status: "expiring", progress: 50, glyph: "🥛", className: "dairy" },
  { name: "Meat", count: "5 items", status: "expiring", progress: 50, glyph: "🥩", className: "meat" },
  { name: "Seafood", count: "4 items", status: "low", progress: 13, glyph: "🍣", className: "seafood" },
  { name: "Eggs", count: "12 items", status: "fresh", progress: 37, glyph: "🥚", className: "eggs" },
  { name: "Drinks", count: "6 items", status: "fresh", progress: 37, glyph: "💧", className: "drinks" },
];

export function InventoryPanel({
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

  return (
    <>
      <section className="inventory-summary-card" aria-label={t("inventorySummary")}>
        <SummaryStat label="Total" value={63} />
        <SummaryStat label="Fresh" tone="fresh" value={48} />
        <SummaryStat label="Expiring" tone="expiring" value={7} />
      </section>

      <section className="inventory-list" aria-label={t("inventory")}>
        {TARGET_ROWS.map((item) => (
          <InventoryCategoryRow item={item} key={item.name} />
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
