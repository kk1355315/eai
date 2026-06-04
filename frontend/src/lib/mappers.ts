import type {
  AdviceItem,
  InventoryItem,
  PendingChangeType,
  StorageState,
  SupportedFoodLabel,
  TodayAdviceItem,
  TodayAdviceResponse,
} from "../api/types";
import { getFoodDisplayName, isSupportedFoodLabel } from "./foods";
import {
  getActionTypeLabel,
  getInventoryStatusMeta,
  getPendingChangeMeta,
  getRemainingDaysText,
  getStorageLocationLabel,
  getStorageStateMeta,
  type StatusMeta,
} from "./status";

export interface InventoryViewModel {
  id: number;
  evidenceId: string;
  food: SupportedFoodLabel;
  displayName: string;
  quantity: number;
  detectedQuantity: number;
  unit: string;
  storageLocationLabel: string;
  daysStored: number | null;
  safeDays: number | null;
  remainingDays: number | null;
  remainingDaysText: string;
  storageState: StorageState | string;
  storageMeta: StatusMeta;
  statusMeta: StatusMeta;
  pendingChangeType: PendingChangeType | string;
  pendingChangeMeta: StatusMeta;
  pendingDetectedQuantity: number | null;
  eatPriorityRank: number | null;
  needsConfirmation: boolean;
  message: string | null;
}

export interface TodayAdviceViewModel {
  food: SupportedFoodLabel;
  displayName: string;
  storageState: StorageState | string;
  storageMeta: StatusMeta;
  daysStored: number | null;
  safeDays: number | null;
  remainingDays: number | null;
  remainingDaysText: string;
  eatPriorityRank: number | null;
  basis: string[];
  evidenceIds: string[];
}

export interface HomeFruitViewModel {
  id: string | number;
  modelLabel: SupportedFoodLabel;
  displayName: string;
  quantity?: number | null;
  unit?: string | null;
  remainingDays?: number | null;
  storageState: StorageState;
  message?: string | null;
}

export interface AdviceViewModel extends AdviceItem {
  relatedSupportedFoods: SupportedFoodLabel[];
  primaryFood: SupportedFoodLabel | null;
  actionLabel: string;
}

export interface HomeFruitData {
  recommended: HomeFruitViewModel | undefined;
  priority: HomeFruitViewModel[];
  needCheck: HomeFruitViewModel[];
  hasAnyFruit: boolean;
}

const RECOMMENDABLE_STORAGE_STATES: readonly StorageState[] = [
  "fresh",
  "eat_soon",
];
const NEED_CHECK_STORAGE_STATES: readonly StorageState[] = [
  "check_required",
  "not_recommended",
];

export function filterSupportedInventory(items: InventoryItem[]): InventoryItem[] {
  return items.filter((item) => isSupportedFoodLabel(item.food.model_label));
}

export function mapInventoryItem(item: InventoryItem): InventoryViewModel | null {
  const food = item.food.model_label;
  if (!isSupportedFoodLabel(food)) {
    return null;
  }

  return {
    id: item.id,
    evidenceId: item.evidence_id,
    food,
    displayName: getFoodDisplayName(food, item.food.display_name),
    quantity: item.confirmed_quantity,
    detectedQuantity: item.detected_quantity,
    unit: item.unit,
    storageLocationLabel: getStorageLocationLabel(item.storage_location),
    daysStored: item.days_stored,
    safeDays: item.safe_days,
    remainingDays: item.remaining_days,
    remainingDaysText: getRemainingDaysText(item.remaining_days),
    storageState: item.storage_state,
    storageMeta: getStorageStateMeta(item.storage_state),
    statusMeta: getInventoryStatusMeta(item.status),
    pendingChangeType: item.pending_change_type,
    pendingChangeMeta: getPendingChangeMeta(item.pending_change_type),
    pendingDetectedQuantity: item.pending_detected_quantity,
    eatPriorityRank: item.eat_priority_rank,
    needsConfirmation:
      item.status === "pending_confirm" || item.pending_change_type !== "none",
    message: item.message,
  };
}

export function mapInventory(items: InventoryItem[]): InventoryViewModel[] {
  return items
    .map(mapInventoryItem)
    .filter((item): item is InventoryViewModel => item !== null);
}

