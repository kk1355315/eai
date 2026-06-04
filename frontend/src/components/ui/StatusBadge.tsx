import styles from "./StatusBadge.module.css";

export type StatusTone =
  | "fresh"
  | "eat_soon"
  | "check_required"
  | "not_recommended"
  | "inactive";

type StatusBadgeProps = {
  tone: StatusTone;
  children: string;
};

export function StatusBadge({ tone, children }: StatusBadgeProps) {
  return <span className={`${styles.badge} ${styles[tone]}`}>{children}</span>;
}
