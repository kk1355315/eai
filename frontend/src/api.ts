export type StorageState =
  | "fresh"
  | "eat_soon"
  | "check_required"
  | "not_recommended"
  | string
  | null;

export type InventoryItem = {
  id: number;
  food: {
    model_label: string;
    display_name: string;
  };
  confirmed_quantity: number;
  unit: string;
  days_stored: number | null;
  remaining_days: number | null;
  storage_state: StorageState;
  status: string;
  message: string | null;
};

export type TodayAdvice = {
  today_priority: Array<Record<string, unknown>>;
  check_required: Array<Record<string, unknown>>;
};

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export function getInventory() {
  return request<InventoryItem[]>("/inventory");
}

export function getTodayAdvice() {
  return request<TodayAdvice>("/advice/today");
}
