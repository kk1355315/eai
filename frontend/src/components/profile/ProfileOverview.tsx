import {
  Bell,
  ChevronRight,
  HeartPulse,
  House,
  Leaf,
  ShieldPlus,
  UsersRound,
  type LucideIcon,
} from "lucide-react";
import type { Profile } from "../../api/types";
import { formatBeijingDateTime } from "../../lib/datetime";
import { useLanguage } from "../../lib/language";
import styles from "./ProfileOverview.module.css";

type ProfileOverviewProps = {
  profile: Profile;
  onEdit?: () => void;
};

type ProfileRow = {
  icon: LucideIcon;
  title: string;
  tags: string[];
};

export function ProfileOverview({ profile, onEdit }: ProfileOverviewProps) {
  const { language, t } = useLanguage();
  const rows = buildRows(profile, language, t);

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

          return (
            <button
              aria-label={`${t("editProfileSection")} ${row.title}`}
              className={styles.menuRow}
              key={row.title}
              onClick={onEdit}
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
              <ChevronRight className={styles.chevron} size={27} strokeWidth={1.9} />
            </button>
          );
        })}
      </section>
    </div>
  );
}

function buildRows(
  profile: Profile,
  language: "en" | "zh",
  t: ReturnType<typeof useLanguage>["t"],
): ProfileRow[] {
  return [
    {
      icon: UsersRound,
      title: t("simplePrep"),
      tags: tagsFromText(profile.cooking_condition, language === "zh" ? "未设置" : "Not set"),
    },
    {
      icon: Leaf,
      title: t("dietPreferences"),
      tags: tagsFromText(profile.diet_preference, language === "zh" ? "未设置" : "Not set"),
    },
    {
      icon: ShieldPlus,
      title: t("allergies"),
      tags: tagsFromText(profile.allergies_optional, t("none")),
    },
    {
      icon: HeartPulse,
      title: t("healthGoals"),
      tags: tagsFromText(
        [profile.goal, profile.health_notes_optional].filter(Boolean).join(","),
        language === "zh" ? "未设置" : "Not set",
      ),
    },
    {
      icon: Bell,
      title: t("avoid"),
      tags: profile.avoid_foods.length
        ? profile.avoid_foods.map((food) => tFoodName(food, language))
        : [t("none")],
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
