import type {
  AdviceActionType,
  AdviceConfidence,
  InventoryStatus,
  PendingChangeType,
  StorageLocation,
  StorageState,
} from "../api/types";

export interface StatusMeta {
  label: string;
  color: string;
  background: string;
  tone: "good" | "warn" | "danger" | "neutral";
}

export const STORAGE_STATE_META: Record<Exclude<StorageState, null>, StatusMeta> = {
  fresh: {
    label: "新鲜",
    color: "#137333",
    background: "#e7f6ec",
    tone: "good",
  },
  eat_soon: {
    label: "尽快吃",
    color: "#b25b00",
    background: "#fff3dd",
    tone: "warn",
  },
  check_required: {
    label: "需检查",
    color: "#b42318",
    background: "#feeceb",
    tone: "danger",
  },
  not_recommended: {
    label: "不推荐直接食用",
    color: "#6f4248",
    background: "#f5e9eb",
    tone: "danger",
  },
};

export const INVENTORY_STATUS_META: Record<InventoryStatus, StatusMeta> = {
  pending_confirm: {
    label: "待确认",
    color: "#8a5a00",
    background: "#fff5d8",
    tone: "warn",
  },
  available: {
    label: "在库",
    color: "#137333",
    background: "#e7f6ec",
    tone: "good",
  },
  consumed: {
    label: "已食用",
    color: "#4b5563",
    background: "#eef2f7",
    tone: "neutral",
  },
  discarded: {
    label: "已丢弃",
    color: "#6f4248",
    background: "#f5e9eb",
    tone: "danger",
  },
  unknown: {
    label: "未知",
    color: "#4b5563",
    background: "#eef2f7",
    tone: "neutral",
  },
};

export const PENDING_CHANGE_META: Record<PendingChangeType, StatusMeta> = {
  none: {
    label: "无变化",
    color: "#4b5563",
    background: "#eef2f7",
    tone: "neutral",
  },
  new_quantity: {
    label: "新识别数量",
    color: "#1d4ed8",
    background: "#e5efff",
    tone: "warn",
  },
  possible_added: {
    label: "可能新增",
    color: "#8a5a00",
    background: "#fff5d8",
    tone: "warn",
  },
  possible_consumed: {
    label: "可能已食用",
    color: "#8a5a00",
    background: "#fff5d8",
    tone: "warn",
  },
};

export const STORAGE_LOCATION_LABELS: Record<StorageLocation, string> = {
  pantry: "常温",
  refrigerate: "冷藏",
  freeze: "冷冻",
};

export const ACTION_TYPE_LABELS: Record<AdviceActionType, string> = {
  eat_first: "优先吃",
  check_food: "检查提示",
  avoid_duplicate_purchase: "购物提醒",
  portion_control: "份量建议",
  variety: "多样搭配",
  general: "一般建议",
};

export const CONFIDENCE_LABELS: Record<AdviceConfidence, string> = {
  low: "低",
  medium: "中",
  high: "高",
};

const FALLBACK_META: StatusMeta = {
  label: "未知",
  color: "#4b5563",
  background: "#eef2f7",
  tone: "neutral",
};

export function getStorageStateMeta(state: StorageState | string): StatusMeta {
  if (state && state in STORAGE_STATE_META) {
    return STORAGE_STATE_META[state as Exclude<StorageState, null>];
  }
  return FALLBACK_META;
}

export function getInventoryStatusMeta(status: InventoryStatus | string): StatusMeta {
  if (status in INVENTORY_STATUS_META) {
    return INVENTORY_STATUS_META[status as InventoryStatus];
  }
  return FALLBACK_META;
}

export function getPendingChangeMeta(change: PendingChangeType | string): StatusMeta {
  if (change in PENDING_CHANGE_META) {
    return PENDING_CHANGE_META[change as PendingChangeType];
  }
  return FALLBACK_META;
}

export function getActionTypeLabel(actionType: AdviceActionType | string): string {
  if (actionType in ACTION_TYPE_LABELS) {
    return ACTION_TYPE_LABELS[actionType as AdviceActionType];
  }
  return "建议";
}

export function getStorageLocationLabel(location: StorageLocation | string): string {
  if (location in STORAGE_LOCATION_LABELS) {
    return STORAGE_LOCATION_LABELS[location as StorageLocation];
  }
  return location;
}

export function getRemainingDaysText(remainingDays: number | null): string {
  if (remainingDays === null) {
    return "暂无保存期限";
  }
  if (remainingDays < 0) {
    return `超过参考期 ${Math.abs(remainingDays)} 天`;
  }
  if (remainingDays === 0) {
    return "今天到参考期限";
  }
  return `还剩 ${remainingDays} 天`;
}
