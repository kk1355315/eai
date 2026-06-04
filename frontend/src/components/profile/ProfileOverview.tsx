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
import { useLanguage } from "../../lib/language";
import styles from "./ProfileOverview.module.css";

type ProfileOverviewProps = {
  profile: Profile;
};

type ProfileRow = {
  icon: LucideIcon;
  title: string;
  tags: string[];
};

export function ProfileOverview({ profile }: ProfileOverviewProps) {
  const { language, t } = useLanguage();
  const rows = buildRows(profile, language, t);

  return (
    <div className={styles.stack}>
      <section className={styles.identityCard} aria-label={t("profile")}>
        <div className={styles.avatar} aria-hidden="true">
          <img alt="" src="/profile-avatar.png" />
        </div>
        <div className={styles.identityCopy}>
          <h2>{t("profileName")}</h2>
          <p>{t("profileEmail")}</p>
        </div>
      </section>

      <section className={styles.menuList} aria-label={t("profile")}>
        {rows.map((row) => {
          const Icon = row.icon;

          return (
            <button className={styles.menuRow} key={row.title} type="button">
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
      title: t("household"),
      tags: [language === "zh" ? "3 人" : "3 people"],
    },
    {
      icon: Leaf,
      title: t("dietPreferences"),
      tags: [t("lightMeals"), t("lowSugar")],
    },
    {
      icon: ShieldPlus,
      title: t("allergies"),
      tags: tagsFromText(profile.allergies_optional, t("none")),
    },
    {
      icon: HeartPulse,
      title: t("healthGoals"),
      tags: [t("fresh"), t("weightManagement")],
    },
    {
      icon: Bell,
      title: t("reminders"),
      tags: [t("everyTwoDays")],
    },
  ];
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
