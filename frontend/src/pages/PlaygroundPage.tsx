import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api, unwrap } from "../api/client";
import { CheckResultView } from "../components/CheckResultView";
import { CountrySelect, useCountries } from "../components/CountrySelect";
import { HolidayTable } from "../components/HolidayTable";
import { Card, ErrorText, Field, Input, Select } from "../components/ui";

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function PlaygroundPage() {
  const [country, setCountry] = useState("PK");
  const [language, setLanguage] = useState("");
  const [date, setDate] = useState(today());
  const [days, setDays] = useState(5);
  const [year, setYear] = useState(new Date().getFullYear());
  const info = useCountries().data?.find((c) => c.code === country);
  const lang = language && info?.languages.includes(language) ? language : undefined;

  const check = useQuery({
    queryKey: ["check", country, date],
    queryFn: () =>
      unwrap(api.GET("/api/v1/business-days/check/", { params: { query: { country, date } } })),
    enabled: Boolean(date),
  });
  const add = useQuery({
    queryKey: ["add", country, date, days],
    queryFn: () =>
      unwrap(api.GET("/api/v1/business-days/add/", { params: { query: { country, date, days } } })),
    enabled: Boolean(date),
  });
  const holidays = useQuery({
    queryKey: ["holidays", country, year, lang],
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/holidays/", { params: { query: { country, year, language: lang } } }),
      ),
  });

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Is it a working day?</h1>
        <p className="mt-1 text-slate-600">
          Live answers from the HolidayOps API for {info?.name ?? country}, using its own weekend
          {info && ` (${info.weekend.map((d) => WEEKDAYS[d]).join("–")})`}.
        </p>
      </div>

      <Card>
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="Country">
            <CountrySelect value={country} onChange={(c) => (setCountry(c), setLanguage(""))} />
          </Field>
          <Field label="Date">
            <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          </Field>
          <Field label="Holiday names in">
            <Select value={language} onChange={(e) => setLanguage(e.target.value)}>
              <option value="">Default ({info?.default_language ?? "…"})</option>
              {info?.languages.map((l) => (
                <option key={l} value={l}>
                  {l}
                </option>
              ))}
            </Select>
          </Field>
        </div>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        <Card title={`Check ${date}`}>
          {check.data && <CheckResultView result={check.data} />}
          <ErrorText error={check.error} />
        </Card>
        <Card title="Add working days">
          <div className="flex items-end gap-3">
            <Field label="Days (negative goes back)">
              <Input
                type="number"
                min={-1000}
                max={1000}
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
              />
            </Field>
          </div>
          {add.data && (
            <p className="mt-3 text-slate-700">
              {days} working days from {date} is{" "}
              <strong className="font-mono">{add.data.result}</strong>
            </p>
          )}
          <ErrorText error={add.error} />
        </Card>
      </div>

      <Card
        title={
          <span className="flex items-center gap-3">
            Holidays in
            <Input
              type="number"
              className="w-28"
              min={1970}
              max={2100}
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
            />
          </span>
        }
      >
        <div dir="auto">{holidays.data && <HolidayTable holidays={holidays.data.holidays} />}</div>
        <ErrorText error={holidays.error} />
      </Card>
    </div>
  );
}
