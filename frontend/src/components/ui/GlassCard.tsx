import type { ComponentPropsWithoutRef, ReactNode } from "react";
import styles from "./GlassCard.module.css";

type GlassCardProps = ComponentPropsWithoutRef<"section"> & {
  children: ReactNode;
  tone?: "default" | "strong";
};

export function GlassCard({
  children,
  className,
  tone = "default",
  ...props
}: GlassCardProps) {
  const classNames = [
    styles.card,
    tone === "strong" ? styles.strong : "",
    className ?? "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <section className={classNames} {...props}>
      {children}
    </section>
  );
}
