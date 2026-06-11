import { GlassCard } from "./GlassCard";
import { useLanguage } from "../../lib/language";
import styles from "./LoadingCard.module.css";

type LoadingCardProps = {
  rows?: number;
  title?: string;
};

export function LoadingCard({ rows = 3, title }: LoadingCardProps) {
  const { t } = useLanguage();
  const visibleTitle = title ?? t("loading");

  return (
    <GlassCard className={styles.card} aria-busy="true" aria-label={visibleTitle}>
      <div className={styles.header} />
      {Array.from({ length: rows }).map((_, index) => (
        <div className={styles.row} key={index}>
          <span className={styles.avatar} />
          <span className={styles.line} />
        </div>
      ))}
    </GlassCard>
  );
}