export function isRecommendableInventoryItem(item: InventoryItem): boolean {
  return (
    isSupportedFoodLabel(item.food.model_label) &&
    item.status === "available" &&
    item.confirmed_quantity > 0 &&
    isRecommendableStorageState(item.storage_state)
  );
}

export function isNeedsCheckInventoryItem(item: InventoryItem): boolean {
  return (
    isSupportedFoodLabel(item.food.model_label) &&
    item.status === "available" &&
    item.confirmed_quantity > 0 &&
    isNeedsCheckStorageState(item.storage_state)
  );
}

export function countPendingInventoryChanges(items: InventoryItem[]): number {
  return filterSupportedInventory(items).filter(
    (item) =>
      item.status === "pending_confirm" || item.pending_change_type !== "none",
  ).length;
}

export function buildHomeFruitData(
  todayAdvice: TodayAdviceResponse | null | undefined,
  inventoryItems: InventoryItem[] | null | undefined,
): HomeFruitData {
  const advice = todayAdvice ?? { today_priority: [], check_required: [] };
  const inventory = inventoryItems ?? [];
  const { todayPriority, checkRequired } = mapTodayAdvice(advice);
  const todayPriorityFruits = todayPriority
    .map(mapTodayAdviceHomeFruit)
    .filter(canRecommendHomeFruit);
  const needCheckFromAdvice = checkRequired.map((item) => ({
    ...mapTodayAdviceHomeFruit(item),
    storageState: normalizeStorageState(item.storageState) ?? "check_required",
  }));
  const inventoryFruits = inventory
    .map(mapInventoryHomeFruit)
    .filter((item): item is HomeFruitViewModel => item !== null);
  const fallbackPriority = inventory
    .filter(isRecommendableInventoryItem)
    .map(mapInventoryHomeFruit)
    .filter((item): item is HomeFruitViewModel => item !== null)
    .sort((a, b) => (a.remainingDays ?? 99) - (b.remainingDays ?? 99));
  const priority = todayPriorityFruits.length
    ? todayPriorityFruits
    : fallbackPriority;
  const needCheck = needCheckFromAdvice.length
    ? needCheckFromAdvice
    : inventory
        .filter(isNeedsCheckInventoryItem)
        .map(mapInventoryHomeFruit)
        .filter((item): item is HomeFruitViewModel => item !== null);

  return {
    recommended: priority[0],
    priority: priority.slice(0, 4),
    needCheck: needCheck.slice(0, 4),
    hasAnyFruit:
      inventoryFruits.length > 0 ||
      todayPriorityFruits.length > 0 ||
      needCheckFromAdvice.length > 0,
  };
}

export function filterSupportedTodayAdvice(
  advice: TodayAdviceResponse,
): TodayAdviceResponse {
  return {
    today_priority: advice.today_priority.filter(isSupportedTodayItem),
    check_required: advice.check_required.filter(isSupportedTodayItem),
  };
}

export function mapTodayAdviceItem(
  item: TodayAdviceItem,
): TodayAdviceViewModel | null {
  if (!isSupportedFoodLabel(item.food)) {
    return null;
  }

  return {
    food: item.food,
    displayName: getFoodDisplayName(item.food, item.display_name),
    storageState: item.storage_state,
    storageMeta: getStorageStateMeta(item.storage_state),
    daysStored: item.days_stored,
    safeDays: item.safe_days,
    remainingDays: item.remaining_days,
    remainingDaysText: getRemainingDaysText(item.remaining_days),
    eatPriorityRank: item.eat_priority_rank ?? null,
    basis: item.basis,
    evidenceIds: item.evidence_ids,
  };
}

export function mapTodayAdvice(advice: TodayAdviceResponse): {
  todayPriority: TodayAdviceViewModel[];
  checkRequired: TodayAdviceViewModel[];
} {
  return {
    todayPriority: advice.today_priority
      .map(mapTodayAdviceItem)
      .filter((item): item is TodayAdviceViewModel => item !== null),
    checkRequired: advice.check_required
      .map(mapTodayAdviceItem)
      .filter((item): item is TodayAdviceViewModel => item !== null),
  };
}

