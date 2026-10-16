import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { Link, useParams } from "react-router";
import { api, type Schemas, unwrap } from "../api/client";
import { CheckResultView } from "../components/CheckResultView";
import { HolidayTable } from "../components/HolidayTable";
import { Button, Card, ErrorText, Field, Input, Select } from "../components/ui";

const KINDS: { value: Schemas["CustomDayKindEnum"]; label: string }[] = [
  { value: "closure", label: "Closure (day off)" },
  { value: "half_day", label: "Half day" },
  { value: "working_day", label: "Extra working day" },
];

export function CalendarPage() {
  const { org = "", id = "" } = useParams();
  const client = useQueryClient();
  const [year, setYear] = useState(new Date().getFullYear());
  const [checkDate, setCheckDate] = useState(new Date().toISOString().slice(0, 10));
  const [day, setDay] = useState({
    date: "",
    name: "",
    kind: "closure" as Schemas["CustomDayKindEnum"],
  });
  const daysPath = { params: { path: { org_slug: org, calendar_id: id } } };

  const calendar = useQuery({
    queryKey: ["calendar", org, id],
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/orgs/{org_slug}/calendars/{id}/", {
          params: { path: { org_slug: org, id } },
        }),
      ),
  });
  const holidays = useQuery({
    queryKey: ["calendar-holidays", id, year],
    queryFn: () =>
      unwrap(api.GET("/api/v1/holidays/", { params: { query: { calendar: id, year } } })),
  });
  const check = useQuery({
    queryKey: ["calendar-check", id, checkDate],
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/business-days/check/", {
          params: { query: { calendar: id, date: checkDate } },
        }),
      ),
    enabled: Boolean(checkDate),
  });
  const customDays = useQuery({
    queryKey: ["custom-days", id, year],
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/orgs/{org_slug}/calendars/{calendar_id}/custom-days/", {
          params: { ...daysPath.params, query: { year } },
        }),
      ),
  });

  const refresh = () =>
    Promise.all(
      ["custom-days", "calendar-holidays", "calendar-check"].map((key) =>
        client.invalidateQueries({ queryKey: [key, id] }),
      ),
    );
  const addDay = useMutation({
    mutationFn: () =>
      unwrap(
        api.POST("/api/v1/orgs/{org_slug}/calendars/{calendar_id}/custom-days/", {
          ...daysPath,
          body: day,
        }),
      ),
    onSuccess: () => {
      setDay({ ...day, date: "", name: "" });
      return refresh();
    },
  });
  const removeDay = useMutation({
    mutationFn: (dayId: number) =>
      unwrap(
        api.DELETE("/api/v1/orgs/{org_slug}/calendars/{calendar_id}/custom-days/{id}/", {
          params: { path: { org_slug: org, calendar_id: id, id: dayId } },
        }),
      ),
    onSuccess: refresh,
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    addDay.mutate();
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link to={`/app/${org}`} className="text-sm text-teal-700 hover:underline">
          ← Back
        </Link>
        <h1 className="text-2xl font-bold text-slate-900">{calendar.data?.name}</h1>
        <p className="text-slate-600">
          {calendar.data?.sources.map((s) => s.country).join(" + ")}
          {calendar.data?.weekend && ` · custom weekend`}
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card title="Check a date">
          <Input type="date" value={checkDate} onChange={(e) => setCheckDate(e.target.value)} />
          <div className="mt-3">{check.data && <CheckResultView result={check.data} />}</div>
          <ErrorText error={check.error} />
        </Card>

        <Card title="Add a company day">
          <form onSubmit={onSubmit} className="flex flex-col gap-3">
            <div className="grid grid-cols-2 gap-3">
              <Field label="Date">
                <Input
                  type="date"
                  required
                  value={day.date}
                  onChange={(e) => setDay({ ...day, date: e.target.value })}
                />
              </Field>
              <Field label="Kind">
                <Select
                  value={day.kind}
                  onChange={(e) =>
                    setDay({ ...day, kind: e.target.value as Schemas["CustomDayKindEnum"] })
                  }
                >
                  {KINDS.map((k) => (
                    <option key={k.value} value={k.value}>
                      {k.label}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>
            <Field label="Name">
              <Input
                required
                value={day.name}
                onChange={(e) => setDay({ ...day, name: e.target.value })}
              />
            </Field>
            <Button type="submit" disabled={addDay.isPending}>
              Add
            </Button>
            <ErrorText error={addDay.error ?? removeDay.error} />
          </form>
          {customDays.data && customDays.data.results.length > 0 && (
            <ul className="mt-4 divide-y divide-slate-100 text-sm">
              {customDays.data.results.map((d) => (
                <li key={d.id} className="flex items-center justify-between py-2">
                  <span>
                    <span className="font-mono">{d.date}</span> {d.name}{" "}
                    <span className="text-slate-500">({d.kind.replace("_", " ")})</span>
                  </span>
                  <Button variant="danger" onClick={() => removeDay.mutate(d.id)}>
                    Delete
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card
        title={
          <span className="flex items-center gap-3">
            Merged holidays in
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
