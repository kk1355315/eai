import { FruitAvatar } from "../ui/FruitAvatar";
import type { HomeFruit } from "./RecommendedFruitCard";
import { useLanguage } from "../../lib/language";
import "./home.css";

type PriorityListProps = {
  items: HomeFruit[];
};

function priorityMeta(item: HomeFruit, language: "en" | "zh") {
  const quantity = item.quantity == null ? null : `${item.quantity}${item.unit ?? ""}`;
  if (item.remainingDays == null) return quantity;
  if (language === "zh") {
    if (item.remainingDays <= 0) return quantity ? `${quantity} · 今天食用` : "今天食用";
    return quantity ? `${quantity} · 剩余 ${item.remainingDays} 天` : `剩余 ${item.remainingDays} 天`;
  }
  if (item.remainingDays <= 0) return quantity ? `${quantity} · use today` : "use today";
  return quantity ? `${quantity} · ${item.remainingDays}d left` : `${item.remainingDays}d left`;
}

export function PriorityList({ items }: PriorityListProps) {
  const { foodName, language, t } = useLanguage();

  return (
    <section className="home-card home-section-card">
      <div className="home-section-head">
        <h2 className="home-section-title">{t("priority")}</h2>
        <span className="home-section-count">{items.slice(0, 2).length} {t("items")}</span>
      </div>
      {items.length === 0 ? (
        <p className="home-empty-copy">{t("priorityEmpty")}</p>
      ) : (
        <div className="home-priority-grid">
          {items.slice(0, 2).map((item) => (
            <article className="home-priority-item" key={item.id}>
              <FruitAvatar fruit={item.modelLabel} label={item.displayName} size="sm" />
              <div>
                <p className="home-item-title">{foodName(item.modelLabel, item.displayName)}</p>
                {priorityMeta(item, language) ? <p className="home-item-meta">{priorityMeta(item, language)}</p> : null}
              </div>
              <span className={`home-status-dot ${item.storageState ?? "fresh"}`} aria-hidden="true" />
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
