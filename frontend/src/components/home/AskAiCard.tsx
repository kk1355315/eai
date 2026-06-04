import { Link } from "react-router-dom";
import { ChevronRight, Sparkles } from "lucide-react";
import { useLanguage } from "../../lib/language";
import "./home.css";

export function AskAiCard() {
  const { language } = useLanguage();

  return (
    <Link to="/advice" className="home-advisor-link" aria-label="Open food advice">
      <section className="home-card home-advisor-card">
        <span className="home-advisor-icon" aria-hidden="true">
          <Sparkles size={27} strokeWidth={2.2} />
        </span>
        <div>
          <h2 className="home-advisor-title">{language === "zh" ? "询问 AI" : "Ask AI"}</h2>
          <p className="home-advisor-copy">
            {language === "zh" ? "获取个性化建议" : "Get personalized advice"}
          </p>
        </div>
        <ChevronRight className="home-advisor-arrow" size={24} strokeWidth={2.2} aria-hidden="true" />
      </section>
    </Link>
  );
}
