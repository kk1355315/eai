import { afterEach, describe, expect, it, vi } from "vitest";
import { createUserFoodEvent, fetchHabits } from "./userEvents";

function jsonResponse(payload: unknown): Response {
  return {
    ok: true,
    status: 200,
    headers: new Headers({ "content-type": "application/json" }),
    json: vi.fn().mockResolvedValue(payload),
    text: vi.fn().mockResolvedValue(""),
  } as unknown as Response;
}

describe("user events api", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("creates user food event with default quantity and metadata", async () => {
    const event = {
      id: 1,
      evidence_id: "event-1",
      user_id: 1,
      food: "apple",
      event_type: "consumed",
      quantity: 1,
      occurred_at: "2026-06-03T00:00:00Z",
      metadata: {},
    };
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(event));
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      createUserFoodEvent({
        food_id: "apple",
        event_type: "consumed",
      }),
    ).resolves.toEqual(event);

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://eai.744477.xyz/api/user-food-events");
    expect(init.method).toBe("POST");
    expect(init.body).toBe(
      JSON.stringify({
        quantity: 1,
        metadata: {},
        food_id: "apple",
        event_type: "consumed",
      }),
    );
  });

  it("lets explicit quantity and metadata override defaults", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        id: 2,
        evidence_id: "event-2",
        user_id: 1,
        food: "pear",
        event_type: "discarded",
        quantity: 2,
        occurred_at: "2026-06-03T00:00:00Z",
        metadata: { reason: "spoiled" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await createUserFoodEvent({
      food_id: "pear",
      event_type: "discarded",
      quantity: 2,
      metadata: { reason: "spoiled" },
    });

    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(init.body).toBe(
      JSON.stringify({
        quantity: 2,
        metadata: { reason: "spoiled" },
        food_id: "pear",
        event_type: "discarded",
      }),
    );
  });

  it("fetches habits", async () => {
    const habits = [
      {
        id: 1,
        evidence_id: "habit-1",
        user_id: 1,
        food: "banana",
        habit_type: "frequent_consumption",
        score: 0.8,
        evidence: { count: 3 },
        updated_at: "2026-06-03T00:00:00Z",
      },
    ];
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(habits));
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchHabits()).resolves.toEqual(habits);
    expect(fetchMock.mock.calls[0][0]).toBe("http://eai.744477.xyz/api/habits");
  });
});
