import { ShieldPlus } from "lucide-react";
import { FruitAvatar } from "../ui/FruitAvatar";
import type { HomeFruit } from "./RecommendedFruitCard";
import { useLanguage } from "../../lib/language";
import "./home.css";

type NeedCheckListProps = {
  items: HomeFruit[];
};

export function NeedCheckList({ items }: NeedCheckListProps) {
  const { foodName, language, t } = useLanguage();

  return (
    <section className="home-card home-section-card">
      <div className="home-need-head">
        <span className="home-need-icon" aria-hidden="true">
          <ShieldPlus size={22} strokeWidth={2.2} />
        </span>
        <h2 className="home-section-title">
          {language === "zh" ? "即将过期" : "Expiring Soon"}
        </h2>
      </div>
      {items.length === 0 ? (
        <p className="home-empty-copy">{t("needCheckEmpty")}</p>
      ) : (
        <div className="home-need-list">
          {items.slice(0, 3).map((item) => (
            <article className="home-need-row" key={item.id}>
              <FruitAvatar fruit={item.modelLabel} label={item.displayName} size="sm" />
              <div>
                <p className="home-item-title">{foodName(item.modelLabel, item.displayName)}</p>
                <p className="home-item-meta">
                  {formatExpiringMeta(item.remainingDays, language)}
                </p>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function formatExpiringMeta(days: number | null | undefined, language: "en" | "zh") {
  if (language === "zh") {
    if (days == null) return "需确认";
    if (days <= 0) return "今天";
    return `${days} 天`;
  }

  if (days == null) return "Check";
  if (days <= 0) return "Today";
  return `${days} days`;
}
