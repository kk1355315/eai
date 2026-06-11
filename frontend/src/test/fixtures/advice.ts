import type { AdviceItem, LlmAdviceResponse, TodayAdviceResponse } from "../../api/types";

export const todayAdviceFixture: TodayAdviceResponse = {
  today_priority: [
    {
      food: "apple",
      display_name: "Apple",
      storage_state: "eat_soon",
      days_stored: 2,
      safe_days: 3,
      remaining_days: 1,
      eat_priority_rank: 1,
      basis: ["Apple is close to its reference storage window."],
      evidence_ids: ["evidence-apple"],
    },
    {
      food: "banana",
      display_name: "Banana",
      storage_state: "fresh",
      days_stored: 1,
      safe_days: 2,
      remaining_days: 1,
      eat_priority_rank: 2,
      basis: ["Banana should be used soon."],
      evidence_ids: ["evidence-banana"],
    },
    {
      food: "pear",
      display_name: "Pear",
      storage_state: "fresh",
      days_stored: 1,
      safe_days: 5,
      remaining_days: 4,
      eat_priority_rank: 3,
      basis: ["Pear is available in confirmed inventory."],
      evidence_ids: ["evidence-pear"],
    },
  ],
  check_required: [
    {
      food: "litchi",
      display_name: "Litchi",
      storage_state: "check_required",
      days_stored: 3,
      safe_days: 3,
      remaining_days: 0,
      basis: ["Litchi has reached its reference storage window."],
      evidence_ids: ["evidence-litchi"],
    },
    {
      food: "strawberry",
      display_name: "Strawberry",
      storage_state: "check_required",
      days_stored: 4,
      safe_days: 2,
      remaining_days: -2,
      basis: ["Non-MVP ingredient sample for filter assertions."],
      evidence_ids: ["evidence-strawberry"],
    },
  ],
};

export const shoppingAdviceFixture = {
  recommendations: [
    {
      title: "Do not duplicate fruit purchases",
      content: "Use the confirmed apple, banana, litchi, and pear inventory before buying more.",
      action_type: "avoid_duplicate_purchase",
      related_foods: ["apple", "banana", "litchi", "pear"],
      basis: ["All four MVP fruits are already present."],
      evidence_ids: ["evidence-apple", "evidence-banana", "evidence-litchi", "evidence-pear"],
      confidence: "high",
    },
    {
      title: "Ignore non-MVP shopping data",
      content: "Strawberry and milk are fixture-only non-MVP ingredients.",
      action_type: "general",
      related_foods: ["strawberry", "milk"],
      basis: ["Non-MVP ingredient sample for filter assertions."],
      evidence_ids: ["evidence-strawberry", "evidence-milk"],
      confidence: "low",
    },
  ] satisfies AdviceItem[],
};

export const llmAdviceFixture: LlmAdviceResponse = {
  accepted: true,
  errors: [],
  record_id: 1,
  advice: {
    summary: "Prioritize MVP fruit inventory and ignore non-MVP ingredients in UI assertions.",
    recommendations: shoppingAdviceFixture.recommendations,
  },
};
