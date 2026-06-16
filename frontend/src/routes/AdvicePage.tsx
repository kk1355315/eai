import { type CSSProperties, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronLeft, ShoppingBasket } from "lucide-react";
import { useGenerateLlmAdvice, useShoppingAdvice } from "../api/advice";
import { EmptyCard } from "../components/ui/EmptyCard";
import { ErrorCard } from "../components/ui/ErrorCard";
import { GlassCard } from "../components/ui/GlassCard";
import { LoadingCard } from "../components/ui/LoadingCard";
import { type AdviceItem as CardAdviceItem } from "../components/advice/AdviceCard";
import { AskAiPanel, type AskAiRequest, type AskAiResult } from "../components/advice/AskAiPanel";
import { mapAdviceResponseLike, type AdviceViewModel } from "../lib/mappers";
import { useLanguage } from "../lib/language";
import { getFoodDisplayName, isSupportedFoodLabel } from "../lib/foods";

type QueryLike<T> = {
  data?: T;
  isLoading?: boolean;
  isError?: boolean;
  error?: unknown;
  refetch?: () => unknown;
};

type MutationLike<TPayload, TResult> = {
  mutate?: (payload: TPayload, options?: { onSuccess?: (data: TResult) => void }) => void;
  mutateAsync?: (payload: TPayload) => Promise<TResult>;
  isPending?: boolean;
  isLoading?: boolean;
  error?: unknown;
};

const styles = {
  back: {
    width: 54,
    height: 54,
    borderRadius: 14,
    display: "grid",
    placeItems: "center",
    marginBottom: 18,
    color: "#2584ff",
    background: "rgba(255, 255, 255, 0.68)",
    border: "1px solid rgba(255, 255, 255, 0.78)",
    boxShadow: "0 14px 36px rgba(74, 103, 139, 0.1)",
    textDecoration: "none",
  },
  sectionHeader: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    margin: "8px 2px 16px",
    color: "#07152f",
  },
  sectionTitle: {
    margin: 0,
    fontSize: 30,
    lineHeight: 1.12,
    fontWeight: 820,
    letterSpacing: 0,
  },
  stack: {
    display: "grid",
    gap: 22,
  },
  cards: {
    display: "grid",
    gap: 18,
  },
  shoppingSummaryCard: {
    padding: "22px 28px",
  },
  shoppingSummary: {
    display: "grid",
    gridTemplateColumns: "46px 1fr",
    alignItems: "center",
    gap: 16,
  },
  shoppingSummaryIcon: {
    width: 46,
    height: 46,
    borderRadius: 12,
    display: "grid",
    placeItems: "center",
    color: "#2584ff",
    background: "rgba(37, 132, 255, 0.1)",
  },
  shoppingSummaryText: {
    margin: 0,
    color: "#07152f",
    fontSize: 25,
    lineHeight: 1.28,
    fontWeight: 800,
    letterSpacing: 0,
  },
} satisfies Record<string, CSSProperties>;

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null ? (value as Record<string, unknown>) : {};
}

function asArray(value: unknown): unknown[] {
  if (Array.isArray(value)) return value;
  if (value && typeof value === "object" && Array.isArray((value as { items?: unknown[] }).items)) {
    return (value as { items: unknown[] }).items;
  }
  return [];
}

function toCardAdvice(item: AdviceViewModel): CardAdviceItem {
  return {
    title: item.title,
    content: item.content,
    actionType: item.action_type,
    actionLabel: item.actionLabel,
    relatedFoods: item.relatedSupportedFoods,
    basis: item.basis,
    evidenceSources: item.evidence_sources,
    confidence: item.confidence,
  };
}

function normalizeAdviceCards(data: unknown): CardAdviceItem[] {
  return mapAdviceResponseLike(data).map(toCardAdvice);
}

function getShoppingSummaryFoods(items: CardAdviceItem[]): string[] {
  const foods: string[] = [];
  for (const item of items) {
    for (const food of item.relatedFoods ?? []) {
      if (!foods.includes(food)) {
        foods.push(food);
      }
    }
  }
  return foods;
}

