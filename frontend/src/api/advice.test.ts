import { afterEach, describe, expect, it, vi } from "vitest";
import type {
  LlmAdviceResponse,
  ShoppingAdviceResponse,
  TodayAdviceResponse,
} from "./types";
import {
  fetchShoppingAdvice,
  fetchTodayAdvice,
  generateLlmAdvice,
  searchAdviceEvidence,
} from "./advice";

function jsonResponse(payload: unknown): Response {
  return {
    ok: true,
    status: 200,
    headers: new Headers({ "content-type": "application/json" }),
    json: vi.fn().mockResolvedValue(payload),
    text: vi.fn().mockResolvedValue(""),
  } as unknown as Response;
}

describe("advice api", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetches today advice and filters unsupported foods", async () => {
    const payload: TodayAdviceResponse = {
      today_priority: [
        {
          food: "apple",
          display_name: "Apple",
          storage_state: "fresh",
          days_stored: 1,
          safe_days: 5,
          remaining_days: 4,
          basis: [],
          evidence_ids: ["evidence-1"],
        },
        {
          food: "mango",
          display_name: "Mango",
          storage_state: "fresh",
          days_stored: 1,
          safe_days: 5,
          remaining_days: 4,
          basis: [],
          evidence_ids: ["evidence-2"],
        },
      ],
      check_required: [
        {
          food: "pear",
          display_name: "Pear",
          storage_state: "check_required",
          days_stored: 3,
          safe_days: 3,
          remaining_days: 0,
          basis: [],
          evidence_ids: ["evidence-3"],
        },
      ],
    };
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(payload));
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchTodayAdvice()).resolves.toMatchObject({
      today_priority: [{ food: "apple" }],
      check_required: [{ food: "pear" }],
    });
    expect(fetchMock.mock.calls[0][0]).toBe("http://eai.744477.xyz/api/advice/today");
  });

  it("fetches shopping advice and drops non-general unsupported recommendations", async () => {
    const payload: ShoppingAdviceResponse = {
      recommendations: [
        {
          title: "Buy less banana",
          content: "You already have bananas.",
          action_type: "avoid_duplicate_purchase",
          related_foods: ["banana", "mango"],
          basis: [],
          evidence_ids: [],
          confidence: "medium",
        },
        {
          title: "Unsupported",
          content: "Only mango.",
          action_type: "eat_first",
          related_foods: ["mango"],
          basis: [],
          evidence_ids: [],
          confidence: "low",
        },
      ],
    };
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(payload));
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchShoppingAdvice()).resolves.toEqual({
      recommendations: [{ ...payload.recommendations[0], related_foods: ["banana"] }],
    });
    expect(fetchMock.mock.calls[0][0]).toBe("http://eai.744477.xyz/api/advice/shopping");
  });

  it("posts LLM request, filters recommendations, and keeps accepted=false", async () => {
    const payload: LlmAdviceResponse = {
      accepted: false,
      errors: ["not enough evidence"],
      record_id: null,
      advice: {
        summary: "Fallback advice",
        recommendations: [
          {
            title: "Check litchi",
            content: "Inspect before eating.",
            action_type: "check_food",
            related_foods: ["litchi", "mango"],
            basis: ["storage state"],
            evidence_ids: ["evidence-1"],
            confidence: "high",
          },
          {
            title: "Only mango",
            content: "Unsupported fruit.",
            action_type: "eat_first",
            related_foods: ["mango"],
            basis: [],
            evidence_ids: [],
            confidence: "low",
          },
        ],
      },
    };
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(payload));
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      generateLlmAdvice({ question: "What should I eat?", enable_thinking: false }),
    ).resolves.toEqual({
      ...payload,
      advice: {
        ...payload.advice,
        recommendations: [
          { ...payload.advice.recommendations[0], related_foods: ["litchi"] },
        ],
      },
    });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://eai.744477.xyz/api/advice/llm/generate");
    expect(init.method).toBe("POST");
    expect(init.body).toBe(
      JSON.stringify({ question: "What should I eat?", enable_thinking: false }),
    );
  });

  it("sends evidence search query params", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ query: "ripe pear", results: [{ id: "evidence-1" }] }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(searchAdviceEvidence("ripe pear")).resolves.toEqual({
      query: "ripe pear",
      results: [{ id: "evidence-1" }],
    });
    expect(fetchMock.mock.calls[0][0]).toBe(
      "http://eai.744477.xyz/api/advice/evidence-search?query=ripe+pear",
    );
  });
});
