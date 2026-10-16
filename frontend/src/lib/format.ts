import { useTranslation } from "react-i18next";
import { parseISO, type ISODate } from "./dates";

const LOCALES: Record<string, string> = { en: "en-GB", ur: "ur-PK", ar: "ar" };

function utc(value: ISODate): Date {
  const { year, month, day } = parseISO(value);
  return new Date(Date.UTC(year, month - 1, day));
}

export function useFormat() {
  const { i18n } = useTranslation();
  const locale = LOCALES[i18n.language] ?? "en-GB";
  const format = (options: Intl.DateTimeFormatOptions) =>
    new Intl.DateTimeFormat(locale, { timeZone: "UTC", ...options });

  const regions = new Intl.DisplayNames([locale], { type: "region" });
  const languages = new Intl.DisplayNames([locale], { type: "language" });

  return {
    locale,
    language: (code: string) => languages.of(code.replace("_", "-")) ?? code,
    country: (code: string, fallback?: string) => {
      const name = regions.of(code);
      return name && name !== code ? name : (fallback ?? code);
    },
    monthYear: (year: number, month: number) =>
      format({ month: "long", year: "numeric" }).format(new Date(Date.UTC(year, month - 1, 1))),
    monthName: (month: number) =>
      format({ month: "long" }).format(new Date(Date.UTC(2027, month - 1, 1))),
    // 2027-03-22 is a Monday, so Python weekday n is that date plus n days.
    weekday: (pythonDay: number, width: "short" | "narrow" | "long" = "short") =>
      format({ weekday: width }).format(new Date(Date.UTC(2027, 2, 22 + pythonDay))),
    longDate: (value: ISODate) =>
      format({ weekday: "long", day: "numeric", month: "long", year: "numeric" }).format(
        utc(value),
      ),
    shortDate: (value: ISODate) =>
      format({ day: "numeric", month: "short", year: "numeric" }).format(utc(value)),
    dayNumber: (value: ISODate) => format({ day: "numeric" }).format(utc(value)),
  };
}
