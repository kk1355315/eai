import type { Profile } from "../../api/types";

export const profileFixture: Profile = {
  id: 1,
  goal: "Keep daily fruit advice practical.",
  diet_preference: "balanced",
  cooking_condition: "no cooking",
  avoid_foods: ["litchi"],
  allergies_optional: "Avoid pear when throat feels dry.",
  health_notes_optional: "Prefer smaller portions of banana.",
  created_at: "2026-06-03T12:00:00.000Z",
  updated_at: "2026-06-03T12:00:00.000Z",
};

export const profileWithAllMvpFruitsFixture: Profile = {
  ...profileFixture,
  avoid_foods: ["apple", "banana", "litchi", "pear"],
};

export const profileWithNonMvpIngredientsFixture: Profile = {
  ...profileFixture,
  avoid_foods: ["apple", "strawberry", "milk"],
  allergies_optional: "Strawberry and milk are non-MVP fixture samples.",
};
