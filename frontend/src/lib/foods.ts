import type { SupportedFoodLabel } from "../api/types";

export const SUPPORTED_FOODS = ["apple", "banana", "litchi", "pear"] as const;

export const FOOD_DISPLAY_NAMES: Record<SupportedFoodLabel, string> = {
  apple: "苹果",
  banana: "香蕉",
  litchi: "荔枝",
  pear: "梨",
};

export const FOOD_ACCENT_COLORS: Record<SupportedFoodLabel, string> = {
  apple: "#ff6b6b",
  banana: "#f6c453",
  litchi: "#f06a9b",
  pear: "#78b159",
};

export const FOOD_SOFT_COLORS: Record<SupportedFoodLabel, string> = {
  apple: "#fff0f0",
  banana: "#fff7dc",
  litchi: "#fff0f6",
  pear: "#edf8e7",
};

export function isSupportedFoodLabel(value: string): value is SupportedFoodLabel {
  return (SUPPORTED_FOODS as readonly string[]).includes(value);
}

export function toSupportedFoodLabel(value: string): SupportedFoodLabel | null {
  return isSupportedFoodLabel(value) ? value : null;
}

export function filterSupportedFoodLabels(values: string[]): SupportedFoodLabel[] {
  return values.filter(isSupportedFoodLabel);
}

export function getFoodDisplayName(food: string, fallback?: string): string {
  return isSupportedFoodLabel(food) ? FOOD_DISPLAY_NAMES[food] : fallback ?? food;
}
