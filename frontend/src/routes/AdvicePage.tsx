import { type CSSProperties, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronLeft, ShoppingBasket } from "lucide-react";
import { useGenerateLlmAdvice, useShoppingAdvice } from "../api/advice";
import { EmptyCard } from "../components/ui/EmptyCard";
import { ErrorCard } from "../components/ui/ErrorCard";
import { LoadingCard } from "../components/ui/LoadingCard";
import { AdviceCard, type AdviceItem as CardAdviceItem } from "../components/advice/AdviceCard";
import { AskAiPanel, type AskAiRequest, type AskAiResult } from "../components/advice/AskAiPanel";
import { mapAdviceResponseLike, type AdviceViewModel } from "../lib/mappers";
import { useLanguage } from "../lib/language";

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
    width: 42,
    height: 42,
    borderRadius: 10,
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
    gap: 9,
    margin: "4px 2px 12px",
    color: "#07152f",
  },
  sectionTitle: {
    margin: 0,
    fontSize: 24,
    lineHeight: 1.12,
    fontWeight: 820,
    letterSpacing: 0,
  },
  stack: {
    display: "grid",
    gap: 16,
  },
  cards: {
    display: "grid",
    gap: 12,
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
    evidenceIds: item.evidence_ids,
    confidence: item.confidence,
  };
}

function normalizeAdviceCards(data: unknown): CardAdviceItem[] {
  return mapAdviceResponseLike(data).map(toCardAdvice);
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
  const { t } = useLanguage();
  const shoppingQuery = useShoppingAdvice() as QueryLike<unknown>;
  const askMutation = useGenerateLlmAdvice() as MutationLike<AskAiRequest, unknown>;
  const [askResult, setAskResult] = useState<AskAiResult | null>(null);
  const shoppingData = shoppingQuery.data;

  const shoppingItems = useMemo(() => normalizeAdviceCards(shoppingData), [shoppingData]);
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
        advice: {
          summary: "Use your confirmed fruit inventory as the source of truth for now.",
          recommendations: [],
          fallback: true,
        },
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
          {!shoppingQuery.isLoading && !shoppingQuery.isError
            ? shoppingItems.map((item, index) => (
                <AdviceCard key={item.id ?? `${item.title ?? "shopping"}-${index}`} item={item} tone="shopping" />
              ))
            : null}
        </div>
      </section>

      <AskAiPanel result={askResult} isPending={isAskPending} onSubmit={handleAskSubmit} />
    </div>
  );
}