export function filterSupportedAdviceItems(items: AdviceItem[]): AdviceItem[] {
  return items
    .map((item) => ({
      ...item,
      related_foods: item.related_foods.filter(isSupportedFoodLabel),
    }))
    .filter(
      (item) => item.related_foods.length > 0 || item.action_type === "general",
    );
}

export function mapAdviceItem(item: AdviceItem): AdviceViewModel {
  const relatedSupportedFoods = item.related_foods.filter(isSupportedFoodLabel);
  return {
    ...item,
    relatedSupportedFoods,
    primaryFood: relatedSupportedFoods[0] ?? null,
    actionLabel: getActionTypeLabel(item.action_type),
  };
}

export function mapAdviceItems(items: AdviceItem[]): AdviceViewModel[] {
  return filterSupportedAdviceItems(items).map(mapAdviceItem);
}

export function mapAdviceResponseLike(data: unknown): AdviceViewModel[] {
  const record = asRecord(data);
  const items = asArray(
    record.items ?? record.advice ?? record.recommendations ?? data,
  )
    .map(toAdviceItem)
    .filter((item): item is AdviceItem => item !== null);
  return mapAdviceItems(items);
}

function isSupportedTodayItem(item: TodayAdviceItem): boolean {
  return isSupportedFoodLabel(item.food);
}

function toAdviceItem(raw: unknown): AdviceItem | null {
  const item = asRecord(raw);
  const title = (item.title ?? item.name ?? null) as string | null;
  const content = (item.content ?? item.message ?? item.body ?? null) as string | null;
  const basis = item.basis ?? item.reason ?? null;

  if (!title && !content && !basis) {
    return null;
  }

  return {
    title: title ?? "",
    content: content ?? "",
    action_type: (item.action_type ??
      item.actionType ??
      "general") as AdviceItem["action_type"],
    related_foods: asArray(item.related_foods ?? item.relatedFoods).map((food) =>
      String(food).toLowerCase(),
    ),
    basis: Array.isArray(basis)
      ? basis.map(String)
      : basis
        ? [String(basis)]
        : [],
    evidence_ids: asArray(item.evidence_ids ?? item.evidenceIds).map(String),
    confidence: (item.confidence ?? "medium") as AdviceItem["confidence"],
  };
}

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null
    ? (value as Record<string, unknown>)
    : {};
}

function asArray(value: unknown): unknown[] {
  if (Array.isArray(value)) {
    return value;
  }
  if (
    value &&
    typeof value === "object" &&
    Array.isArray((value as { items?: unknown[] }).items)
  ) {
    return (value as { items: unknown[] }).items;
  }
  return [];
}

function mapInventoryHomeFruit(item: InventoryItem): HomeFruitViewModel | null {
  const food = item.food.model_label;
  if (!isSupportedFoodLabel(food)) {
    return null;
  }

  return {
    id: item.id,
    modelLabel: food,
    displayName: getFoodDisplayName(food, item.food.display_name),
    quantity: item.confirmed_quantity,
    unit: item.unit,
    remainingDays: item.remaining_days,
    storageState: normalizeStorageState(item.storage_state),
    message: item.message,
  };
}

function mapTodayAdviceHomeFruit(
  item: TodayAdviceViewModel,
): HomeFruitViewModel {
  return {
    id: item.evidenceIds[0] ?? `${item.food}-${item.eatPriorityRank ?? "advice"}`,
    modelLabel: item.food,
    displayName: item.displayName,
    remainingDays: item.remainingDays,
    storageState: normalizeStorageState(item.storageState),
    message: item.basis[0] ?? null,
  };
}

function canRecommendHomeFruit(item: HomeFruitViewModel): boolean {
  return item.storageState === null || isRecommendableStorageState(item.storageState);
}

function isRecommendableStorageState(
  state: StorageState | string,
): state is "fresh" | "eat_soon" {
  return RECOMMENDABLE_STORAGE_STATES.includes(normalizeStorageState(state));
}

function isNeedsCheckStorageState(
  state: StorageState | string,
): state is "check_required" | "not_recommended" {
  return NEED_CHECK_STORAGE_STATES.includes(normalizeStorageState(state));
}

function normalizeStorageState(state: StorageState | string): StorageState {
  if (
    state === "fresh" ||
    state === "eat_soon" ||
    state === "check_required" ||
    state === "not_recommended"
  ) {
    return state;
  }
  return null;
}
