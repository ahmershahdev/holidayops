import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router";
import { api, unwrap } from "../api/client";
import { type Source, SourcesEditor } from "../components/SourcesEditor";
import { Badge, Button, Card, ErrorText, Field, Input, PageHeader } from "../components/ui";

function NewCalendarForm({ org }: { org: string }) {
  const { t } = useTranslation();
  const client = useQueryClient();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [sources, setSources] = useState<Source[]>([{ country: "PK" }]);
  const create = useMutation({
    mutationFn: () =>
      unwrap(
        api.POST("/api/v1/orgs/{org_slug}/calendars/", {
          params: { path: { org_slug: org } },
          body: { name, sources },
        }),
      ),
    onSuccess: async (calendar) => {
      await client.invalidateQueries({ queryKey: ["calendars", org] });
      navigate(`/app/${org}/calendars/${calendar.id}`);
    },
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    create.mutate();
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4">
      <Field label={t("org.calendarName")}>
        <Input required maxLength={120} value={name} onChange={(e) => setName(e.target.value)} />
      </Field>
      <SourcesEditor value={sources} onChange={setSources} />
      <div>
        <Button type="submit" disabled={create.isPending}>
          {t("org.createCalendar")}
        </Button>
      </div>
      <ErrorText error={create.error} />
    </form>
  );
}

export function OrgPage() {
  const { t } = useTranslation();
  const { org = "" } = useParams();
  const path = { params: { path: { org_slug: org } } };
  const detail = useQuery({
    queryKey: ["org", org],
    queryFn: () => unwrap(api.GET("/api/v1/orgs/{org_slug}/", path)),
  });
  const calendars = useQuery({
    queryKey: ["calendars", org],
    queryFn: () => unwrap(api.GET("/api/v1/orgs/{org_slug}/calendars/", path)),
  });
  const role = detail.data?.role ?? "viewer";

  if (detail.error) return <ErrorText error={detail.error} />;

  return (
    <>
      <PageHeader
        title={detail.data?.name}
        subtitle={<Badge tone="neutral">{t(`roles.${role}`)}</Badge>}
        actions={
          <Link
            to={`/app/${org}/settings`}
            className="rounded-lg border border-line bg-surface px-4 py-2 text-sm hover:border-accent"
          >
            {t("org.settings")}
          </Link>
        }
      />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card title={t("org.calendars")}>
          {calendars.data?.results.length === 0 && (
            <p className="text-sm text-muted">{t("org.noCalendars")}</p>
          )}
          <ul className="divide-y divide-line">
            {calendars.data?.results.map((c) => (
              <li key={c.id} className="flex flex-wrap items-baseline justify-between gap-2 py-3">
                <Link
                  to={`/app/${org}/calendars/${c.id}`}
                  className="font-medium text-accent hover:underline"
                >
                  {c.name}
                </Link>
                <span className="text-sm text-muted">
                  {c.sources
                    .map((s) => (s.subdiv ? `${s.country}-${s.subdiv}` : s.country))
                    .join(" + ")}
                </span>
              </li>
            ))}
          </ul>
        </Card>
        {role !== "viewer" && (
          <Card title={t("org.newCalendar")}>
            <NewCalendarForm org={org} />
          </Card>
        )}
      </div>
    </>
  );
}
