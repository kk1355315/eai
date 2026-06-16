import { type ChangeEvent, useState } from "react";
import { Check, Package } from "lucide-react";
import { useLanguage } from "../../lib/language";
import { FRUIT_IMAGE_SRC } from "../../lib/fruitAssets";
import { getFoodDisplayName, isSupportedFoodLabel } from "../../lib/foods";
import { formatBeijingDateTime } from "../../lib/datetime";
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
  evidence_id?: string;
  user_id?: number;
  camera_id?: string | null;
  food: InventoryFood;
  confirmed_quantity: number;
  detected_quantity?: number;
  unit: string;
  storage_location: "pantry" | "refrigerate" | "freeze" | string;
  first_seen_at?: string | null;
  days_stored: number | null;
  remaining_days: number | null;
  safe_days: number | null;
  eat_priority_rank: number | null;
  last_seen_at: string | null;
  created_at: string | null;
  storage_state: StorageState;
  source_event_id?: number | null;
  pending_change_type: PendingChangeType;
  pending_detected_quantity?: number | null;
  check_snoozed_until?: string | null;
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
  snooze_days?: number;
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
  status: "fresh" | "expiring" | "low" | "notRecommended";
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
  busyItemId,
  onCreateUserFoodEvent,
  onConfirmChange,
  onPatchInventory,
}: InventoryPanelProps) {
  const { t } = useLanguage();
  const [quantityDrafts, setQuantityDrafts] = useState<Record<number, string>>({});
  const [eventQuantityDrafts, setEventQuantityDrafts] = useState<Record<number, string>>({});
  const [expandedItemIds, setExpandedItemIds] = useState<Set<number>>(() => new Set());
  const [snoozeDrafts, setSnoozeDrafts] = useState<Record<number, string>>({});
  const [openSnoozeItemIds, setOpenSnoozeItemIds] = useState<Set<number>>(() => new Set());
  const [locallySnoozedItems, setLocallySnoozedItems] = useState<Record<number, number>>({});

  if (loading) {
    return <StateCard title={t("loadingInventory")} copy={t("checkingLatestFruitBatches")} />;
  }

  if (error) {
    return <StateCard title={t("inventoryIsOffline")} copy={error} onRetry={onRetry} />;
  }

  const visibleItems = items
    .filter(shouldShowInventoryItem)
    .map((item) => applyLocalSnooze(item, locallySnoozedItems[item.id]));
  const pendingItems = visibleItems.filter(needsInventoryConfirmation);
  const regularItems = visibleItems.filter((item) => !needsInventoryConfirmation(item));
  const pendingRows = pendingItems.map((item) => toInventoryRow(item, t));
  const regularRows = regularItems.map((item) => toInventoryRow(item, t));
  const totalQuantity = visibleItems.reduce((total, item) => total + item.confirmed_quantity, 0);
  const freshCount = visibleItems.filter((item) => item.storage_state === "fresh").length;
  const expiringCount = visibleItems.filter((item) =>
    item.storage_state === "eat_soon" ||
    item.storage_state === "check_required" ||
    item.storage_state === "not_recommended",
  ).length;
  const collapseItemControls = (itemId: number) => {
    setExpandedItemIds((current) => {
      if (!current.has(itemId)) return current;
      const next = new Set(current);
      next.delete(itemId);
      return next;
    });
  };
  const toggleItemControls = (itemId: number) => {
    setExpandedItemIds((current) => {
      const next = new Set(current);
      if (next.has(itemId)) {
        next.delete(itemId);
      } else {
        next.add(itemId);
      }
      return next;
    });
  };
  const runItemAction = (itemId: number, action: () => Promise<void> | void) => {
    void Promise.resolve(action()).finally(() => {
      collapseItemControls(itemId);
      closeSnoozeControls(itemId);
    });
  };
  const closeSnoozeControls = (itemId: number) => {
    setOpenSnoozeItemIds((current) => {
      if (!current.has(itemId)) return current;
      const next = new Set(current);
      next.delete(itemId);
      return next;
    });
  };
  const toggleSnoozeControls = (itemId: number) => {
    setOpenSnoozeItemIds((current) => {
      const next = new Set(current);
      if (next.has(itemId)) {
        next.delete(itemId);
      } else {
        next.add(itemId);
      }
      return next;
    });
  };
  const readEventQuantity = (
    itemId: number,
    sourceItem: InventoryItem,
    eventType: FoodEventType,
  ) => {
    const rawQuantity = eventQuantityDrafts[itemId];
    const parsedQuantity =
      rawQuantity === undefined || rawQuantity.trim() === "" ? 1 : Number(rawQuantity);
    const quantity = Number.isFinite(parsedQuantity) && parsedQuantity > 0
      ? Math.floor(parsedQuantity)
      : 1;

    if (eventType === "purchased") {
      return quantity;
    }

    return Math.min(quantity, sourceItem.confirmed_quantity);
  };

  return (
    <>
      <section className="inventory-summary-card" aria-label={t("inventorySummary")}>
        <SummaryStat label={t("total")} value={totalQuantity} />
        <SummaryStat label={t("fresh")} tone="fresh" value={freshCount} />
        <SummaryStat label={t("expiring")} tone="expiring" value={expiringCount} />
      </section>

      <section className="inventory-list" aria-label={t("check")}>
        <h2 className="inventory-list-title">{t("check")}</h2>
        {pendingRows.length === 0 ? (
          <p className="inventory-list-empty">{t("confirmInventoryFirst")}</p>
        ) : null}
        {pendingRows.map((item) => {
          const sourceItem = pendingItems.find((source) => source.id === item.id);
          const snoozeDraft = snoozeDrafts[item.id] ?? "3";
          const readSnoozeDays = () => {
            const nextDays = Number(snoozeDraft);
            return Number.isFinite(nextDays) && nextDays > 0 ? nextDays : 3;
          };

          return (
            <InventoryCategoryRow
              busy={busyItemId === item.id}
              controlsMode="check"
              item={item}
              key={item.id}
              eventQuantityDraft={eventQuantityDrafts[item.id]}
              quantityDraft={quantityDrafts[item.id]}
              snoozeDaysDraft={snoozeDraft}
              snoozeOpen={openSnoozeItemIds.has(item.id)}
              source={sourceItem}
              onCreateEvent={(eventType) => {
                if (!sourceItem) return;

                runItemAction(item.id, () =>
                  onCreateUserFoodEvent({
                    food_id: sourceItem.food.model_label,
                    event_type: eventType,
                    quantity: readEventQuantity(item.id, sourceItem, eventType),
                    inventory_id: sourceItem.id,
                  }),
                );
              }}
              onEventQuantityChange={(event) =>
                setEventQuantityDrafts((current) => ({
                  ...current,
                  [item.id]: event.target.value,
                }))
              }
              onSnoozeDraftChange={(event) =>
                setSnoozeDrafts((current) => ({
                  ...current,
                  [item.id]: event.target.value,
                }))
              }
              onDraftChange={(event) =>
                setQuantityDrafts((current) => ({
                  ...current,
                  [item.id]: event.target.value,
                }))
              }
              onStorageChange={(storageLocation) => {
                runItemAction(item.id, () =>
                  onPatchInventory(item.id, { storage_location: storageLocation }),
                );
              }}
              onConfirm={() => undefined}
              onSnoozeCheck={() => {
                if (!sourceItem) return;

                runItemAction(item.id, () =>
                  Promise.resolve(
                    onConfirmChange(item.id, {
                      new_quantity: sourceItem.confirmed_quantity,
                      status: "available",
                      as_new_batch: false,
                      snooze_days: readSnoozeDays(),
                    }),
                  ).then(() => {
                    setLocallySnoozedItems((current) => ({
                      ...current,
                      [item.id]: readSnoozeDays(),
                    }));
                  }),
                );
              }}
              onToggleSnooze={() => {
                toggleSnoozeControls(item.id);
              }}
              onToggleEdit={() => {
                toggleItemControls(item.id);
              }}
            />
          );
        })}
      </section>

      <section className="inventory-list" aria-label={t("inventory")}>
        <h2 className="inventory-list-title">{t("inventory")}</h2>
        {regularRows.length === 0 && pendingRows.length === 0 ? (
          <StateCard title={t("noFruitBatches")} copy={t("noFruitBatchesCopy")} />
        ) : null}
        {regularRows.map((item) => {
          const sourceItem = regularItems.find((source) => source.id === item.id);
          const isExpanded = expandedItemIds.has(item.id);
          const readQuantity = () => {
              const rawQuantity = quantityDrafts[item.id];
              const nextQuantity =
                rawQuantity === undefined || rawQuantity.trim() === ""
                  ? sourceItem?.pending_detected_quantity ?? sourceItem?.confirmed_quantity
                  : Number(rawQuantity);

              return Number.isFinite(nextQuantity) ? nextQuantity : undefined;
          };

          return (
            <InventoryCategoryRow
              busy={busyItemId === item.id}
              controlsMode={isExpanded ? "expanded" : "collapsed"}
              item={item}
              key={item.id}
              eventQuantityDraft={eventQuantityDrafts[item.id]}
              quantityDraft={quantityDrafts[item.id]}
              source={sourceItem}
              onCreateEvent={(eventType) => {
                if (!sourceItem) return;

                runItemAction(item.id, () =>
                  onCreateUserFoodEvent({
                    food_id: sourceItem.food.model_label,
                    event_type: eventType,
                    quantity: readEventQuantity(item.id, sourceItem, eventType),
                    inventory_id: sourceItem.id,
                  }),
                );
              }}
              onEventQuantityChange={(event) =>
                setEventQuantityDrafts((current) => ({
                  ...current,
                  [item.id]: event.target.value,
                }))
              }
              onDraftChange={(event) =>
                setQuantityDrafts((current) => ({
                  ...current,
                  [item.id]: event.target.value,
                }))
              }
              onStorageChange={(storageLocation) => {
                runItemAction(item.id, () =>
                  onPatchInventory(item.id, { storage_location: storageLocation }),
                );
              }}
              onConfirm={() => {
                runItemAction(item.id, () =>
                  onConfirmChange(item.id, {
                    new_quantity: readQuantity(),
                    status: "available",
                    as_new_batch: false,
                  }),
                );
              }}
              onConfirmAsNewBatch={() => {
                runItemAction(item.id, () =>
                  onConfirmChange(item.id, {
                    new_quantity: readQuantity(),
                    status: "available",
                    as_new_batch: true,
                  }),
                );
              }}
              onToggleEdit={() => {
                toggleItemControls(item.id);
              }}
            />
          );
        })}
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

function InventoryCategoryRow({
  busy,
  controlsMode,
  eventQuantityDraft,
  item,
  onConfirm,
  onConfirmAsNewBatch,
  onCreateEvent,
  onDraftChange,
  onEventQuantityChange,
  onStorageChange,
  onSnoozeCheck,
  onSnoozeDraftChange,
  onToggleSnooze,
  onToggleEdit,
  quantityDraft,
  snoozeDaysDraft,
  snoozeOpen,
  source,
}: {
  busy: boolean;
  controlsMode: "collapsed" | "expanded" | "check";
  eventQuantityDraft?: string;
  item: InventoryRow;
  onConfirm: () => void;
  onConfirmAsNewBatch?: () => void;
  onCreateEvent: (eventType: FoodEventType) => void;
  onDraftChange: (event: ChangeEvent<HTMLInputElement>) => void;
  onEventQuantityChange?: (event: ChangeEvent<HTMLInputElement>) => void;
  onStorageChange: (storageLocation: "pantry" | "refrigerate" | "freeze") => void;
  onSnoozeCheck?: () => void;
  onSnoozeDraftChange?: (event: ChangeEvent<HTMLSelectElement>) => void;
  onToggleSnooze?: () => void;
  onToggleEdit?: () => void;
  quantityDraft?: string;
  snoozeDaysDraft?: string;
  snoozeOpen?: boolean;
  source?: InventoryItem;
}) {
  const { t } = useLanguage();
  const canCreateNewBatch = controlsMode === "expanded" && source?.pending_change_type === "possible_added";

  return (
    <article className="inventory-row">
      <div className={`inventory-food-image ${item.className ?? ""}`} aria-hidden="true">
        {item.image ? <img alt="" src={item.image} /> : <span>{item.glyph}</span>}
      </div>
      <div className="inventory-row-copy">
        <h2 className="inventory-food-title">{item.name}</h2>
        <p className="inventory-food-meta">{item.count}</p>
        {source ? (
          <div className="inventory-item-facts">
            <span>{formatStorageLocation(source.storage_location, t)}</span>
            <span>{formatRemainingDays(source.remaining_days, t)}</span>
            <span>{formatLastSeen(source.last_seen_at, t)}</span>
            {source.pending_change_type !== "none" ? (
              <span>{formatPendingChange(source.pending_change_type, t)}</span>
            ) : null}
            {source.message ? (
              <span className="inventory-item-warning">{source.message}</span>
            ) : null}
          </div>
        ) : null}
      </div>
      <div className="inventory-progress-track" aria-hidden="true">
        <span
          className={`inventory-progress-fill state-${item.status}`}
          style={{ width: `${item.progress}%` }}
        />
      </div>
      <span className={`inventory-state-label state-text-${item.status}`}>
        {formatState(item.status, t)}
      </span>
      <div className={`inventory-confirm-controls mode-${controlsMode}`}>
        {controlsMode === "collapsed" ? (
          <button disabled={busy} type="button" onClick={onToggleEdit}>
            {t("patchInventory")}
          </button>
        ) : null}
        {controlsMode === "check" ? (
          <div className="inventory-check-actions">
            <label className="inventory-event-quantity">
              <span className="sr-only">{t("eventQuantity")}</span>
              <input
                min={1}
                max={source?.confirmed_quantity}
                type="number"
                value={eventQuantityDraft ?? ""}
                placeholder="1"
                onChange={onEventQuantityChange}
              />
            </label>
            <button disabled={busy || !source} type="button" onClick={() => onCreateEvent("consumed")}>
              {t("ate")}
            </button>
            <button disabled={busy || !source} type="button" onClick={() => onCreateEvent("discarded")}>
              {t("tossed")}
            </button>
            <button disabled={busy || !source} type="button" onClick={onToggleSnooze}>
              {t("keepAFewDays")}
            </button>
            {snoozeOpen ? (
              <div className="inventory-snooze-controls">
                <label>
                  <span className="sr-only">{t("remindAgainIn")}</span>
                  <select
                    aria-label={t("remindAgainIn")}
                    disabled={busy}
                    value={snoozeDaysDraft ?? "3"}
                    onChange={onSnoozeDraftChange}
                  >
                    <option value="1">1 {t("dayUnit")}</option>
                    <option value="2">2 {t("daysUnit")}</option>
                    <option value="3">3 {t("daysUnit")}</option>
                    <option value="5">5 {t("daysUnit")}</option>
                    <option value="7">7 {t("daysUnit")}</option>
                  </select>
                </label>
                <button disabled={busy || !source} type="button" onClick={onSnoozeCheck}>
                  {t("confirm")}
                </button>
              </div>
            ) : null}
          </div>
        ) : null}
        {controlsMode === "expanded" ? (
          <>
        <label>
          <span className="sr-only">{t("newQuantity")}</span>
          <input
            min={0}
            type="number"
            value={quantityDraft ?? ""}
            placeholder={String(source?.pending_detected_quantity ?? source?.confirmed_quantity ?? "")}
            onChange={onDraftChange}
          />
        </label>
        <select
          aria-label={t("storageLocation")}
          disabled={busy}
          value={isStorageLocation(source?.storage_location) ? source.storage_location : "pantry"}
          onChange={(event) =>
            onStorageChange(event.target.value as "pantry" | "refrigerate" | "freeze")
          }
        >
          <option value="pantry">{t("pantry")}</option>
          <option value="refrigerate">{t("fridge")}</option>
          <option value="freeze">{t("freezer")}</option>
        </select>
        <button disabled={busy} type="button" onClick={onConfirm}>
          <Check size={17} strokeWidth={2.4} aria-hidden="true" />
          <span>{busy ? t("waitingConfirmation") : t("confirm")}</span>
        </button>
        {canCreateNewBatch ? (
          <button disabled={busy} type="button" onClick={onConfirmAsNewBatch}>
            {t("newBatch")}
          </button>
        ) : null}
        <div className="inventory-event-controls">
          <label className="inventory-event-quantity">
            <span className="sr-only">{t("eventQuantity")}</span>
            <input
              min={1}
              max={source?.confirmed_quantity}
              type="number"
              value={eventQuantityDraft ?? ""}
              placeholder="1"
              onChange={onEventQuantityChange}
            />
          </label>
          <button disabled={busy || !source} type="button" onClick={() => onCreateEvent("consumed")}>
            {t("ate")}
          </button>
          <button disabled={busy || !source} type="button" onClick={() => onCreateEvent("discarded")}>
            {t("tossed")}
          </button>
          <button disabled={busy || !source} type="button" onClick={() => onCreateEvent("purchased")}>
            {t("bought")}
          </button>
        </div>
          </>
        ) : null}
      </div>
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

function formatState(
  status: InventoryRow["status"],
  t: ReturnType<typeof useLanguage>["t"],
) {
  if (status === "fresh") return t("fresh");
  if (status === "expiring") return t("eatSoon");
  if (status === "notRecommended") return t("notRecommendedDirect");
  return t("check");
}

function toInventoryRow(
  item: InventoryItem,
  t: ReturnType<typeof useLanguage>["t"],
): InventoryRow {
  const food = item.food.model_label;
  const isKnownFruit = isSupportedFoodLabel(food);
  const quantityLabel = `${item.confirmed_quantity} ${formatUnit(item.unit, t)}`;

  return {
    id: item.id,
    name: getFoodDisplayName(food, item.food.display_name),
    count: quantityLabel,
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
  if (item.storage_state === "not_recommended") {
    return "notRecommended";
  }
  if (item.storage_state === "eat_soon") {
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

function formatPendingChange(
  change: PendingChangeType,
  t: ReturnType<typeof useLanguage>["t"],
) {
  if (change === "new_quantity") return t("newQuantity");
  if (change === "possible_added") return t("possibleAdded");
  if (change === "possible_consumed") return t("possibleUsed");
  return t("confirmedQuantity");
}

function needsInventoryConfirmation(item: InventoryItem): boolean {
  return (
    item.status === "pending_confirm" ||
    item.pending_change_type !== "none" ||
    item.storage_state === "check_required" ||
    item.storage_state === "not_recommended"
  );
}

function shouldShowInventoryItem(item: InventoryItem): boolean {
  if (item.status === "consumed" || item.status === "discarded") {
    return false;
  }
  return item.confirmed_quantity > 0;
}

function applyLocalSnooze(item: InventoryItem, snoozeDays: number | undefined): InventoryItem {
  if (snoozeDays === undefined) {
    return item;
  }

  return {
    ...item,
    remaining_days: snoozeDays,
    storage_state: "eat_soon",
    status: "available",
    pending_change_type: "none",
    pending_detected_quantity: null,
    message: null,
  };
}

function formatUnit(unit: string | null | undefined, t: ReturnType<typeof useLanguage>["t"]) {
  if (!unit || unit === "items") return t("items");
  if (unit === "piece" || unit === "pieces") return t("pieces");
  return unit;
}

function formatLastSeen(
  value: string | null | undefined,
  t: ReturnType<typeof useLanguage>["t"],
): string {
  if (!value) {
    return t("noRecentScan");
  }

  return `${t("seen")} ${formatBeijingDateTime(value).slice(0, 16)}`;
}

function formatRemainingDays(
  value: number | null,
  t: ReturnType<typeof useLanguage>["t"],
): string {
  if (value == null) {
    return t("checkTiming");
  }

  if (value < 0) {
    return `${Math.abs(value)} ${t("pastReferenceDays")}`;
  }

  if (value === 0) {
    return t("referenceDateToday");
  }

  return `${value} ${t(value === 1 ? "dayLeft" : "daysLeft")}`;
}

function formatStorageLocation(
  value: InventoryItem["storage_location"],
  t: ReturnType<typeof useLanguage>["t"],
): string {
  if (value === "pantry") return t("pantry");
  if (value === "refrigerate") return t("fridge");
  if (value === "freeze") return t("freezer");
  return value || t("storageUnset");
}

function isStorageLocation(
  value: InventoryItem["storage_location"] | null | undefined,
): value is "pantry" | "refrigerate" | "freeze" {
  return value === "pantry" || value === "refrigerate" || value === "freeze";
}
