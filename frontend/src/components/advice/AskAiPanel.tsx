import { type CSSProperties, type FormEvent, useState } from "react";
import { Search, Send, Sparkles } from "lucide-react";
import { GlassCard } from "../ui/GlassCard";
import { AdviceCard, type AdviceItem } from "./AdviceCard";
import { useLanguage } from "../../lib/language";
import stylesModule from "./AskAiPanel.module.css";

export type AskAiRequest = {
  question?: string;
  enable_thinking?: boolean;
  search_query?: string;
};

export type AskAiResult = {
  accepted: boolean;
  errors?: string[] | null;
  advice?: {
    summary?: string | null;
    recommendations?: AdviceItem[] | null;
    fallback?: boolean | null;
  } | null;
  record_id?: string | number | null;
};

type AskAiPanelProps = {
  result?: AskAiResult | null;
  isPending?: boolean;
  onSubmit: (request: AskAiRequest) => void;
};

const styles = {
  card: {
    padding: "48px 42px 52px",
    color: "#07152f",
    opacity: 1,
  },
  header: {
    display: "flex",
    alignItems: "center",
    gap: 18,
    marginBottom: 30,
  },
  icon: {
    width: 58,
    height: 58,
    borderRadius: 16,
    display: "grid",
    placeItems: "center",
    color: "#2584ff",
    background: "rgba(37, 132, 255, 0.1)",
  },
  title: {
    margin: 0,
    color: "#07152f",
    fontSize: 38,
    lineHeight: 1.12,
    fontWeight: 820,
    letterSpacing: 0,
  },
  form: {
    display: "grid",
    gap: 24,
    opacity: 1,
  },
  textarea: {
    width: "100%",
    minHeight: 238,
    boxSizing: "border-box" as const,
    resize: "vertical" as const,
    border: "1px solid rgba(143, 164, 194, 0.22)",
    borderRadius: 16,
    padding: "26px 28px",
    color: "#07152f",
    background: "rgba(255, 255, 255, 0.68)",
    font: "inherit",
    fontSize: 23,
    lineHeight: 1.5,
    outline: "none",
  },
  searchRow: {
    display: "grid",
    gridTemplateColumns: "1fr auto",
    gap: 16,
    alignItems: "center",
  },
  inputWrap: {
    display: "grid",
    gridTemplateColumns: "24px 1fr",
    alignItems: "center",
    gap: 12,
    border: "1px solid rgba(143, 164, 194, 0.22)",
    borderRadius: 16,
    padding: "20px 22px",
    color: "#2584ff",
    background: "rgba(255, 255, 255, 0.58)",
  },
  input: {
    minWidth: 0,
    border: 0,
    outline: 0,
    color: "#07152f",
    background: "transparent",
    font: "inherit",
    fontSize: 22,
  },
  thinking: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    color: "#07152f",
    fontSize: 21,
    lineHeight: 1.35,
  },
  checkbox: {
    width: 26,
    height: 26,
    accentColor: "#2584ff",
  },
  button: {
    width: 72,
    height: 72,
    border: 0,
    borderRadius: 17,
    display: "grid",
    placeItems: "center",
    color: "#ffffff",
    background: "#2584ff",
    boxShadow: "0 14px 32px rgba(37, 132, 255, 0.24)",
    cursor: "pointer",
  },
  buttonDisabled: {
    opacity: 0.86,
    cursor: "default",
  },
  thinkingStatus: {
    display: "grid",
    gridTemplateColumns: "42px 1fr",
    alignItems: "center",
    gap: 14,
    border: "1px solid rgba(37, 132, 255, 0.18)",
    borderRadius: 16,
    padding: "16px 18px",
    color: "#254063",
    background: "rgba(37, 132, 255, 0.08)",
    fontSize: 18,
    lineHeight: 1.45,
    fontWeight: 720,
    overflow: "hidden",
  },
  thinkingOrb: {
    width: 42,
    height: 42,
    borderRadius: 12,
    display: "grid",
    placeItems: "center",
    color: "#2584ff",
    background: "rgba(255, 255, 255, 0.72)",
    boxShadow: "0 10px 26px rgba(37, 132, 255, 0.16)",
  },
  result: {
    display: "grid",
    gap: 18,
    marginTop: 24,
  },
  summary: {
    margin: 0,
    color: "#07152f",
    fontSize: 20,
    lineHeight: 1.58,
    fontWeight: 700,
  },
  notice: {
    borderRadius: 12,
    padding: 16,
    color: "#697895",
    background: "rgba(255, 138, 0, 0.1)",
    fontSize: 17,
    lineHeight: 1.5,
  },
  errorList: {
    margin: 0,
    paddingLeft: 18,
    color: "#8b5e63",
    fontSize: 17,
    lineHeight: 1.5,
  },
} satisfies Record<string, CSSProperties>;

