import { describe, expect, it } from "vitest";
import {
  ACTION_TYPE_LABELS,
  CONFIDENCE_LABELS,
  getInventoryStatusMeta,
  getPendingChangeMeta,
  getRemainingDaysText,
  getStorageLocationLabel,
  getStorageStateMeta,
} from "./status";

describe("status", () => {
  it("returns known status metadata and neutral fallback metadata", () => {
    expect(getStorageStateMeta("fresh")).toMatchObject({
      label: "新鲜",
      tone: "good",
    });
    expect(getStorageStateMeta("expired")).toMatchObject({
      label: "未知",
      tone: "neutral",
    });
    expect(getStorageStateMeta(null)).toMatchObject({
      label: "未知",
      tone: "neutral",
    });

    expect(getInventoryStatusMeta("pending_confirm")).toMatchObject({
      label: "待确认",
      tone: "warn",
    });
    expect(getInventoryStatusMeta("moved")).toMatchObject({
      label: "未知",
      tone: "neutral",
    });

    expect(getPendingChangeMeta("possible_consumed")).toMatchObject({
      label: "可能已食用",
      tone: "warn",
    });
    expect(getPendingChangeMeta("renamed")).toMatchObject({
      label: "未知",
      tone: "neutral",
    });
  });

  it("returns labels for storage location, action, and confidence", () => {
    expect(getStorageLocationLabel("pantry")).toBe("常温");
    expect(getStorageLocationLabel("balcony")).toBe("balcony");
    expect(ACTION_TYPE_LABELS.eat_first).toBe("优先吃");
    expect(CONFIDENCE_LABELS.high).toBe("高");
  });

  it("formats remaining days text", () => {
    expect(getRemainingDaysText(null)).toBe("暂无保存期限");
    expect(getRemainingDaysText(-2)).toBe("超过参考期 2 天");
    expect(getRemainingDaysText(0)).toBe("今天到参考期限");
    expect(getRemainingDaysText(3)).toBe("还剩 3 天");
  });
});
