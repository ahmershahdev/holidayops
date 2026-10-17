// The same `theme` cookie the server-rendered pages use (backend/apps/public/theme.py), so a choice
// made on either side of the site applies everywhere. No cookie means "follow the device".

export type Theme = "light" | "dark" | "system";

export const THEMES: Theme[] = ["light", "system", "dark"];
const COOKIE = "theme";
const ONE_YEAR = 365 * 24 * 3600;

export function readTheme(cookie: string = document.cookie): Theme {
  const match = /(?:^|;\s*)theme=(light|dark)(?:;|$)/.exec(cookie);
  return match ? (match[1] as Theme) : "system";
}

export function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
}

export function saveTheme(theme: Theme): void {
  const value = theme === "system" ? "" : theme;
  const age = theme === "system" ? 0 : ONE_YEAR;
  document.cookie = `${COOKIE}=${value}; path=/; max-age=${age}; samesite=lax`;
  applyTheme(theme);
}
