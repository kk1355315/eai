import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "../../test/test-utils";
import { ProfileForm, type ProfileFormValue } from "./ProfileForm";

const emptyProfile: ProfileFormValue = {
  goal: "",
  diet_preference: "",
  cooking_condition: "",
  avoid_foods: [],
  allergies_optional: "",
  health_notes_optional: "",
};

describe("ProfileForm", () => {
  it("marks required fields and disables save when submit is not allowed", () => {
    renderWithProviders(
      <ProfileForm
        value={emptyProfile}
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        canSubmit={false}
      />,
    );

    expect(
      (screen.getByPlaceholderText("Eat fruit before it loses freshness") as HTMLTextAreaElement)
        .required,
    ).toBe(true);
    expect(
      (screen.getByPlaceholderText("Light, low sugar, fruit first") as HTMLInputElement)
        .required,
    ).toBe(true);
    expect(
      (screen.getByPlaceholderText("No oven, simple washing and slicing") as HTMLTextAreaElement)
        .required,
    ).toBe(true);
    expect((screen.getByRole("button", { name: /save profile/i }) as HTMLButtonElement).disabled).toBe(
      true,
    );
  });

  it("offers only the four MVP avoid foods and emits food labels", () => {
    const onChange = vi.fn();

    renderWithProviders(
      <ProfileForm
        value={emptyProfile}
        onChange={onChange}
        onSubmit={vi.fn()}
      />,
    );

    for (const fruit of ["苹果", "香蕉", "荔枝", "梨"]) {
      expect(screen.getByRole("button", { name: fruit })).toBeTruthy();
    }
    expect(screen.queryByRole("button", { name: /mango|pineapple|orange/i })).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "梨" }));

    expect(onChange).toHaveBeenCalledWith({
      ...emptyProfile,
      avoid_foods: ["pear"],
    });
  });

  it("renders profile editing copy in Chinese", () => {
    renderWithProviders(
      <ProfileForm
        value={emptyProfile}
        onChange={vi.fn()}
        onSubmit={vi.fn()}
      />,
      { language: "zh" },
    );

    expect(screen.getByText("目标")).toBeTruthy();
    expect(screen.getByText("饮食偏好")).toBeTruthy();
    expect(screen.getByText("处理条件")).toBeTruthy();
    expect(screen.getByText("避免食物")).toBeTruthy();
    expect(screen.getByPlaceholderText("在水果失去新鲜度前吃完")).toBeTruthy();
    expect(screen.getByRole("button", { name: "保存资料" })).toBeTruthy();
  });
});
