import type { CSSProperties, ReactNode } from "react";
import { ChevronRight } from "lucide-react";

type ProfileFieldRowProps = {
  icon: ReactNode;
  title: string;
  hint: string;
  children: ReactNode;
  quiet?: boolean;
};

export function ProfileFieldRow({
  icon,
  title,
  hint,
  children,
  quiet = false,
}: ProfileFieldRowProps) {
  return (
    <section style={{ ...styles.row, ...(quiet ? styles.rowQuiet : undefined) }}>
      <div style={styles.rowHead}>
        <div style={styles.iconWrap}>{icon}</div>
        <div style={styles.rowCopy}>
          <h2 style={styles.rowTitle}>{title}</h2>
          <p style={styles.rowHint}>{hint}</p>
        </div>
        <ChevronRight aria-hidden="true" size={22} strokeWidth={2.1} color="#8a98b3" />
      </div>
      <div style={styles.control}>{children}</div>
    </section>
  );
}

const styles: Record<string, CSSProperties> = {
  row: {
    background: "rgba(255, 255, 255, 0.76)",
    border: "1px solid rgba(255, 255, 255, 0.86)",
    borderRadius: 24,
    boxShadow: "0 14px 34px rgba(74, 103, 139, 0.1)",
    padding: "22px 24px 24px",
  },
  rowQuiet: {
    borderBottom: "1px solid rgba(255, 255, 255, 0.86)",
    paddingBottom: 24,
  },
  rowHead: {
    alignItems: "center",
    display: "flex",
    gap: 14,
  },
  iconWrap: {
    alignItems: "center",
    background: "rgba(37, 132, 255, 0.1)",
    borderRadius: 10,
    color: "#2584ff",
    display: "flex",
    flex: "0 0 auto",
    height: 48,
    justifyContent: "center",
    width: 48,
  },
  rowCopy: {
    flex: "1 1 auto",
    minWidth: 0,
  },
  rowTitle: {
    color: "#07152f",
    fontSize: 20,
    fontWeight: 850,
    lineHeight: 1.15,
    margin: 0,
  },
  rowHint: {
    color: "#8a98b3",
    fontSize: 14,
    lineHeight: 1.35,
    margin: "5px 0 0",
  },
  control: {
    marginTop: 16,
  },
};
