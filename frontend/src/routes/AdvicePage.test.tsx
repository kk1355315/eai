import { screen } from "@testing-library/react";
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
});
