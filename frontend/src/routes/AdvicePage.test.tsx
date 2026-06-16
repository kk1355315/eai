import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useGenerateLlmAdvice, useShoppingAdvice } from "../api/advice";
import { renderWithProviders } from "../test/test-utils";
import AdvicePage from "./AdvicePage";

vi.mock("../api/advice", () => ({
  useGenerateLlmAdvice: vi.fn(),
  useShoppingAdvice: vi.fn(),
}));

const mockUseShoppingAdvice = vi.mocked(useShoppingAdvice);
const mockUseGenerateLlmAdvice = vi.mocked(useGenerateLlmAdvice);

describe("AdvicePage", () => {
  beforeEach(() => {
    mockUseGenerateLlmAdvice.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as never);
  });

  it("shows an error instead of static shopping advice when the API fails", () => {
    mockUseShoppingAdvice.mockReturnValue({
      data: undefined,
      error: new Error("backend offline"),
      isError: true,
      isLoading: false,
      refetch: vi.fn(),
    } as never);

    renderWithProviders(<AdvicePage />);

    expect(screen.getByRole("alert")).toBeTruthy();
    expect(screen.queryByText("Eat banana before buying more")).toBeNull();
  });

  it("shows LLM request errors without fabricating fallback advice", async () => {
    mockUseShoppingAdvice.mockReturnValue({
      data: { recommendations: [] },
      error: null,
      isError: false,
      isLoading: false,
      refetch: vi.fn(),
    } as never);
    mockUseGenerateLlmAdvice.mockReturnValue({
      mutateAsync: vi.fn().mockRejectedValue(new Error("LLM unavailable")),
      isPending: false,
    } as never);

    renderWithProviders(<AdvicePage />);

    fireEvent.change(
      screen.getByPlaceholderText("Ask about today's fruit, meals, or what to buy next."),
      { target: { value: "Help me plan" } },
    );
    fireEvent.click(screen.getByRole("button", { name: /send advice request/i }));

    await waitFor(() => {
      expect(screen.getByText("LLM unavailable")).toBeTruthy();
    });
    expect(
      screen.queryByText("Use your confirmed fruit inventory as the source of truth for now."),
    ).toBeNull();
  });

  it("groups duplicate shopping suggestions into one compact card", () => {
    mockUseShoppingAdvice.mockReturnValue({
      data: {
        recommendations: [
          {
            title: "Apple no duplicate purchase",
            content: "Apple inventory is still available.",
            action_type: "avoid_duplicate_purchase",
            related_foods: ["apple"],
            basis: ["Apple is available."],
            evidence_ids: ["evidence-apple"],
            confidence: "high",
          },
          {
            title: "Banana no duplicate purchase",
            content: "Banana inventory is still available.",
            action_type: "avoid_duplicate_purchase",
            related_foods: ["banana"],
            basis: ["Banana is available."],
            evidence_ids: ["evidence-banana"],
            confidence: "high",
          },
          {
            title: "Pear no duplicate purchase",
            content: "Pear inventory is still available.",
            action_type: "avoid_duplicate_purchase",
            related_foods: ["pear"],
            basis: ["Pear is available."],
            evidence_ids: ["evidence-pear"],
            confidence: "high",
          },
        ],
      },
      error: null,
      isError: false,
      isLoading: false,
      refetch: vi.fn(),
    } as never);

    renderWithProviders(<AdvicePage />, { language: "zh" });

    expect(screen.getByText("苹果、香蕉、梨 暂时不用重复购买")).toBeTruthy();
    expect(screen.queryByText("Apple no duplicate purchase")).toBeNull();
    expect(screen.getByRole("heading", { name: "询问建议" })).toBeTruthy();
  });
});
