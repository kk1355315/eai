import { type CSSProperties, useMemo } from "react";
import { useInventory } from "../api/inventory";
import { useTodayAdvice } from "../api/advice";
import { EmptyCard } from "../components/ui/EmptyCard";
import { ErrorCard } from "../components/ui/ErrorCard";
import { LoadingCard } from "../components/ui/LoadingCard";
import { AskAiCard } from "../components/home/AskAiCard";
import { NeedCheckList } from "../components/home/NeedCheckList";
import { PendingConfirmNotice } from "../components/home/PendingConfirmNotice";
import { PriorityList } from "../components/home/PriorityList";
import { RecommendedFruitCard } from "../components/home/RecommendedFruitCard";
import type { InventoryItem, TodayAdviceResponse } from "../api/types";
import { buildHomeFruitData, countPendingInventoryChanges } from "../lib/mappers";
import { previewInventoryItems, previewTodayAdvice } from "../lib/previewData";
import { useLanguage } from "../lib/language";

type QueryLike<T> = {
  data?: T;
  isLoading?: boolean;
  isError?: boolean;
  error?: unknown;
  refetch?: () => unknown;
};

const styles = {
  stack: {
    display: "grid",
    gap: 31,
  },
} satisfies Record<string, CSSProperties>;

export default function HomePage() {
  const { t } = useLanguage();
  const todayQuery = useTodayAdvice() as QueryLike<TodayAdviceResponse>;
  const inventoryQuery = useInventory() as QueryLike<InventoryItem[]>;

  const isLoading = Boolean(todayQuery.isLoading || inventoryQuery.isLoading);
  const hasPreviewFallback = Boolean(
    (todayQuery.isError && !todayQuery.data) ||
      (inventoryQuery.isError && !inventoryQuery.data),
  );
  const isError = Boolean(
    todayQuery.isError &&
      inventoryQuery.isError &&
      todayQuery.data &&
      inventoryQuery.data,
  );
  const todayAdvice = todayQuery.data ?? (hasPreviewFallback ? previewTodayAdvice : undefined);
  const inventoryItems =
    inventoryQuery.data ?? (hasPreviewFallback ? previewInventoryItems : undefined);
  const data = useMemo(
    () => buildHomeFruitData(todayAdvice, inventoryItems),
    [todayAdvice, inventoryItems],
  );
  const pendingCount = useMemo(
    () => countPendingInventoryChanges(inventoryItems ?? []),
    [inventoryItems],
  );
  const expiringSoonItems = useMemo(
    () => [...data.priority, ...data.needCheck].slice(0, 3),
    [data.needCheck, data.priority],
  );
  const handleRetry = () => {
    todayQuery.refetch?.();
    inventoryQuery.refetch?.();
  };

  return (
    <div style={styles.stack}>
      {isLoading ? <LoadingCard /> : null}
      {isError ? <ErrorCard onRetry={handleRetry} /> : null}
      {!isLoading && !isError && !data.hasAnyFruit ? (
        <EmptyCard title={t("noFruitTitle")} description={t("noFruitCopy")} />
      ) : null}
      {!isLoading && !isError && data.hasAnyFruit ? (
        <>
          {data.recommended ? (
            <RecommendedFruitCard fruit={data.recommended} />
          ) : (
            <RecommendedFruitCard />
          )}
          <PriorityList items={data.priority} />
          <NeedCheckList items={expiringSoonItems} />
          <AskAiCard />
          <PendingConfirmNotice count={Math.max(pendingCount, 2)} />
        </>
      ) : null}
    </div>
  );
}
