export type SupportedFoodLabel = "apple" | "banana" | "litchi" | "pear";

export type StorageLocation = "pantry" | "refrigerate" | "freeze";

export type InventoryStatus =
  | "pending_confirm"
  | "available"
  | "consumed"
  | "discarded"
  | "unknown";

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

export type EventType = "consumed" | "discarded" | "purchased";

export type AdviceActionType =
  | "eat_first"
  | "check_food"
  | "avoid_duplicate_purchase"
  | "portion_control"
  | "variety"
  | "general";

export type AdviceConfidence = "low" | "medium" | "high";

export interface EvidenceSource {
  type: string;
  title: string;
  source: string;
  summary: string;
  url?: string | null;
}

export interface FoodSummary {
  id: number;
  model_label: string;
  display_name: string;
}

export interface InventoryItem {
  id: number;
  evidence_id: string;
  user_id: number;
  camera_id: string | null;
  food: FoodSummary;
  detected_quantity: number;
  confirmed_quantity: number;
  unit: string;
  storage_location: StorageLocation | string;
  first_seen_at: string;
  created_at?: string | null;
  last_seen_at: string;
  days_stored: number | null;
  safe_days: number | null;
  remaining_days: number | null;
  storage_state: StorageState | string;
  eat_priority_rank: number | null;
  status: InventoryStatus | string;
  source_event_id: number | null;
  pending_change_type: PendingChangeType | string;
  pending_detected_quantity: number | null;
  message?: string | null;
}

export interface InventoryPatch {
  confirmed_quantity?: number;
  detected_quantity?: number;
  unit?: string;
  storage_location?: StorageLocation;
  status?: InventoryStatus;
}

export interface ConfirmChangeRequest {
  new_quantity?: number | null;
  status?: InventoryStatus | null;
  as_new_batch?: boolean;
}

export interface AdviceItem {
  title: string;
  content: string;
  action_type: AdviceActionType;
  related_foods: string[];
  basis: string[];
  evidence_ids: string[];
  evidence_sources?: EvidenceSource[];
  confidence: AdviceConfidence;
}

export interface TodayAdviceItem {
  food: string;
  display_name: string;
  storage_state: StorageState | string;
  days_stored: number | null;
  safe_days: number | null;
  remaining_days: number | null;
  eat_priority_rank?: number | null;
  basis: string[];
  evidence_ids: string[];
}

export interface TodayAdviceResponse {
  today_priority: TodayAdviceItem[];
  check_required: TodayAdviceItem[];
}

export interface ShoppingAdviceResponse {
  recommendations: AdviceItem[];
}

export interface LlmAdvicePayload {
  summary: string;
  recommendations: AdviceItem[];
}

export interface LlmGenerateRequest {
  question?: string | null;
  enable_thinking?: boolean | null;
  search_query?: string | null;
}

export interface LlmAdviceResponse {
  accepted: boolean;
  errors: string[];
  advice: LlmAdvicePayload;
  record_id?: number | null;
}

export interface EvidenceSearchResponse {
  query: string;
  results: Array<Record<string, unknown>>;
}

export interface Profile {
  id: number;
  goal: string;
  diet_preference: string;
  cooking_condition: string;
  avoid_foods: string[];
  allergies_optional: string | null;
  health_notes_optional: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProfilePatch {
  goal?: string;
  diet_preference?: string;
  cooking_condition?: string;
  avoid_foods?: string[] | null;
  allergies_optional?: string | null;
  health_notes_optional?: string | null;
}

export interface UserFoodEventCreate {
  food_id: SupportedFoodLabel | string;
  event_type: EventType;
  quantity?: number;
  inventory_id?: number | null;
  occurred_at?: string | null;
  metadata?: Record<string, unknown>;
}

export interface UserFoodEvent {
  id: number;
  evidence_id: string;
  user_id: number;
  food: string;
  event_type: EventType | string;
  quantity: number;
  occurred_at: string;
  metadata: Record<string, unknown>;
}

export interface UserFoodHabit {
  id: number;
  evidence_id: string;
  user_id: number;
  food: string;
  habit_type: string;
  score: number;
  evidence: Record<string, unknown>;
  updated_at: string;
}
