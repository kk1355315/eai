import {
  Bell,
  ChevronRight,
  CircleGauge,
  HeartPulse,
  Leaf,
  Package,
  ShieldPlus,
  type LucideIcon,
} from "lucide-react";
import type { Profile } from "../../api/types";
import { formatBeijingDateTime } from "../../lib/datetime";
import { FOOD_DISPLAY_NAMES, SUPPORTED_FOODS } from "../../lib/foods";
import { useLanguage } from "../../lib/language";
import { type AvoidFood, type ProfileFormValue } from "./ProfileForm";
import { ProfilePillGroup } from "./ProfilePillGroup";
import styles from "./ProfileOverview.module.css";

export type ProfileEditField = keyof ProfileFormValue;

type ProfileOverviewProps = {
  activeField: ProfileEditField | null;
  canSubmit?: boolean;
  error?: string | null;
  formValue: ProfileFormValue;
  isSaving?: boolean;
  onChange: (value: ProfileFormValue) => void;
  onSubmit: () => void;
  onToggleField: (field: ProfileEditField) => void;
  profile: Profile;
};

type ProfileRow = {
  field: ProfileEditField;
  icon: LucideIcon;
  title: string;
  tags: string[];
  hint: string;
  placeholder?: string;
  multiline?: boolean;
};

const avoidFoodOptions: Array<{ value: AvoidFood; label: string }> = SUPPORTED_FOODS.map(
  (value) => ({
    value,
    label: FOOD_DISPLAY_NAMES[value],
  }),
);

export function ProfileOverview({
  activeField,
  canSubmit = true,
  error,
  formValue,
  isSaving = false,
  onChange,
  onSubmit,
  onToggleField,
  profile,
}: ProfileOverviewProps) {
  const { language, t } = useLanguage();
  const rows = buildRows(profile, language, t);
  const updateField = (field: ProfileEditField, nextValue: string | AvoidFood[]) => {
    onChange({
      ...formValue,
      [field]: nextValue,
    });
  };

  return (
    <div className={styles.stack}>
      <section className={styles.identityCard} aria-label={t("profile")}>
        <div className={styles.avatar} aria-hidden="true">
          <img alt="" src="/profile-avatar.png" />
        </div>
        <div className={styles.identityCopy}>
          <h2>{t("profile")}</h2>
          <p>{profile.updated_at ? `${t("updated")} ${formatDate(profile.updated_at)}` : t("none")}</p>
        </div>
      </section>

      <section className={styles.menuList} aria-label={t("profile")}>
        {rows.map((row) => {
          const Icon = row.icon;
          const isOpen = activeField === row.field;

          return (
            <div className={styles.rowGroup} key={row.field}>
              <button
                aria-expanded={isOpen}
                aria-label={`${t("editProfileSection")} ${row.title}`}
                className={styles.menuRow}
                onClick={() => onToggleField(row.field)}
                type="button"
              >
                <span className={styles.iconWrap} aria-hidden="true">
                  <Icon size={30} strokeWidth={2} />
                </span>
                <span className={styles.rowCopy}>
                  <span className={styles.rowTitle}>{row.title}</span>
                  <span className={styles.tags}>
                    {row.tags.slice(0, 2).map((tag) => (
                      <span className={styles.tag} key={tag}>
                        {tag}
                      </span>
                    ))}
                    {row.tags.length > 2 ? (
                      <span className={styles.tag}>+{row.tags.length - 2}</span>
                    ) : null}
                  </span>
                </span>
                <ChevronRight
                  className={`${styles.chevron} ${isOpen ? styles.chevronOpen : ""}`}
                  size={27}
                  strokeWidth={1.9}
                />
              </button>
              {isOpen ? (
                <form
                  aria-label={`${t("editProfile")} ${row.title}`}
                  className={styles.inlineEditor}
                  onSubmit={(event) => {
                    event.preventDefault();
                    onSubmit();
                  }}
                >
                  <label className={styles.editorLabel}>
                    <span>{row.hint}</span>
                    {row.field === "avoid_foods" ? (
                      <ProfilePillGroup
                        label={t("profileAvoidLabel")}
                        options={avoidFoodOptions}
                        value={formValue.avoid_foods}
                        onChange={(nextValue) => updateField("avoid_foods", nextValue)}
                      />
                    ) : row.multiline ? (
                      <textarea
                        required={isRequiredField(row.field)}
                        value={String(formValue[row.field] ?? "")}
                        onChange={(event) => updateField(row.field, event.target.value)}
                        placeholder={row.placeholder}
                        rows={row.field === "allergies_optional" ? 2 : 3}
                        className={styles.editorControl}
                      />
                    ) : (
                      <input
                        required={isRequiredField(row.field)}
                        value={String(formValue[row.field] ?? "")}
                        onChange={(event) => updateField(row.field, event.target.value)}
                        placeholder={row.placeholder}
                        className={styles.editorControl}
                      />
                    )}
                  </label>
                  {error ? <p className={styles.editorError}>{error}</p> : null}
                  <button
                    className={styles.saveButton}
                    disabled={!canSubmit || isSaving}
                    type="submit"
                  >
                    {isSaving ? t("saving") : t("saveProfile")}
                  </button>
                </form>
              ) : null}
            </div>
          );
        })}
      </section>
    </div>
  );
}

