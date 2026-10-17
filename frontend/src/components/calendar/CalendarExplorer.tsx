import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, unwrap } from "../../api/client";
import { type Target, useDayRange, useHolidays } from "../../api/hooks";
import { addMonths, daysInMonth, type ISODate, parseISO, todayISO, toISO } from "../../lib/dates";
import { useFormat } from "../../lib/format";
import { Button, Card, ErrorText } from "../ui";
import { DayPanel } from "./DayPanel";
import { HolidayList } from "./HolidayList";
import { Legend } from "./Legend";
import { MonthGrid } from "./MonthGrid";
import { YearView } from "./YearView";

type View = "month" | "year" | "list";

type Props = {
  target: Target;
  weekStart: number;
  language?: string;
  sources?: string[];
  editor?: { org: string; calendar: string; canWrite: boolean };
};

export function CalendarExplorer({ target, weekStart, language, sources = [], editor }: Props) {
  const { t } = useTranslation();
  const fmt = useFormat();
  const today = todayISO();
  const [view, setView] = useState<View>("month");
  const [selected, setSelected] = useState<ISODate>(today);
  const [hidden, setHidden] = useState<ReadonlySet<string>>(new Set());
  const { year, month } = parseISO(selected);

  const monthStart = toISO(year, month, 1);
  const monthEnd = toISO(year, month, daysInMonth(year, month));
  const range = useDayRange(
    target,
    view === "month" ? monthStart : toISO(year, 1, 1),
    view === "month" ? monthEnd : toISO(year, 12, 31),
    language,
  );
  const holidays = useHolidays(target, year, language);
  const customDays = useQuery({
    queryKey: ["custom-days", editor?.calendar, year],
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/orgs/{org_slug}/calendars/{calendar_id}/custom-days/", {
          params: {
            path: { org_slug: editor?.org ?? "", calendar_id: editor?.calendar ?? "" },
            query: { year },
          },
        }),
      ),
    enabled: Boolean(editor),
  });

  const days = useMemo(() => new Map((range.data ?? []).map((d) => [d.date, d])), [range.data]);
  const holidaySources = useMemo(() => {
    const map = new Map<string, string[]>();
    for (const h of holidays.data?.holidays ?? []) map.set(`${h.date}|${h.name}`, h.sources);
    return map;
  }, [holidays.data]);

  const isHolidayVisible = (date: ISODate, name: string) => {
    const origin = holidaySources.get(`${date}|${name}`);
    return !origin || origin.length === 0 || origin.some((s) => !hidden.has(s));
  };

  function move(delta: number) {
    if (view === "month") {
      const next = addMonths(year, month, delta);
      setSelected(toISO(next.year, next.month, 1));
    } else {
      setSelected(toISO(year + delta, 1, 1));
    }
  }

  function toggleSource(source: string) {
    const next = new Set(hidden);
    if (next.has(source)) next.delete(source);
    else next.add(source);
    setHidden(next);
  }

  const visibleHolidays = (holidays.data?.holidays ?? []).filter(
    (h) => h.sources.length === 0 || h.sources.some((s) => !hidden.has(s)),
  );
  const custom = customDays.data?.results.find((d) => d.date === selected);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1">
          <Button variant="ghost" aria-label={t("calendar.previous")} onClick={() => move(-1)}>
            <span aria-hidden className="inline-block rtl:rotate-180">
              ←
            </span>
          </Button>
          <Button variant="ghost" onClick={() => setSelected(today)}>
            {t("calendar.today")}
          </Button>
          <Button variant="ghost" aria-label={t("calendar.next")} onClick={() => move(1)}>
            <span aria-hidden className="inline-block rtl:rotate-180">
              →
            </span>
          </Button>
        </div>
        <h2 className="font-display text-2xl" aria-live="polite">
          {view === "month" ? fmt.monthYear(year, month) : year}
        </h2>
        <div
          role="tablist"
          aria-label={t("calendar.view")}
          className="ms-auto flex rounded-lg border border-line bg-surface p-0.5"
        >
          {(["month", "year", "list"] as const).map((v) => (
            <button
              key={v}
              type="button"
              role="tab"
              aria-selected={view === v}
              onClick={() => setView(v)}
              className={`rounded-md px-3 py-1.5 text-sm ${view === v ? "bg-accent text-on-accent" : "text-muted hover:text-ink"}`}
            >
              {t(`calendar.views.${v}`)}
            </button>
          ))}
        </div>
      </div>

      {sources.length > 1 && (
        <fieldset className="flex flex-wrap items-center gap-2">
          <legend className="me-2 text-sm text-muted">{t("calendar.showHolidaysFrom")}</legend>
          {sources.map((s) => (
            <label
              key={s}
              className="flex cursor-pointer items-center gap-1.5 rounded-full border border-line bg-surface px-3 py-1 text-sm has-[:checked]:border-accent has-[:checked]:bg-accent-soft"
            >
              <input
                type="checkbox"
                className="accent-accent"
                checked={!hidden.has(s)}
                onChange={() => toggleSource(s)}
              />
              {s}
            </label>
          ))}
        </fieldset>
      )}

      <ErrorText error={range.error ?? holidays.error} />

      {view === "list" ? (
        <Card>
          <HolidayList holidays={visibleHolidays} />
        </Card>
      ) : view === "year" ? (
        <YearView
          year={year}
          weekStart={weekStart}
          days={days}
          isHolidayVisible={isHolidayVisible}
          onPickMonth={(m) => {
            setSelected(toISO(year, m, 1));
            setView("month");
          }}
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-[1fr_20rem]">
          <MonthGrid
            year={year}
            month={month}
            weekStart={weekStart}
            days={days}
            selected={selected}
            today={today}
            onSelect={setSelected}
            isHolidayVisible={isHolidayVisible}
          />
          <Card>
            <DayPanel
              date={selected}
              day={days.get(selected)}
              editor={editor && { ...editor, custom }}
            />
          </Card>
        </div>
      )}
      <Legend />
    </div>
  );
}
