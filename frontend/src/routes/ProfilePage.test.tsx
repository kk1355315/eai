import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { profileQueryKey, usePatchProfile, useProfile } from "../api/profile";
import type { Profile } from "../api/types";
import { renderWithProviders } from "../test/test-utils";
import ProfilePage from "./ProfilePage";

vi.mock("../api/profile", () => ({
  profileQueryKey: ["profile"],
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
    expect(screen.queryByLabelText("Edit profile")).toBeNull();
    expect(screen.queryByText("Diana Kemmer")).toBeNull();
    expect(screen.queryByText("diana.k@gmail.com")).toBeNull();
  });

  it("shows the profile update time in Beijing time", () => {
    mockUseProfile.mockReturnValue({
      data: profile({ updated_at: "2026-06-10T18:52:27Z" }),
      error: null,
      isError: false,
      isLoading: false,
      refetch: vi.fn(),
    } as never);

    renderWithProviders(<ProfilePage />);

    expect(screen.getByText("Updated 2026-06-11 02:52:27")).toBeTruthy();
  });

  it("saves only the active profile field to PATCH payload shape", async () => {
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

    fireEvent.click(screen.getByRole("button", { name: /edit profile section goal/i }));
    fireEvent.change(
      screen.getByPlaceholderText("Eat fruit before it loses freshness"),
      { target: { value: "  Eat pears first  " } },
    );

    fireEvent.click(screen.getByRole("button", { name: /save profile/i }));

    await waitFor(() => {
      expect(mutate).toHaveBeenCalledWith(
        {
          goal: "Eat pears first",
        },
        expect.objectContaining({
          onSuccess: expect.any(Function),
        }),
      );
    });
  });

  it("keeps local draft values when profile data refetches while editing", () => {
    const firstProfile = profile();
    mockUseProfile.mockReturnValue({
      data: firstProfile,
      error: null,
      isError: false,
      isLoading: false,
      refetch: vi.fn(),
    } as never);

    const { rerender } = renderWithProviders(<ProfilePage />);

    fireEvent.click(screen.getByRole("button", { name: /edit profile section goal/i }));
    fireEvent.change(
      screen.getByPlaceholderText("Eat fruit before it loses freshness"),
      { target: { value: "Draft goal that is not saved yet" } },
    );

    mockUseProfile.mockReturnValue({
      data: profile({ goal: "Server refetch value" }),
      error: null,
      isError: false,
      isLoading: false,
      refetch: vi.fn(),
    } as never);
    rerender(<ProfilePage />);

    expect(screen.getByDisplayValue("Draft goal that is not saved yet")).toBeTruthy();
    expect(screen.queryByDisplayValue("Server refetch value")).toBeNull();
  });

  it("collapses the edit form after a successful save and caches the returned profile", async () => {
    const savedProfile = profile({ goal: "Saved profile goal" });
    const mutate = vi.fn((_payload, options?: { onSuccess?: (profile: Profile) => void }) => {
      options?.onSuccess?.(savedProfile);
    });
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

    const { queryClient } = renderWithProviders(<ProfilePage />);

    fireEvent.click(screen.getByRole("button", { name: /edit profile section goal/i }));
    expect(screen.getByLabelText("Edit profile Goal")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /save profile/i }));

    await waitFor(() => {
      expect(screen.queryByLabelText("Edit profile Goal")).toBeNull();
    });
    expect(queryClient.getQueryData(profileQueryKey)).toEqual(savedProfile);
  });

  it("opens only the clicked inline editor and toggles it closed", () => {
    mockUseProfile.mockReturnValue({
      data: profile(),
      error: null,
      isError: false,
      isLoading: false,
      refetch: vi.fn(),
    } as never);

    renderWithProviders(<ProfilePage />);

    const goalRow = screen.getByRole("button", { name: /edit profile section goal/i });
    const dietRow = screen.getByRole("button", { name: /edit profile section diet preference/i });

    fireEvent.click(goalRow);
    expect(screen.getByLabelText("Edit profile Goal")).toBeTruthy();
    expect(screen.queryByLabelText("Edit profile Diet Preference")).toBeNull();

    fireEvent.click(dietRow);
    expect(screen.queryByLabelText("Edit profile Goal")).toBeNull();
    expect(screen.getByLabelText("Edit profile Diet Preference")).toBeTruthy();

    fireEvent.click(dietRow);
    expect(screen.queryByLabelText("Edit profile Diet Preference")).toBeNull();
  });
});
