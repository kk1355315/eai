import { afterEach, describe, expect, it, vi } from "vitest";
import type { Profile } from "./types";
import { fetchProfile, patchProfile } from "./profile";

function profile(overrides: Partial<Profile> = {}): Profile {
  return {
    id: 1,
    goal: "balanced",
    diet_preference: "home cooking",
    cooking_condition: "simple kitchen",
    avoid_foods: ["apple"],
    allergies_optional: null,
    health_notes_optional: null,
    created_at: "2026-06-01T00:00:00Z",
    updated_at: "2026-06-02T00:00:00Z",
    ...overrides,
  };
}

function jsonResponse(payload: unknown): Response {
  return {
    ok: true,
    status: 200,
    headers: new Headers({ "content-type": "application/json" }),
    json: vi.fn().mockResolvedValue(payload),
    text: vi.fn().mockResolvedValue(""),
  } as unknown as Response;
}

describe("profile api", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetches profile and filters avoid_foods to supported fruit", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse(profile({ avoid_foods: ["apple", "mango", "pear"] })));
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchProfile()).resolves.toMatchObject({
      avoid_foods: ["apple", "pear"],
    });
    expect(fetchMock.mock.calls[0][0]).toBe("/api/profile");
  });

  it("filters avoid_foods before patching profile", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse(profile({ avoid_foods: ["banana"] })));
    vi.stubGlobal("fetch", fetchMock);

    await patchProfile({
      goal: "less waste",
      avoid_foods: ["banana", "mango", "litchi"],
    });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/profile");
    expect(init.method).toBe("PATCH");
    expect(init.body).toBe(
      JSON.stringify({
        goal: "less waste",
        avoid_foods: ["banana", "litchi"],
      }),
    );
  });
});
