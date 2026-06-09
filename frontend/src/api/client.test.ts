import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiRequest } from "./client";

function jsonResponse(payload: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers({ "content-type": "application/json" }),
    json: vi.fn().mockResolvedValue(payload),
    text: vi.fn().mockResolvedValue(""),
  } as unknown as Response;
}

function textResponse(payload: string, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers({ "content-type": "text/plain" }),
    json: vi.fn(),
    text: vi.fn().mockResolvedValue(payload),
  } as unknown as Response;
}

describe("apiRequest", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("adds the /api prefix once and serializes query/body", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      apiRequest("/inventory", {
        method: "POST",
        query: {
          page: 1,
          active: true,
          empty: null,
          missing: undefined,
        },
        headers: { "X-Test": "yes" },
        body: { food: "apple" },
      }),
    ).resolves.toEqual({ ok: true });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = new Headers(init.headers);

    expect(url).toBe("http://eai.744477.xyz/api/inventory?page=1&active=true");
    expect(init.method).toBe("POST");
    expect(init.body).toBe(JSON.stringify({ food: "apple" }));
    expect(headers.get("Accept")).toBe("application/json");
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(headers.get("X-Test")).toBe("yes");
  });

  it("does not duplicate an existing /api prefix", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: 1 }));
    vi.stubGlobal("fetch", fetchMock);

    await apiRequest("/api/profile");

    expect(fetchMock.mock.calls[0][0]).toBe("http://eai.744477.xyz/api/profile");
  });

  it("throws ApiError with json detail and details payload", async () => {
    const payload = { detail: "Bad profile patch", code: "invalid" };
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(payload, 422));
    vi.stubGlobal("fetch", fetchMock);

    await expect(apiRequest("/profile")).rejects.toMatchObject({
      name: "ApiError",
      message: "Bad profile patch",
      status: 422,
      details: payload,
    });

    await expect(apiRequest("/profile")).rejects.toBeInstanceOf(ApiError);
  });

  it("uses non-json error text as the ApiError message", async () => {
    const fetchMock = vi.fn().mockResolvedValue(textResponse("Gateway timeout", 504));
    vi.stubGlobal("fetch", fetchMock);

    await expect(apiRequest("/inventory")).rejects.toMatchObject({
      message: "Gateway timeout",
      status: 504,
      details: "Gateway timeout",
    });
  });
});