function normalizeAskAiResult(data: unknown): AskAiResult {
  const record = asRecord(data);
  const advice = asRecord(record.advice);
  const recommendations = normalizeAdviceCards(advice.recommendations ?? record.recommendations);

  return {
    accepted: record.accepted !== false,
    errors: asArray(record.errors).map(String),
    advice: {
      summary: (advice.summary ?? record.summary ?? null) as string | null,
      recommendations,
      fallback: (advice.fallback ?? record.fallback ?? false) as boolean,
    },
    record_id: (record.record_id ?? record.recordId ?? null) as string | number | null,
  };
}

export default function AdvicePage() {
  const { foodName, language, t } = useLanguage();
  const shoppingQuery = useShoppingAdvice() as QueryLike<unknown>;
  const askMutation = useGenerateLlmAdvice() as MutationLike<AskAiRequest, unknown>;
  const [askResult, setAskResult] = useState<AskAiResult | null>(null);
  const shoppingData = shoppingQuery.data;

  const shoppingItems = useMemo(() => normalizeAdviceCards(shoppingData), [shoppingData]);
  const shoppingSummaryFoods = useMemo(
    () => getShoppingSummaryFoods(shoppingItems),
    [shoppingItems],
  );
  const shoppingSummaryText = shoppingSummaryFoods.length
    ? `${shoppingSummaryFoods
        .map((food) =>
          isSupportedFoodLabel(food)
            ? foodName(food, getFoodDisplayName(food))
            : getFoodDisplayName(food),
        )
        .join(language === "zh" ? "、" : ", ")} ${t("shoppingDuplicateSummary")}`
    : null;
  const isAskPending = Boolean(askMutation.isPending || askMutation.isLoading);

  async function handleAskSubmit(request: AskAiRequest) {
    try {
      if (askMutation.mutateAsync) {
        const result = await askMutation.mutateAsync(request);
        setAskResult(normalizeAskAiResult(result));
        return;
      }

      askMutation.mutate?.(request, {
        onSuccess: (result) => setAskResult(normalizeAskAiResult(result)),
      });
    } catch (error) {
      setAskResult({
        accepted: false,
        errors: [error instanceof Error ? error.message : "Advice request failed."],
        advice: null,
        record_id: null,
      });
    }
  }

  return (
    <div style={styles.stack}>
      <Link to="/" style={styles.back} aria-label={t("backToday")}>
        <ChevronLeft size={22} strokeWidth={2.2} aria-hidden="true" />
      </Link>

      <section>
        <div style={styles.sectionHeader}>
          <ShoppingBasket size={21} strokeWidth={2.2} aria-hidden="true" />
          <h2 style={styles.sectionTitle}>{t("shoppingAdvice")}</h2>
        </div>
        <div style={styles.cards}>
          {shoppingQuery.isLoading ? <LoadingCard /> : null}
          {shoppingQuery.isError ? (
            <ErrorCard onRetry={() => shoppingQuery.refetch?.()} />
          ) : null}
          {!shoppingQuery.isLoading && !shoppingQuery.isError && shoppingItems.length === 0 ? (
            <EmptyCard
              title={t("noShoppingAdvice")}
              description={t("noShoppingAdviceCopy")}
            />
          ) : null}
          {!shoppingQuery.isLoading && !shoppingQuery.isError && shoppingSummaryText ? (
            <GlassCard style={styles.shoppingSummaryCard}>
              <div style={styles.shoppingSummary}>
                <span style={styles.shoppingSummaryIcon} aria-hidden="true">
                  <ShoppingBasket size={19} strokeWidth={2.2} />
                </span>
                <p style={styles.shoppingSummaryText}>{shoppingSummaryText}</p>
              </div>
            </GlassCard>
          ) : null}
        </div>
      </section>

      <AskAiPanel result={askResult} isPending={isAskPending} onSubmit={handleAskSubmit} />
    </div>
  );
}