export function AskAiPanel({ result, isPending = false, onSubmit }: AskAiPanelProps) {
  const { t } = useLanguage();
  const [question, setQuestion] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [enableThinking, setEnableThinking] = useState(false);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit({
      question: question.trim() || undefined,
      search_query: searchQuery.trim() || undefined,
      enable_thinking: enableThinking,
    });
  }

  const recommendations = result?.advice?.recommendations ?? [];
  const hasErrors = Boolean(result?.errors?.length);
  const isFallback = Boolean(result?.advice?.fallback || result?.accepted === false);

  return (
    <GlassCard style={styles.card}>
      <div style={styles.header}>
        <span style={styles.icon} aria-hidden="true">
          <Sparkles size={24} strokeWidth={2.2} />
        </span>
        <h2 style={styles.title}>{t("askAdvice")}</h2>
      </div>
      <form style={styles.form} onSubmit={handleSubmit}>
        <textarea
          className={stylesModule.textarea}
          style={styles.textarea}
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder={t("askAdvicePlaceholder")}
        />
        <div style={styles.searchRow}>
          <label style={styles.inputWrap}>
            <Search size={21} strokeWidth={2.1} aria-hidden="true" />
            <input
              className={stylesModule.input}
              style={styles.input}
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder={t("optionalSearchContext")}
            />
          </label>
          <button
            type="submit"
            style={{ ...styles.button, ...(isPending ? styles.buttonDisabled : {}) }}
            disabled={isPending}
            aria-label={t("sendAdviceRequest")}
          >
            <Send size={23} strokeWidth={2.3} aria-hidden="true" />
          </button>
        </div>
        <label style={styles.thinking}>
          <input
            type="checkbox"
            style={styles.checkbox}
            checked={enableThinking}
            onChange={(event) => setEnableThinking(event.target.checked)}
          />
          {t("moreCarefulReasoning")}
        </label>
        {isPending ? (
          <div
            className={stylesModule.thinkingStatus}
            style={styles.thinkingStatus}
            role="status"
            aria-live="polite"
          >
            <span className={stylesModule.thinkingOrb} style={styles.thinkingOrb} aria-hidden="true">
              <Sparkles size={19} strokeWidth={2.25} />
            </span>
            <span>
              {t("thinkingAboutAdvice")}
              <span className={stylesModule.dots} aria-hidden="true">
                <span />
                <span />
                <span />
              </span>
            </span>
          </div>
        ) : null}
      </form>

      {result ? (
        <div style={styles.result}>
          {isFallback ? (
            <div style={styles.notice}>
              {t("fallbackGuidance")}
            </div>
          ) : null}
          {hasErrors ? (
            <ul style={styles.errorList}>
              {result.errors?.map((error) => (
                <li key={error}>{error}</li>
              ))}
            </ul>
          ) : null}
          {result.advice?.summary ? <p style={styles.summary}>{result.advice.summary}</p> : null}
          {recommendations.map((item, index) => (
            <AdviceCard
              key={item.id ?? `${item.title ?? "advice"}-${index}`}
              item={item}
              variant="inline"
            />
          ))}
        </div>
      ) : null}
    </GlassCard>
  );
}
