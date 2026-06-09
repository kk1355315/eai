import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useProfile } from "../api/profile";
import { renderWithProviders } from "../test/test-utils";
import ProfilePage from "./ProfilePage";

vi.mock("../api/profile", () => ({
  useProfile: vi.fn(),
}));

const mockUseProfile = vi.mocked(useProfile);

describe("ProfilePage", () => {
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
});
