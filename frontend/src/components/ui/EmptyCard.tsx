import { Leaf } from "lucide-react";
import { GlassCard } from "./GlassCard";
import styles from "./EmptyCard.module.css";

type EmptyCardProps = {
  title: string;
  description?: string;
};

export function EmptyCard({ title, description }: EmptyCardProps) {
  return (
    <GlassCard className={styles.card}>
      <div className={styles.iconWrap}>
        <Leaf className={styles.icon} aria-hidden="true" strokeWidth={2.2} />
      </div>
      <div className={styles.copy}>
        <h2>{title}</h2>
        {description ? <p>{description}</p> : null}
      </div>
    </GlassCard>
  );
}
