import { AlertCircle, RotateCcw } from "lucide-react";
import { GlassCard } from "./GlassCard";
import { useLanguage } from "../../lib/language";
import styles from "./ErrorCard.module.css";

type ErrorCardProps = {
  title?: string;
  message?: string;
  onRetry?: () => void;
  retryLabel?: string;
};

export function ErrorCard({
  title,
  message,
  onRetry,
  retryLabel,
}: ErrorCardProps) {
  const { t } = useLanguage();
  const visibleTitle = title ?? t("somethingNeedsAttention");
  const visibleMessage = message ?? t("pleaseTryAgain");
  const visibleRetryLabel = retryLabel ?? t("retry");

  return (
    <GlassCard className={styles.card} tone="strong" role="alert">
      <div className={styles.iconWrap}>
        <AlertCircle className={styles.icon} aria-hidden="true" strokeWidth={2.2} />
      </div>
      <div className={styles.copy}>
        <h2>{visibleTitle}</h2>
        <p>{visibleMessage}</p>
        {onRetry ? (
          <button className={styles.retryButton} type="button" onClick={onRetry}>
            <RotateCcw size={17} strokeWidth={2.2} aria-hidden="true" />
            <span>{visibleRetryLabel}</span>
          </button>
        ) : null}
      </div>
    </GlassCard>
  );
}
