import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { usePatchProfile, useProfile } from "../api/profile";
import type { Profile } from "../api/types";
import { renderWithProviders } from "../test/test-utils";
import ProfilePage from "./ProfilePage";

vi.mock("../api/profile", () => ({
  usePatchProfile: vi.fn(),
  useProfile: vi.fn(),
}));

const mockUseProfile = vi.mocked(useProfile);
const mockUsePatchProfile = vi.mocked(usePatchProfile);

function profile(overrides: Partial<Profile> = {}): Profile {
  return {
    id: 1,
    goal: "Reduce fruit waste",
    diet_preference: "Light meals",
    cooking_condition: "Simple washing and slicing",
    avoid_foods: ["apple"],
    allergies_optional: "None",
    health_notes_optional: null,
    created_at: "2026-06-01T00:00:00Z",
    updated_at: "2026-06-02T00:00:00Z",
    ...overrides,
  };
}

describe("ProfilePage", () => {
  beforeEach(() => {
    mockUsePatchProfile.mockReturnValue({
      error: null,
      isPending: false,
      mutate: vi.fn(),
    } as never);
  });

  it("shows an error instead of the preview profile when the API fails", () => {
    mockUseProfile.mockReturnValue({
      data: undefined,
      error: new Error("backend offline"),
      isError: true,
      isLoading: false,
      refetch: vi.fn(),
    } as never);

    renderWithProviders(<ProfilePage />);

    expect(screen.getByRole("alert")).toBeTruthy();
    expect(screen.queryByText("Diana Kemmer")).toBeNull();
  });

  it("renders backend profile data instead of fixed identity text", () => {
    mockUseProfile.mockReturnValue({
      data: profile(),
      error: null,
      isError: false,
      isLoading: false,
      refetch: vi.fn(),
    } as never);

    renderWithProviders(<ProfilePage />);

    expect(screen.getAllByText("Reduce fruit waste").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Light meals").length).toBeGreaterThan(0);
    expect(screen.queryByText("Diana Kemmer")).toBeNull();
    expect(screen.queryByText("diana.k@gmail.com")).toBeNull();
  });

  it("saves editable profile fields to PATCH payload shape", async () => {
    const mutate = vi.fn();
    mockUsePatchProfile.mockReturnValue({
      error: null,
      isPending: false,
      mutate,
    } as never);
    mockUseProfile.mockReturnValue({
      data: profile(),
      error: null,
      isError: false,
      isLoading: false,
      refetch: vi.fn(),
    } as never);

    renderWithProviders(<ProfilePage />);

    fireEvent.change(
      screen.getByPlaceholderText("Eat fruit before it loses freshness"),
      { target: { value: "  Eat pears first  " } },
    );
    fireEvent.change(
      screen.getByPlaceholderText("Light, low sugar, fruit first"),
      { target: { value: "  low sugar  " } },
    );
    fireEvent.change(
      screen.getByPlaceholderText("No oven, simple washing and slicing"),
      { target: { value: "  no oven  " } },
    );
    fireEvent.change(screen.getAllByPlaceholderText("Optional")[0], {
      target: { value: "   " },
    });
    fireEvent.change(screen.getAllByPlaceholderText("Optional")[1], {
      target: { value: "  avoid late snacks  " },
    });
    fireEvent.click(screen.getByRole("button", { name: "香蕉" }));
    fireEvent.click(screen.getByRole("button", { name: /save profile/i }));

    await waitFor(() => {
      expect(mutate).toHaveBeenCalledWith({
        goal: "Eat pears first",
        diet_preference: "low sugar",
        cooking_condition: "no oven",
        avoid_foods: ["apple", "banana"],
        allergies_optional: null,
        health_notes_optional: "avoid late snacks",
      });
    });
  });
});
