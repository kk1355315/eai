import type { CSSProperties } from "react";
import { CheckCircle2, Info, ShoppingBasket } from "lucide-react";
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
  confidence?: number | string | null;
};

type AdviceCardProps = {
  item: AdviceItem;
  tone?: "shopping" | "ai";
};

const styles = {
  card: {
    padding: 20,
  },
  header: {
    display: "grid",
    gridTemplateColumns: "38px 1fr",
    alignItems: "center",
    gap: 12,
    marginBottom: 10,
  },
  icon: {
    width: 38,
    height: 38,
    borderRadius: 9,
    display: "grid",
    placeItems: "center",
    color: "#2584ff",
    background: "rgba(37, 132, 255, 0.1)",
  },
  title: {
    margin: 0,
    color: "#07152f",
    fontSize: 19,
    lineHeight: 1.18,
    fontWeight: 800,
    letterSpacing: 0,
  },
  content: {
    margin: 0,
    color: "#697895",
    fontSize: 16,
    lineHeight: 1.52,
  },
  meta: {
    display: "flex",
    flexWrap: "wrap" as const,
    gap: 8,
    marginTop: 14,
  },
  pill: {
    borderRadius: 8,
    padding: "6px 10px",
    color: "#697895",
    background: "rgba(255, 255, 255, 0.66)",
    fontSize: 13,
    lineHeight: 1.2,
  },
} satisfies Record<string, CSSProperties>;

function confidenceCopy(confidence?: number | string | null) {
  if (confidence == null) return null;
  if (typeof confidence === "string") return `${confidence} confidence`;
  if (confidence > 1) return `${Math.round(confidence)}% confidence`;
  return `${Math.round(confidence * 100)}% confidence`;
}

export function AdviceCard({ item, tone = "ai" }: AdviceCardProps) {
  const Icon = tone === "shopping" ? ShoppingBasket : CheckCircle2;
  const confidence = confidenceCopy(item.confidence);
  const actionLabel =
    item.actionLabel ?? (item.actionType ? getActionTypeLabel(item.actionType) : null);

  return (
    <GlassCard style={styles.card}>
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
        {item.evidenceIds?.length ? (
          <span style={styles.pill}>
            <Info size={12} strokeWidth={2.2} aria-hidden="true" /> {item.evidenceIds.length} evidence
          </span>
        ) : null}
      </div>
    </GlassCard>
  );
}
