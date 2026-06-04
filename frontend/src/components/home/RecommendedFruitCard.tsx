import { Sparkle } from "lucide-react";
import { useLanguage } from "../../lib/language";
import { HOME_HERO_IMAGE_SRC } from "../../lib/fruitAssets";
import "./home.css";

export type HomeFruitStatus =
  | "fresh"
  | "eat_soon"
  | "check_required"
  | "not_recommended"
  | null;

export type HomeFruit = {
  id: string | number;
  modelLabel: "apple" | "banana" | "litchi" | "pear";
  displayName: string;
  quantity?: number | null;
  unit?: string | null;
  remainingDays?: number | null;
  storageState: HomeFruitStatus;
  message?: string | null;
};

type RecommendedFruitCardProps = {
  fruit?: HomeFruit;
};

function recommendedCopy(days: number | null | undefined, language: "en" | "zh") {
  if (language === "zh") {
    if (days == null) return "今天优先检查后再安排。";
    if (days <= 0) return "今天最适合食用。";
    return days === 1 ? "今天最值得优先安排。" : `还有 ${days} 天新鲜窗口。`;
  }

  if (days == null) return "Check before planning the next bite.";
  if (days <= 0) return "Best to eat today.";
  return days === 1 ? "Best to eat today." : `${days} days of freshness left.`;
}

export function RecommendedFruitCard({ fruit }: RecommendedFruitCardProps) {
  const { foodName, language, t } = useLanguage();
  const title = fruit ? foodName(fruit.modelLabel, fruit.displayName) : t("nothingUrgent");
  const copy = fruit
    ? recommendedCopy(fruit.remainingDays, language)
    : t("nothingUrgentCopy");

  return (
    <section className="home-card home-recommended">
      <div>
        <p className="home-recommended-kicker">
          {language === "zh" ? "今日推荐水果" : "Today's Recommended Fruit"}
        </p>
        <h2 className="home-recommended-title">{title}</h2>
        <p className="home-recommended-copy">{copy}</p>
        <span className="home-recommended-pill">
          <Sparkle size={18} strokeWidth={2.2} aria-hidden="true" />
          {language === "zh" ? "新鲜优先" : "Freshness first"}
        </span>
      </div>
      <div className="home-fruit-photo" aria-hidden="true">
        <img alt="" className="home-hero-image" src={HOME_HERO_IMAGE_SRC} />
      </div>
    </section>
  );
}
