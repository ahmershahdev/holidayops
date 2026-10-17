import { type KeyboardEvent, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import {
  addDays,
  type ISODate,
  monthMatrix,
  orderedWeekdays,
  pythonWeekday,
} from "../../lib/dates";
import { useFormat } from "../../lib/format";
import { type DayResult, TONE_CELL, toneOf } from "./dayStatus";

type Props = {
  year: number;
  month: number;
  weekStart: number;
  days: ReadonlyMap<ISODate, DayResult>;
  selected: ISODate;
  today: ISODate;
  onSelect: (date: ISODate) => void;
  isHolidayVisible: (date: ISODate, name: string) => boolean;
};

const KEY_STEPS: Record<string, number> = {
  ArrowUp: -7,
  ArrowDown: 7,
  ArrowLeft: -1,
  ArrowRight: 1,
};

export function MonthGrid(props: Props) {
  const { year, month, weekStart, days, selected, today, onSelect, isHolidayVisible } = props;
  const { t, i18n } = useTranslation();
  const fmt = useFormat();
  const grid = useRef<HTMLDivElement>(null);
  const navigating = useRef(false);
  const rtl = i18n.dir() === "rtl";

  useEffect(() => {
    if (!navigating.current) return;
    navigating.current = false;
    grid.current?.querySelector<HTMLElement>('[tabindex="0"]')?.focus();
  }, [selected, year, month]);

  function onKeyDown(event: KeyboardEvent) {
    let step = KEY_STEPS[event.key];
    if (step !== undefined && rtl && Math.abs(step) === 1) step = -step;
    if (event.key === "PageUp") step = -28;
    if (event.key === "PageDown") step = 28;
    const column = (pythonWeekday(selected) - weekStart + 7) % 7;
    if (event.key === "Home") step = -column;
    if (event.key === "End") step = 6 - column;
    if (step === undefined) return;
    event.preventDefault();
    navigating.current = true;
    onSelect(addDays(selected, step));
  }

  return (
    <div
      ref={grid}
      role="grid"
      aria-label={fmt.monthYear(year, month)}
      onKeyDown={onKeyDown}
      className="overflow-hidden rounded-[var(--radius-card)] border border-line bg-line"
    >
      <div role="row" className="grid grid-cols-7 gap-px">
        {orderedWeekdays(weekStart).map((d) => (
          <div
            key={d}
            role="columnheader"
            className="bg-paper py-2 text-center text-xs font-medium tracking-wide text-muted uppercase"
          >
            <abbr title={fmt.weekday(d, "long")} className="no-underline">
              {fmt.weekday(d, "short")}
            </abbr>
          </div>
        ))}
      </div>
      {monthMatrix(year, month, weekStart).map((week, i) => (
        <div role="row" key={i} className="grid grid-cols-7 gap-px border-t border-line">
          {week.map((date, j) => {
            if (!date) return <div role="gridcell" key={j} className="bg-paper" aria-hidden />;
            const day = days.get(date);
            const visibleNames = day?.holidays.filter((n) => isHolidayVisible(date, n)) ?? [];
            const tone = day ? toneOf(day, visibleNames.length > 0) : "workday";
            const status = day ? t(`reason.${day.reason}`) : "";
            const label = [fmt.longDate(date), status, ...visibleNames].filter(Boolean).join(", ");
            const isSelected = date === selected;
            return (
              <button
                type="button"
                role="gridcell"
                key={date}
                tabIndex={isSelected ? 0 : -1}
                aria-selected={isSelected}
                aria-current={date === today ? "date" : undefined}
                aria-label={label}
                onClick={() => onSelect(date)}
                className={`relative flex min-h-16 flex-col items-start gap-1 p-1.5 text-start transition-colors sm:min-h-24 sm:p-2 ${TONE_CELL[tone]} ${isSelected ? "z-10 outline-2 -outline-offset-2 outline-accent" : "hover:brightness-[0.97]"}`}
              >
                <span
                  className={`grid size-7 place-items-center rounded-full text-sm font-medium ${date === today ? "bg-accent text-on-accent" : ""}`}
                >
                  {fmt.dayNumber(date)}
                </span>
                {visibleNames[0] && (
                  <span className="line-clamp-2 hidden text-xs leading-snug sm:block">
                    {visibleNames[0]}
                  </span>
                )}
                {tone === "moved" && day && (
                  <span className="hidden text-[11px] font-semibold sm:block">
                    {t(`reason.${day.reason}`)}
                  </span>
                )}
                {day?.half_day && (
                  <span className="hidden text-[11px] font-semibold sm:block">
                    {t("reason.half_day")}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      ))}
    </div>
  );
}
