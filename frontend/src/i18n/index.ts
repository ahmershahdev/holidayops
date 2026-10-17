import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import ar from "./ar.json";
import en from "./en.json";
import ur from "./ur.json";

export const LANGUAGES = [
  { code: "en", label: "English", dir: "ltr" },
  { code: "ur", label: "اردو", dir: "rtl" },
  { code: "ar", label: "العربية", dir: "rtl" },
] as const;

export type Language = (typeof LANGUAGES)[number]["code"];

const STORAGE_KEY = "holidayops.language";

function isLanguage(value: string | null | undefined): value is Language {
  return LANGUAGES.some((l) => l.code === value);
}

function initialLanguage(): Language {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (isLanguage(saved)) return saved;
  } catch {
    // Storage can be unavailable (private mode); fall back to the browser language.
  }
  const browser = navigator.language.slice(0, 2);
  return isLanguage(browser) ? browser : "en";
}

export function applyDocumentLanguage(language: Language): void {
  const dir = LANGUAGES.find((l) => l.code === language)?.dir ?? "ltr";
  document.documentElement.lang = language;
  document.documentElement.dir = dir;
}

export function currentLanguage(): Language {
  return isLanguage(i18n.language) ? i18n.language : "en";
}

export async function changeLanguage(language: Language): Promise<void> {
  await i18n.changeLanguage(language);
  try {
    localStorage.setItem(STORAGE_KEY, language);
  } catch {
    // Not persisting is fine.
  }
}

export function holidayLanguage(
  ui: Language,
  supported: readonly string[],
  fallback: string | null | undefined,
): string | undefined {
  const preferences: Record<Language, string[]> = {
    en: ["en_US", "en_GB", "en"],
    ur: ["ur_PK", "ur"],
    ar: ["ar"],
  };
  if (ui === "en" && fallback?.startsWith("en")) return fallback;
  return (
    preferences[ui].find((code) => supported.includes(code)) ??
    supported.find((code) => code.startsWith(ui)) ??
    undefined
  );
}

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, ur: { translation: ur }, ar: { translation: ar } },
  lng: initialLanguage(),
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

applyDocumentLanguage(currentLanguage());
i18n.on("languageChanged", (language) => {
  if (isLanguage(language)) applyDocumentLanguage(language);
});

export default i18n;