function isRequiredField(field: ProfileEditField) {
  return (
    field === "goal" ||
    field === "diet_preference" ||
    field === "cooking_condition"
  );
}

function buildRows(
  profile: Profile,
  language: "en" | "zh",
  t: ReturnType<typeof useLanguage>["t"],
): ProfileRow[] {
  return [
    {
      field: "goal",
      icon: CircleGauge,
      title: t("profileGoalTitle"),
      hint: t("profileGoalHint"),
      placeholder: t("profileGoalPlaceholder"),
      tags: tagsFromText(profile.goal, language === "zh" ? "未设置" : "Not set"),
      multiline: true,
    },
    {
      field: "diet_preference",
      icon: Leaf,
      title: t("profileDietTitle"),
      hint: t("profileDietHint"),
      placeholder: t("profileDietPlaceholder"),
      tags: tagsFromText(profile.diet_preference, language === "zh" ? "未设置" : "Not set"),
    },
    {
      field: "cooking_condition",
      icon: Package,
      title: t("profileCookingTitle"),
      hint: t("profileCookingHint"),
      placeholder: t("profileCookingPlaceholder"),
      tags: tagsFromText(profile.cooking_condition, language === "zh" ? "未设置" : "Not set"),
      multiline: true,
    },
    {
      field: "avoid_foods",
      icon: Bell,
      title: t("profileAvoidTitle"),
      hint: t("profileAvoidHint"),
      tags: profile.avoid_foods.length
        ? profile.avoid_foods.map((food) => tFoodName(food, language))
        : [t("none")],
    },
    {
      field: "allergies_optional",
      icon: ShieldPlus,
      title: t("profileAllergiesTitle"),
      hint: t("profileAllergiesHint"),
      placeholder: t("profileOptionalPlaceholder"),
      tags: tagsFromText(profile.allergies_optional, t("none")),
      multiline: true,
    },
    {
      field: "health_notes_optional",
      icon: HeartPulse,
      title: t("profileHealthNotesTitle"),
      hint: t("profileHealthNotesHint"),
      placeholder: t("profileOptionalPlaceholder"),
      tags: tagsFromText(profile.health_notes_optional, t("none")),
      multiline: true,
    },
  ];
}

function tFoodName(food: string, language: "en" | "zh") {
  const names: Record<string, Record<"en" | "zh", string>> = {
    apple: { en: "Apple", zh: "苹果" },
    banana: { en: "Banana", zh: "香蕉" },
    litchi: { en: "Litchi", zh: "荔枝" },
    pear: { en: "Pear", zh: "梨" },
  };

  return names[food]?.[language] ?? food;
}

function tagsFromText(value: string | null | undefined, fallback: string) {
  if (!value?.trim()) {
    return [fallback];
  }

  return value
    .split(/[,，/]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function formatDate(value: string) {
  return formatBeijingDateTime(value);
}
