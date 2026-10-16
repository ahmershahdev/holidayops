import { useTranslation } from "react-i18next";
import { type ISODate, monthMatrix } from "../../lib/dates";
import { useFormat } from "../../lib/format";
import { type DayResult, TONE_DOT, toneOf } from "./dayStatus";

type Props = {
  year: number;
  weekStart: number;
  days: ReadonlyMap<ISODate, DayResult>;
  onPickMonth: (month: number) => void;
  isHolidayVisible: (date: ISODate, name: string) => boolean;
};

export function YearView({ year, weekStart, days, onPickMonth, isHolidayVisible }: Props) {
  const { t } = useTranslation();
  const fmt = useFormat();

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
      {Array.from({ length: 12 }, (_, i) => i + 1).map((month) => {
        const weeks = monthMatrix(year, month, weekStart);
        const off = weeks
          .flat()
          .filter((d): d is ISODate => d !== null)
          .filter((d) => {
            const day = days.get(d);
            return day && !day.is_business_day && day.reason !== "weekend";
          }).length;
        return (
          <button
            key={month}
            type="button"
            onClick={() => onPickMonth(month)}
            aria-label={`${fmt.monthYear(year, month)}: ${t("calendar.daysOff", { count: off })}`}
            className="rounded-[var(--radius-card)] border border-line bg-surface p-3 text-start transition hover:border-accent"
          >
            <span className="mb-2 flex items-baseline justify-between">
              <span className="font-display text-base">{fmt.monthName(month)}</span>
              <span className="text-xs text-muted">{t("calendar.daysOff", { count: off })}</span>
            </span>
            <span aria-hidden className="grid grid-cols-7 gap-0.5">
              {weeks.flat().map((date, j) => {
                const day = date ? days.get(date) : undefined;
                const visible = Boolean(
                  date && day?.holidays.some((n) => isHolidayVisible(date, n)),
                );
                const tone = day ? toneOf(day, visible) : "workday";
                return (
                  <span
                    key={date ?? `blank-${j}`}
                    className={`aspect-square rounded-[3px] ${date ? TONE_DOT[tone] : ""}`}
                  />
                );
              })}
            </span>
          </button>
        );
      })}
    </div>
  );
}
