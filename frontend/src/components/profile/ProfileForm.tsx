import type { CSSProperties } from "react";
import { CircleGauge, Leaf, Package, ShieldPlus } from "lucide-react";
import type { SupportedFoodLabel } from "../../api/types";
import { FOOD_DISPLAY_NAMES, SUPPORTED_FOODS } from "../../lib/foods";
import { ProfileFieldRow } from "./ProfileFieldRow";
import { ProfilePillGroup } from "./ProfilePillGroup";

export type AvoidFood = SupportedFoodLabel;

export type ProfileFormValue = {
  goal: string;
  diet_preference: string;
  cooking_condition: string;
  avoid_foods: AvoidFood[];
  allergies_optional: string;
  health_notes_optional: string;
};

type ProfileFormProps = {
  value: ProfileFormValue;
  onChange: (value: ProfileFormValue) => void;
  onSubmit: () => void;
  isSaving?: boolean;
  canSubmit?: boolean;
  error?: string | null;
};

const avoidFoodOptions: Array<{ value: AvoidFood; label: string }> = SUPPORTED_FOODS.map(
  (value) => ({
    value,
    label: FOOD_DISPLAY_NAMES[value],
  }),
);

export function ProfileForm({
  value,
  onChange,
  onSubmit,
  isSaving = false,
  canSubmit = true,
  error,
}: ProfileFormProps) {
  const updateField = (field: keyof ProfileFormValue, nextValue: string | AvoidFood[]) => {
    onChange({
      ...value,
      [field]: nextValue,
    });
  };

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
      style={styles.form}
    >
      <ProfileFieldRow
        icon={<CircleGauge size={23} strokeWidth={2.2} />}
        title="Goal"
        hint="Keep the recommendation direction practical."
      >
        <textarea
          required
          value={value.goal}
          onChange={(event) => updateField("goal", event.target.value)}
          placeholder="Eat fruit before it loses freshness"
          rows={3}
          style={styles.textarea}
        />
      </ProfileFieldRow>

      <ProfileFieldRow
        icon={<Leaf size={23} strokeWidth={2.2} />}
        title="Diet Preference"
        hint="Short preference for daily food advice."
      >
        <input
          required
          value={value.diet_preference}
          onChange={(event) => updateField("diet_preference", event.target.value)}
          placeholder="Light, low sugar, fruit first"
          style={styles.input}
        />
      </ProfileFieldRow>

      <ProfileFieldRow
        icon={<Package size={23} strokeWidth={2.2} />}
        title="Cooking Condition"
        hint="What you can prepare at home."
      >
        <textarea
          required
          value={value.cooking_condition}
          onChange={(event) => updateField("cooking_condition", event.target.value)}
          placeholder="No oven, simple washing and slicing"
          rows={3}
          style={styles.textarea}
        />
      </ProfileFieldRow>

      <ProfileFieldRow
        icon={<ShieldPlus size={23} strokeWidth={2.2} />}
        title="Avoid Foods"
        hint="Only MVP fruit options are supported."
      >
        <ProfilePillGroup
          label="Fruit to avoid"
          options={avoidFoodOptions}
          value={value.avoid_foods}
          onChange={(nextValue) => updateField("avoid_foods", nextValue)}
        />
      </ProfileFieldRow>

      <ProfileFieldRow
        icon={<ShieldPlus size={23} strokeWidth={2.2} />}
        title="Allergies"
        hint="Optional notes used by food advice."
      >
        <textarea
          value={value.allergies_optional}
          onChange={(event) => updateField("allergies_optional", event.target.value)}
          placeholder="Optional"
          rows={2}
          style={styles.textarea}
        />
      </ProfileFieldRow>

      <ProfileFieldRow
        quiet
        icon={<ShieldPlus size={23} strokeWidth={2.2} />}
        title="Health Notes"
        hint="Optional constraints to keep recommendations calm."
      >
        <textarea
          value={value.health_notes_optional}
          onChange={(event) => updateField("health_notes_optional", event.target.value)}
          placeholder="Optional"
          rows={3}
          style={styles.textarea}
        />
      </ProfileFieldRow>

      {error ? <p style={styles.error}>{error}</p> : null}

      <button
        type="submit"
        disabled={!canSubmit || isSaving}
        style={{
          ...styles.saveButton,
          ...(!canSubmit || isSaving ? styles.saveButtonDisabled : undefined),
        }}
      >
        {isSaving ? "Saving" : "Save Profile"}
      </button>
    </form>
  );
}

const controlBase: CSSProperties = {
  background: "rgba(255, 255, 255, 0.76)",
  border: "1px solid rgba(143, 164, 194, 0.22)",
  borderRadius: 12,
  boxSizing: "border-box",
  color: "#07152f",
  font: "inherit",
  fontSize: 16,
  fontWeight: 650,
  lineHeight: 1.45,
  outline: "none",
  width: "100%",
};

const styles: Record<string, CSSProperties> = {
  form: {
    display: "flex",
    flexDirection: "column",
  },
  input: {
    ...controlBase,
    height: 52,
    padding: "0 16px",
  },
  textarea: {
    ...controlBase,
    minHeight: 86,
    padding: "14px 16px",
    resize: "vertical",
  },
  error: {
    background: "rgba(239, 68, 68, 0.08)",
    border: "1px solid rgba(239, 68, 68, 0.14)",
    borderRadius: 10,
    color: "#8b5e63",
    fontSize: 14,
    fontWeight: 750,
    lineHeight: 1.45,
    margin: "20px 0 0",
    padding: "12px 14px",
  },
  saveButton: {
    appearance: "none",
    background: "#2584ff",
    border: 0,
    borderRadius: 10,
    boxShadow: "0 16px 34px rgba(37, 132, 255, 0.24)",
    color: "#ffffff",
    cursor: "pointer",
    font: "inherit",
    fontSize: 17,
    fontWeight: 850,
    height: 56,
    marginTop: 22,
    transition: "transform 140ms ease, opacity 140ms ease",
    width: "100%",
  },
  saveButtonDisabled: {
    cursor: "not-allowed",
    opacity: 0.58,
  },
};
