import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api, unwrap } from "../api/client";
import { useCountries } from "../api/hooks";
import { CalendarExplorer } from "../components/calendar/CalendarExplorer";
import { CountryPicker } from "../components/CountryPicker";
import { Card, ErrorText, Field, Input, PageHeader } from "../components/ui";
import { currentLanguage, holidayLanguage } from "../i18n";
import { todayISO, weekStartFor } from "../lib/dates";
import { useFormat } from "../lib/format";

export function PlaygroundPage() {
  const { t } = useTranslation();
  const fmt = useFormat();
  const [country, setCountry] = useState("PK");
  const [start, setStart] = useState(todayISO());
  const [days, setDays] = useState(5);
  const info = useCountries().data?.find((c) => c.code === country);
  const language = info
    ? holidayLanguage(currentLanguage(), info.languages, info.default_language)
    : undefined;
  const weekend = info?.weekend ?? [5, 6];

  const add = useQuery({
    queryKey: ["add", country, start, days],
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/business-days/add/", {
          params: { query: { country, date: start, days } },
        }),
      ),
    enabled: Boolean(start) && Number.isInteger(days),
  });

  return (
    <>
      <PageHeader
        title={t("playground.title")}
        subtitle={t("playground.subtitle", {
          country: fmt.country(country, info?.name),
          weekend: weekend.map((d) => fmt.weekday(d, "long")).join(t("common.and")),
        })}
        actions={
          <div className="w-full sm:w-64">
            <CountryPicker value={country} onChange={setCountry} label={t("playground.country")} />
          </div>
        }
      />

      <CalendarExplorer
        key={country}
        target={{ country }}
        weekStart={weekStartFor(weekend)}
        language={language}
      />

      <Card title={t("playground.addTitle")}>
        <div className="flex flex-wrap items-end gap-4">
          <Field label={t("playground.from")}>
            <Input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
          </Field>
          <Field label={t("playground.days")} hint={t("playground.daysHint")}>
            <Input
              type="number"
              min={-1000}
              max={1000}
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="w-32"
            />
          </Field>
          {add.data && (
            <p className="pb-2 text-lg">
              {t("playground.addResult", { count: days })}{" "}
              <strong className="font-display">{fmt.longDate(add.data.result)}</strong>
            </p>
          )}
        </div>
        <ErrorText error={add.error} />
      </Card>
    </>
  );
}
