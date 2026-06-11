import { Home, Lightbulb, Package, User } from "lucide-react";
import { NavLink } from "react-router-dom";
import { useLanguage } from "../../lib/language";
import styles from "./BottomNav.module.css";

const navItems = [
  { to: "/", label: "home", icon: Home, end: true },
  { to: "/inventory", label: "inventory", icon: Package },
  { to: "/advice", label: "advice", icon: Lightbulb },
  { to: "/profile", label: "profile", icon: User },
] as const;

export function BottomNav() {
  const { t } = useLanguage();

  return (
    <nav className={styles.nav} aria-label="Primary">
      {navItems.map((item) => {
        const Icon = item.icon;
        return (
        <NavLink
          key={item.to}
          to={item.to}
          end={"end" in item ? item.end : undefined}
          className={({ isActive }) =>
            isActive ? `${styles.item} ${styles.active}` : styles.item
          }
        >
          <Icon className={styles.icon} aria-hidden="true" strokeWidth={2.2} />
          <span>{t(item.label)}</span>
        </NavLink>
        );
      })}
    </nav>
  );
}
