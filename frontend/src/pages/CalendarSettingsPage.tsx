import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router";
import { api, type Schemas, unwrap } from "../api/client";
import { useCountries } from "../api/hooks";
import { type Source, SourcesEditor } from "../components/SourcesEditor";
import { Button, Card, ErrorText, Field, Input, PageHeader, Select } from "../components/ui";
import { useFormat } from "../lib/format";

export function CalendarSettingsPage() {
  const { org = "", id = "" } = useParams();
  const calendar = useQuery({
    queryKey: ["calendar", org, id],
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/orgs/{org_slug}/calendars/{id}/", {
          params: { path: { org_slug: org, id } },
        }),
      ),
  });
  if (calendar.error) return <ErrorText error={calendar.error} />;
  if (!calendar.data) return null;
  return <SettingsForm key={calendar.data.updated_at} org={org} calendar={calendar.data} />;
}

function SettingsForm({ org, calendar }: { org: string; calendar: Schemas["Calendar"] }) {
  const { t } = useTranslation();
  const fmt = useFormat();
  const client = useQueryClient();
  const navigate = useNavigate();
  const countries = useCountries().data ?? [];
  const [name, setName] = useState(calendar.name);
  const [isPublic, setIsPublic] = useState(Boolean(calendar.is_public));
  const [language, setLanguage] = useState(calendar.language ?? "");
  const [weekend, setWeekend] = useState<number[] | null>(calendar.weekend ?? null);
  const [sources, setSources] = useState<Source[]>(calendar.sources);
  const [confirmDelete, setConfirmDelete] = useState("");
  const path = { params: { path: { org_slug: org, id: calendar.id } } };

  const languages = [
    ...new Set(
      sources.flatMap((s) => countries.find((c) => c.code === s.country)?.languages ?? []),
    ),
  ].sort();

  const save = useMutation({
    mutationFn: () =>
      unwrap(
        api.PATCH("/api/v1/orgs/{org_slug}/calendars/{id}/", {
          ...path,
          body: { name, is_public: isPublic, language, weekend, sources },
        }),
      ),
    onSuccess: () => client.invalidateQueries(),
  });
  const remove = useMutation({
    mutationFn: () => unwrap(api.DELETE("/api/v1/orgs/{org_slug}/calendars/{id}/", path)),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: ["calendars", org] });
      navigate(`/app/${org}`);
    },
  });

  function toggleDay(day: number) {
    const current = weekend ?? [];
    setWeekend(current.includes(day) ? current.filter((d) => d !== day) : [...current, day].sort());
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    save.mutate();
  }

  return (
    <>
      <PageHeader
        title={t("settings.calendarTitle", { name: calendar.name })}
        actions={
          <Link
            to={`/app/${org}/calendars/${calendar.id}`}
            className="rounded-lg border border-line bg-surface px-4 py-2 text-sm hover:border-accent"
          >
            {t("common.back")}
          </Link>
        }
      />
      <form onSubmit={onSubmit} className="flex flex-col gap-6">
        <Card>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t("settings.name")}>
              <Input
                required
                maxLength={120}
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </Field>
            <Field label={t("settings.language")} hint={t("settings.languageHint")}>
              <Select value={language} onChange={(e) => setLanguage(e.target.value)}>
                <option value="">{t("settings.countryDefault")}</option>
                {languages.map((l) => (
                  <option key={l} value={l}>
                    {fmt.language(l)}
                  </option>
                ))}
              </Select>
            </Field>
          </div>
          <label className="mt-4 flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              className="accent-accent"
              checked={isPublic}
              onChange={(e) => setIsPublic(e.target.checked)}
            />
            {t("settings.public")}
          </label>
        </Card>

        <Card>
          <SourcesEditor value={sources} onChange={setSources} />
        </Card>

        <Card title={t("settings.weekend")}>
          <label className="mb-3 flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              className="accent-accent"
              checked={weekend === null}
              onChange={(e) => setWeekend(e.target.checked ? null : [5, 6])}
            />
            {t("settings.weekendFromSource")}
          </label>
          {weekend !== null && (
            <div className="flex flex-wrap gap-2" role="group" aria-label={t("settings.weekend")}>
              {[0, 1, 2, 3, 4, 5, 6].map((d) => (
                <label
                  key={d}
                  className="flex cursor-pointer items-center gap-1.5 rounded-full border border-line px-3 py-1 text-sm has-[:checked]:border-accent has-[:checked]:bg-accent-soft"
                >
                  <input
                    type="checkbox"
                    className="accent-accent"
                    checked={weekend.includes(d)}
                    onChange={() => toggleDay(d)}
                  />
                  {fmt.weekday(d, "long")}
                </label>
              ))}
            </div>
          )}
        </Card>

        <div className="flex items-center gap-3">
          <Button type="submit" disabled={save.isPending}>
            {t("common.save")}
          </Button>
          {save.isSuccess && <span className="text-sm text-workday">{t("common.saved")}</span>}
          <ErrorText error={save.error} />
        </div>
      </form>

      <Card title={t("settings.dangerZone")}>
        <p className="mb-3 text-sm text-muted">
          {t("settings.deleteHint", { name: calendar.name })}
        </p>
        <div className="flex flex-wrap gap-2">
          <Input
            aria-label={t("settings.confirmName")}
            value={confirmDelete}
            onChange={(e) => setConfirmDelete(e.target.value)}
            placeholder={calendar.name}
          />
          <Button
            variant="danger"
            disabled={confirmDelete !== calendar.name || remove.isPending}
            onClick={() => remove.mutate()}
          >
            {t("settings.deleteCalendar")}
          </Button>
        </div>
        <ErrorText error={remove.error} />
      </Card>
    </>
  );
}
