import { useQuery } from "@tanstack/react-query";
import { type KeyboardEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, unwrap } from "../api/client";
import { ltr, niceMax } from "../lib/chart";
import { useFormat } from "../lib/format";
import { Card, ErrorText } from "./ui";

export function UsageCard({ org }: { org: string }) {
  const { t, i18n } = useTranslation();
  const fmt = useFormat();
  const [active, setActive] = useState<number | null>(null);
  const [showTable, setShowTable] = useState(false);
  const usage = useQuery({
    queryKey: ["usage", org],
    queryFn: () =>
      unwrap(api.GET("/api/v1/orgs/{org_slug}/usage/", { params: { path: { org_slug: org } } })),
  });

  if (usage.error) return <ErrorText error={usage.error} />;
  if (!usage.data) return null;

  const data = usage.data;
  const days = data.days;
  const first = days[0];
  const last = days[days.length - 1];
  if (!first || !last) return null;
  const number = new Intl.NumberFormat(i18n.language);
  const compact = new Intl.NumberFormat(i18n.language, { notation: "compact" });
  const top = niceMax(Math.max(0, ...days.map((d) => d.requests)));
  // A non-zero day stays at least 2% tall so it never looks like zero.
  const barHeight = (requests: number) => (requests ? Math.max(2, (requests / top) * 100) : 0);
  const used = Math.min(1, data.used_this_month / data.monthly_quota);
  const day = active === null ? null : days[active];

  function onKeyDown(event: KeyboardEvent) {
    const forward = document.documentElement.dir === "rtl" ? "ArrowLeft" : "ArrowRight";
    const back = forward === "ArrowRight" ? "ArrowLeft" : "ArrowRight";
    if (event.key !== forward && event.key !== back) return;
    event.preventDefault();
    const current = active ?? days.length - 1;
    const next = current + (event.key === forward ? 1 : -1);
    setActive(Math.min(days.length - 1, Math.max(0, next)));
  }

  return (
    <Card title={t("usage.title")}>
      <div className="mb-5">
        <div className="mb-1 flex flex-wrap justify-between gap-2 text-sm">
          <span>
            {t("usage.quota", {
              used: number.format(data.used_this_month),
              quota: number.format(data.monthly_quota),
            })}
          </span>
          <span className="text-muted">
            {t("usage.plan", { plan: t(`usage.plans.${data.plan}`), rate: ltr(data.rate) })}
          </span>
        </div>
        <div
          role="meter"
          aria-label={t("usage.quotaLabel")}
          aria-valuemin={0}
          aria-valuemax={data.monthly_quota}
          aria-valuenow={data.used_this_month}
          className="h-2 overflow-hidden rounded-full bg-line"
        >
          <div
            className={`h-full rounded-full ${used >= 0.9 ? "bg-holiday" : "bg-accent"}`}
            style={{ width: `${used * 100}%` }}
          />
        </div>
      </div>

      <div className="flex items-baseline justify-between gap-2">
        <h3 className="text-sm font-medium">{t("usage.chartTitle", { count: days.length })}</h3>
        <button
          type="button"
          className="text-xs text-accent underline"
          aria-expanded={showTable}
          onClick={() => setShowTable(!showTable)}
        >
          {showTable ? t("usage.hideTable") : t("usage.showTable")}
        </button>
      </div>

      <div className="relative mt-2">
        <div className="flex">
          <div className="flex h-32 w-8 shrink-0 flex-col justify-between pe-1 text-end text-[10px] text-muted">
            <span>{compact.format(top)}</span>
            <span>0</span>
          </div>
          <div
            role="group"
            tabIndex={0}
            aria-label={t("usage.chartLabel")}
            onKeyDown={onKeyDown}
            onBlur={() => setActive(null)}
            onPointerLeave={() => setActive(null)}
            className="relative flex h-32 flex-1 items-end gap-[2px] border-b border-line focus-visible:outline-2"
          >
            <div className="pointer-events-none absolute inset-x-0 top-0 border-t border-dashed border-line" />
            {days.map((d, i) => (
              <div
                key={d.date}
                onPointerEnter={() => setActive(i)}
                className="flex h-full flex-1 items-end"
              >
                <div
                  className={`w-full rounded-t-[4px] ${active === i ? "bg-accent/70" : "bg-accent"}`}
                  style={{ height: `${barHeight(d.requests)}%` }}
                />
              </div>
            ))}
            {day && active !== null && (
              <div
                role="status"
                className="pointer-events-none absolute z-10 -translate-x-1/2 rounded-lg border border-line bg-surface px-3 py-2 text-xs whitespace-nowrap shadow-sm rtl:translate-x-1/2"
                style={{
                  insetInlineStart: `${((active + 0.5) / days.length) * 100}%`,
                  bottom: `calc(${barHeight(day.requests)}% + 6px)`,
                }}
              >
                <p className="font-medium">{fmt.shortDate(day.date)}</p>
                <p>{t("usage.requests", { count: day.requests })}</p>
                {day.failed > 0 && (
                  <p className="text-muted">{t("usage.failed", { count: day.failed })}</p>
                )}
              </div>
            )}
          </div>
        </div>
        <div className="ms-8 mt-1 flex justify-between text-[10px] text-muted">
          <span>{fmt.shortDate(first.date)}</span>
          <span>{fmt.shortDate(last.date)}</span>
        </div>
      </div>

      {showTable && (
        <table className="mt-4 w-full text-sm">
          <thead className="text-muted">
            <tr>
              <th className="py-1 text-start font-medium">{t("usage.date")}</th>
              <th className="py-1 text-end font-medium">{t("usage.requestsColumn")}</th>
              <th className="py-1 text-end font-medium">{t("usage.failedColumn")}</th>
            </tr>
          </thead>
          <tbody>
            {[...days].reverse().map((d) => (
              <tr key={d.date} className="border-t border-line">
                <td className="py-1">{fmt.shortDate(d.date)}</td>
                <td className="py-1 text-end tabular-nums">{number.format(d.requests)}</td>
                <td className="py-1 text-end tabular-nums">{number.format(d.failed)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}
