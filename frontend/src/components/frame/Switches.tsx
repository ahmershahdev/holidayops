import { useState } from "react";
import { useTranslation } from "react-i18next";
import { changeLanguage, currentLanguage, type Language, LANGUAGES } from "../../i18n";
import { readTheme, saveTheme, type Theme, THEMES } from "../../lib/theme";

const LABELS: Record<Language, string> = { en: "EN", ur: "اردو", ar: "عربي" };

const segment = (active: boolean, dark: boolean) =>
  `inline-grid h-8 min-w-8 place-items-center rounded-full px-2 text-xs font-semibold transition-colors ${
    active
      ? dark
        ? "bg-[#0f3a3a] text-[#e6edf7]"
        : "bg-accent-soft text-ink"
      : dark
        ? "text-[#a3b3c9] hover:text-[#e6edf7]"
        : "text-muted hover:text-ink"
  }`;

const group = (dark: boolean) =>
  `inline-flex gap-0.5 rounded-full border p-[3px] ${dark ? "border-[#24375c] bg-[#111d36]" : "border-line bg-surface"}`;

const ICONS: Record<Theme, string> = {
  light:
    "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4",
  system: "M5 4h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zM8 20h8M12 16v4",
  dark: "M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z",
};

export function Switches({ dark = false }: { dark?: boolean }) {
  const { t } = useTranslation();
  const [theme, setTheme] = useState<Theme>(readTheme);
  const language = currentLanguage();

  function pick(next: Theme) {
    saveTheme(next);
    setTheme(next);
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className={group(dark)} role="group" aria-label={t("nav.language")}>
        {LANGUAGES.map((l) => (
          <button
            key={l.code}
            type="button"
            lang={l.code}
            aria-pressed={language === l.code}
            className={segment(language === l.code, dark)}
            onClick={() => void changeLanguage(l.code)}
          >
            {LABELS[l.code]}
          </button>
        ))}
      </div>
      <div className={group(dark)} role="group" aria-label={t("theme.label")}>
        {THEMES.map((option) => (
          <button
            key={option}
            type="button"
            aria-pressed={theme === option}
            title={t(`theme.${option}`)}
            className={segment(theme === option, dark)}
            onClick={() => pick(option)}
          >
            <svg
              viewBox="0 0 24 24"
              aria-hidden="true"
              className="size-4 fill-none stroke-current"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d={ICONS[option]} />
            </svg>
            <span className="sr-only">{t(`theme.${option}`)}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
