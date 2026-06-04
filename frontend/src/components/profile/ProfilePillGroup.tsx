import type { CSSProperties } from "react";

type ProfilePillGroupProps<T extends string> = {
  label: string;
  options: Array<{
    value: T;
    label: string;
  }>;
  value: T[];
  onChange: (value: T[]) => void;
};

export function ProfilePillGroup<T extends string>({
  label,
  options,
  value,
  onChange,
}: ProfilePillGroupProps<T>) {
  const selected = new Set(value);

  return (
    <div>
      <div style={styles.label}>{label}</div>
      <div style={styles.pills}>
        {options.map((option) => {
          const isActive = selected.has(option.value);

          return (
            <button
              key={option.value}
              type="button"
              onClick={() => {
                const next = isActive
                  ? value.filter((item) => item !== option.value)
                  : [...value, option.value];
                onChange(next);
              }}
              style={{
                ...styles.pill,
                ...(isActive ? styles.pillActive : undefined),
              }}
              aria-pressed={isActive}
            >
              {option.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  label: {
    color: "#697895",
    fontSize: 15,
    fontWeight: 700,
    marginBottom: 10,
  },
  pills: {
    display: "flex",
    flexWrap: "wrap",
    gap: 10,
  },
  pill: {
    appearance: "none",
    background: "rgba(255, 255, 255, 0.72)",
    border: "1px solid rgba(143, 164, 194, 0.22)",
    borderRadius: 9,
    color: "#697895",
    cursor: "pointer",
    font: "inherit",
    fontSize: 15,
    fontWeight: 800,
    minHeight: 40,
    padding: "0 16px",
    transition: "transform 140ms ease, background 140ms ease, color 140ms ease",
  },
  pillActive: {
    background: "#2584ff",
    borderColor: "#2584ff",
    color: "#ffffff",
    boxShadow: "0 12px 28px rgba(37, 132, 255, 0.22)",
  },
};
