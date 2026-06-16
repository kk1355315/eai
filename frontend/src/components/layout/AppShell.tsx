import { Outlet, useLocation } from "react-router-dom";
import { BottomNav } from "./BottomNav";
import { type TranslationKey, useLanguage } from "../../lib/language";
import styles from "./AppShell.module.css";

type PageTitle = {
  title: TranslationKey;
  subtitle?: TranslationKey;
};

const pageTitles: Record<string, PageTitle> = {
  "/": { title: "today", subtitle: "eatSmarter" },
  "/inventory": { title: "inventory" },
  "/advice": { title: "advice" },
  "/profile": { title: "profile" },
};

export function AppShell() {
  const { pathname } = useLocation();
  const { t } = useLanguage();
  const page = pageTitles[pathname] ?? pageTitles["/"];
  const pageClass =
    pathname === "/inventory"
      ? styles.inventoryPage
      : pathname === "/profile"
        ? styles.profilePage
        : pathname === "/"
          ? styles.homePage
          : "";

  return (
    <div className={styles.viewport}>
      <div className={styles.phoneFrame}>
        <main className={`${styles.content} ${pageClass}`} aria-label={t(page.title)}>
          <header className={styles.header}>
            <div>
              <h1 className={styles.title}>{t(page.title)}</h1>
              {page.subtitle ? <p className={styles.subtitle}>{t(page.subtitle)}</p> : null}
            </div>
            <LanguageButton />
          </header>
          <Outlet />
        </main>
        <div className={styles.bottomScrim} aria-hidden="true" />
        <BottomNav />
      </div>
    </div>
  );
}

function LanguageButton() {
  const { t, toggleLanguage } = useLanguage();

  return (
    <button
      aria-label="Switch language"
      className={styles.languageButton}
      onClick={toggleLanguage}
      type="button"
    >
      {t("languageToggle")}
    </button>
  );
}
