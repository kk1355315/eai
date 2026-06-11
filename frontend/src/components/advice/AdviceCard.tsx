import type { CSSProperties } from "react";
import { CheckCircle2, ShoppingBasket } from "lucide-react";
import { GlassCard } from "../ui/GlassCard";
import { getActionTypeLabel } from "../../lib/status";
import { getFoodDisplayName } from "../../lib/foods";

export type AdviceItem = {
  id?: string | number;
  title?: string | null;
  content?: string | null;
  actionType?: string | null;
  actionLabel?: string | null;
  relatedFoods?: string[] | null;
  basis?: string[] | string | null;
  evidenceIds?: Array<string | number> | null;
  evidenceSources?: Array<{
    title?: string | null;
    source?: string | null;
    summary?: string | null;
    url?: string | null;
  }> | null;
  confidence?: number | string | null;
};

type AdviceCardProps = {
  item: AdviceItem;
  tone?: "shopping" | "ai";
  variant?: "card" | "inline";
};

const styles = {
  card: {
    padding: 28,
  },
  inlineCard: {
    padding: "22px 0 0",
    borderTop: "1px solid rgba(143, 164, 194, 0.18)",
  },
  header: {
    display: "grid",
    gridTemplateColumns: "46px 1fr",
    alignItems: "center",
    gap: 16,
    marginBottom: 16,
  },
  icon: {
    width: 46,
    height: 46,
    borderRadius: 12,
    display: "grid",
    placeItems: "center",
    color: "#2584ff",
    background: "rgba(37, 132, 255, 0.1)",
  },
  title: {
    margin: 0,
    color: "#07152f",
    fontSize: 25,
    lineHeight: 1.22,
    fontWeight: 800,
    letterSpacing: 0,
  },
  content: {
    margin: 0,
    color: "#697895",
    fontSize: 20,
    lineHeight: 1.58,
  },
  meta: {
    display: "flex",
    flexWrap: "wrap" as const,
    gap: 10,
    marginTop: 20,
  },
  pill: {
    borderRadius: 10,
    padding: "8px 12px",
    color: "#697895",
    background: "rgba(255, 255, 255, 0.66)",
    fontSize: 16,
    lineHeight: 1.25,
  },
  evidence: {
    display: "grid",
    gap: 10,
    marginTop: 20,
    paddingTop: 18,
    borderTop: "1px solid rgba(143, 164, 194, 0.18)",
  },
  evidenceTitle: {
    margin: 0,
    color: "#07152f",
    fontSize: 17,
    fontWeight: 800,
    lineHeight: 1.25,
  },
  evidenceText: {
    margin: 0,
    color: "#697895",
    fontSize: 17,
    lineHeight: 1.55,
  },
  sourceList: {
    display: "grid",
    gap: 8,
    margin: 0,
    padding: 0,
    listStyle: "none",
  },
  sourceItem: {
    display: "grid",
    gap: 3,
  },
  sourceTitle: {
    color: "#07152f",
    fontWeight: 760,
    textDecoration: "none",
  },
  sourceMeta: {
    margin: 0,
    color: "#8a98b3",
    fontSize: 13,
    lineHeight: 1.35,
  },
} satisfies Record<string, CSSProperties>;

function confidenceCopy(confidence?: number | string | null) {
  if (confidence == null) return null;
  if (typeof confidence === "string") return `${confidence} confidence`;
  if (confidence > 1) return `${Math.round(confidence)}% confidence`;
  return `${Math.round(confidence * 100)}% confidence`;
}

export function AdviceCard({ item, tone = "ai", variant = "card" }: AdviceCardProps) {
  const Icon = tone === "shopping" ? ShoppingBasket : CheckCircle2;
  const confidence = confidenceCopy(item.confidence);
  const actionLabel =
    item.actionLabel ?? (item.actionType ? getActionTypeLabel(item.actionType) : null);
  const basis = Array.isArray(item.basis)
    ? item.basis
    : item.basis
      ? [item.basis]
      : [];
  const evidenceSources = item.evidenceSources?.filter(
    (source) => source.title || source.summary,
  ) ?? [];

  const content = (
    <>
      <div style={styles.header}>
        <span style={styles.icon} aria-hidden="true">
          <Icon size={19} strokeWidth={2.2} />
        </span>
        <h3 style={styles.title}>{item.title || "Food advice"}</h3>
      </div>
      <p style={styles.content}>
        {item.content ||
          (Array.isArray(item.basis) ? item.basis.join(" ") : item.basis) ||
          "No extra detail was returned for this suggestion."}
      </p>
      <div style={styles.meta}>
        {actionLabel ? <span style={styles.pill}>{actionLabel}</span> : null}
        {confidence ? <span style={styles.pill}>{confidence}</span> : null}
        {item.relatedFoods?.map((food) => (
          <span key={food} style={styles.pill}>
            {getFoodDisplayName(food)}
          </span>
        ))}
      </div>
      {basis.length || evidenceSources.length ? (
        <div style={styles.evidence}>
          {basis.length ? (
            <>
              <p style={styles.evidenceTitle}>依据</p>
              <p style={styles.evidenceText}>{basis.join("；")}</p>
            </>
          ) : null}
          {evidenceSources.length ? (
            <>
              <p style={styles.evidenceTitle}>来源</p>
              <ul style={styles.sourceList}>
                {evidenceSources.map((source, index) => (
                  <li key={`${source.title ?? "source"}-${index}`} style={styles.sourceItem}>
                    {source.url ? (
                      <a href={source.url} target="_blank" rel="noreferrer" style={styles.sourceTitle}>
                        {source.title}
                      </a>
                    ) : (
                      <span style={styles.sourceTitle}>{source.title}</span>
                    )}
                    {source.source ? (
                      <p style={styles.sourceMeta}>{source.source}</p>
                    ) : null}
                    {source.summary ? (
                      <p style={styles.evidenceText}>{source.summary}</p>
                    ) : null}
                  </li>
                ))}
              </ul>
            </>
          ) : null}
        </div>
      ) : null}
    </>
  );

  if (variant === "inline") {
    return <article style={styles.inlineCard}>{content}</article>;
  }

  return (
    <GlassCard style={styles.card}>
      {content}
    </GlassCard>
  );
}
