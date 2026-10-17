import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, type Schemas, unwrap } from "../api/client";
import { useFormat } from "../lib/format";
import { Badge, Button, Card, ErrorText, Field, Input } from "./ui";

type Event = Schemas["EventsEnum"];
const EVENTS: Event[] = [
  "calendar.updated",
  "calendar.deleted",
  "custom_day.created",
  "custom_day.updated",
  "custom_day.deleted",
];
const STATUS_TONE = { success: "workday", failed: "holiday", pending: "neutral" } as const;

export function WebhooksCard({ org }: { org: string }) {
  const { t } = useTranslation();
  const client = useQueryClient();
  const [url, setUrl] = useState("");
  const [events, setEvents] = useState<Event[]>(EVENTS);
  const [secret, setSecret] = useState<string | null>(null);
  const [open, setOpen] = useState<number | null>(null);
  const queryKey = ["webhooks", org];
  const refresh = () => client.invalidateQueries({ queryKey });
  const at = (id: number) => ({ params: { path: { org_slug: org, id } } });

  const hooks = useQuery({
    queryKey,
    queryFn: () =>
      unwrap(api.GET("/api/v1/orgs/{org_slug}/webhooks/", { params: { path: { org_slug: org } } })),
  });
  const create = useMutation({
    mutationFn: () =>
      unwrap(
        api.POST("/api/v1/orgs/{org_slug}/webhooks/", {
          params: { path: { org_slug: org } },
          body: { url, events },
        }),
      ),
    onSuccess: (hook) => {
      setUrl("");
      setSecret(hook.secret);
      return refresh();
    },
  });
  const rotate = useMutation({
    mutationFn: (id: number) =>
      unwrap(api.POST("/api/v1/orgs/{org_slug}/webhooks/{id}/rotate-secret/", at(id))),
    onSuccess: (hook) => setSecret(hook.secret),
  });
  const toggle = useMutation({
    mutationFn: (hook: Schemas["Webhook"]) =>
      unwrap(
        api.PATCH("/api/v1/orgs/{org_slug}/webhooks/{id}/", {
          ...at(hook.id),
          body: { is_active: !hook.is_active },
        }),
      ),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: (id: number) =>
      unwrap(api.DELETE("/api/v1/orgs/{org_slug}/webhooks/{id}/", at(id))),
    onSuccess: refresh,
  });
  const ping = useMutation({
    mutationFn: (id: number) =>
      unwrap(api.POST("/api/v1/orgs/{org_slug}/webhooks/{id}/ping/", at(id))),
    onSuccess: (_, id) => {
      setOpen(id);
      return client.invalidateQueries({ queryKey: ["deliveries", org, id] });
    },
  });

  function toggleEvent(event: Event) {
    setEvents((current) =>
      current.includes(event) ? current.filter((e) => e !== event) : [...current, event],
    );
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    create.mutate();
  }

  const list = hooks.data?.results ?? [];

  return (
    <Card title={t("webhooks.title")}>
      <p className="mb-4 text-sm text-muted">{t("webhooks.intro")}</p>

      {secret && (
        <div className="mb-4 rounded-lg border border-accent bg-accent-soft p-3" role="status">
          <p className="mb-2 text-sm font-medium">{t("webhooks.secretOnce")}</p>
          <Input
            readOnly
            dir="ltr"
            aria-label={t("webhooks.secret")}
            value={secret}
            onFocus={(e) => e.target.select()}
            className="w-full font-mono text-xs"
          />
        </div>
      )}

      {list.length === 0 ? (
        <p className="mb-4 text-sm text-muted">{t("webhooks.none")}</p>
      ) : (
        <ul className="mb-4 divide-y divide-line">
          {list.map((hook) => (
            <li key={hook.id} className="py-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="min-w-0 text-sm">
                  <p className="truncate font-mono" dir="ltr">
                    {hook.url}
                  </p>
                  <p className="text-muted">
                    {hook.is_active ? (
                      <Badge tone="workday">{t("webhooks.active")}</Badge>
                    ) : (
                      <Badge tone="holiday">{t("webhooks.disabled")}</Badge>
                    )}{" "}
                    {hook.events.join(", ")}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="ghost"
                    disabled={!hook.is_active || ping.isPending}
                    onClick={() => ping.mutate(hook.id)}
                  >
                    {t("webhooks.ping")}
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() => setOpen(open === hook.id ? null : hook.id)}
                    aria-expanded={open === hook.id}
                  >
                    {t("webhooks.deliveries")}
                  </Button>
                  <Button variant="ghost" onClick={() => toggle.mutate(hook)}>
                    {hook.is_active ? t("webhooks.disable") : t("webhooks.enable")}
                  </Button>
                  <Button variant="ghost" onClick={() => rotate.mutate(hook.id)}>
                    {t("webhooks.rotate")}
                  </Button>
                  <Button variant="danger" onClick={() => remove.mutate(hook.id)}>
                    {t("common.remove")}
                  </Button>
                </div>
              </div>
              {open === hook.id && <Deliveries org={org} id={hook.id} />}
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={onSubmit} className="flex flex-col gap-3">
        <Field label={t("webhooks.url")} hint={t("webhooks.urlHint")}>
          <Input
            required
            type="url"
            dir="ltr"
            maxLength={500}
            placeholder="https://"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
        </Field>
        <fieldset className="flex flex-wrap gap-2">
          <legend className="mb-1 text-sm font-medium">{t("webhooks.events")}</legend>
          {EVENTS.map((event) => (
            <label
              key={event}
              className="flex cursor-pointer items-center gap-1.5 rounded-full border border-line px-3 py-1 font-mono text-xs has-[:checked]:border-accent has-[:checked]:bg-accent-soft"
            >
              <input
                type="checkbox"
                className="accent-accent"
                checked={events.includes(event)}
                onChange={() => toggleEvent(event)}
              />
              {event}
            </label>
          ))}
        </fieldset>
        <div>
          <Button type="submit" disabled={create.isPending || events.length === 0}>
            {t("webhooks.create")}
          </Button>
        </div>
      </form>
      <ErrorText
        error={
          hooks.error ?? create.error ?? rotate.error ?? toggle.error ?? remove.error ?? ping.error
        }
      />
    </Card>
  );
}

function Deliveries({ org, id }: { org: string; id: number }) {
  const { t } = useTranslation();
  const fmt = useFormat();
  const deliveries = useQuery({
    queryKey: ["deliveries", org, id],
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/orgs/{org_slug}/webhooks/{id}/deliveries/", {
          params: { path: { org_slug: org, id } },
        }),
      ),
    refetchInterval: 5000,
  });
  const list = deliveries.data ?? [];
  if (list.length === 0)
    return <p className="mt-2 text-sm text-muted">{t("webhooks.noDeliveries")}</p>;
  return (
    <table className="mt-2 w-full text-start text-xs">
      <thead className="text-muted">
        <tr>
          <th className="py-1 text-start font-medium">{t("webhooks.when")}</th>
          <th className="py-1 text-start font-medium">{t("webhooks.event")}</th>
          <th className="py-1 text-start font-medium">{t("webhooks.status")}</th>
          <th className="py-1 text-start font-medium">{t("webhooks.response")}</th>
        </tr>
      </thead>
      <tbody>
        {list.map((d) => (
          <tr key={d.id} className="border-t border-line">
            <td className="py-1">{fmt.shortDate(d.created_at.slice(0, 10))}</td>
            <td className="py-1 font-mono">{d.event}</td>
            <td className="py-1">
              <Badge tone={STATUS_TONE[d.status ?? "pending"]}>
                {t(`webhooks.statuses.${d.status ?? "pending"}`)}
              </Badge>{" "}
              {t("webhooks.attempts", { count: d.attempts ?? 0 })}
            </td>
            <td className="py-1 font-mono" dir="ltr">
              {d.response_status ?? "—"} {d.error}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
