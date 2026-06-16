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
          {language === "zh" ? "需要检查" : "Need Check"}
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
                  {formatCheckMeta(item.remainingDays, language)}
                </p>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function formatCheckMeta(days: number | null | undefined, language: "en" | "zh") {
  if (language === "zh") {
    if (days == null || days <= 0) {
      return "已超过参考保存期";
    }
    return `参考保存期还剩 ${days} 天`;
  }

  if (days == null || days <= 0) {
    return "Past the reference storage period. Check appearance, smell, and actual condition.";
  }
  return `${days} days left in the reference storage period`;
}
