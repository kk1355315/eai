import { describe, expect, it } from "vitest";
import {
  FOOD_ACCENT_COLORS,
  FOOD_DISPLAY_NAMES,
  FOOD_SOFT_COLORS,
  SUPPORTED_FOODS,
  filterSupportedFoodLabels,
  getFoodDisplayName,
  isSupportedFoodLabel,
  toSupportedFoodLabel,
} from "./foods";

describe("foods", () => {
  it("defines the MVP four fruit labels and metadata", () => {
    expect(SUPPORTED_FOODS).toEqual(["apple", "banana", "litchi", "pear"]);

    for (const food of SUPPORTED_FOODS) {
      expect(FOOD_DISPLAY_NAMES[food]).toBeTruthy();
      expect(FOOD_ACCENT_COLORS[food]).toMatch(/^#/);
      expect(FOOD_SOFT_COLORS[food]).toMatch(/^#/);
    }
  });

  it("recognizes and filters supported labels only", () => {
    expect(isSupportedFoodLabel("apple")).toBe(true);
    expect(isSupportedFoodLabel("mango")).toBe(false);
    expect(toSupportedFoodLabel("pear")).toBe("pear");
    expect(toSupportedFoodLabel("grape")).toBeNull();

    expect(filterSupportedFoodLabels(["apple", "mango", "banana", "pear", "durian"])).toEqual([
      "apple",
      "banana",
      "pear",
    ]);
  });

  it("returns display names with fallback for unsupported labels", () => {
    expect(getFoodDisplayName("litchi")).toBe("荔枝");
    expect(getFoodDisplayName("dragonfruit", "火龙果")).toBe("火龙果");
    expect(getFoodDisplayName("dragonfruit")).toBe("dragonfruit");
  });
});
