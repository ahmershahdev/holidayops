import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, type Schemas, unwrap } from "../api/client";
import { useFormat } from "../lib/format";
import { Button, Card, ErrorText, Field, Input } from "./ui";

export function FeedsCard({
  org,
  calendar,
  canWrite,
}: {
  org: string;
  calendar: string;
  canWrite: boolean;
}) {
  const { t } = useTranslation();
  const fmt = useFormat();
  const client = useQueryClient();
  const [label, setLabel] = useState("");
  const [created, setCreated] = useState<Schemas["FeedTokenCreated"] | null>(null);
  const [copied, setCopied] = useState(false);
  const path = { org_slug: org, calendar_id: calendar };
  const queryKey = ["feeds", org, calendar];

  const feeds = useQuery({
    queryKey,
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/orgs/{org_slug}/calendars/{calendar_id}/feeds/", { params: { path } }),
      ),
  });

  function show(result: Schemas["FeedTokenCreated"]) {
    setCreated(result);
    setCopied(false);
    return client.invalidateQueries({ queryKey });
  }

  const create = useMutation({
    mutationFn: () =>
      unwrap(
        api.POST("/api/v1/orgs/{org_slug}/calendars/{calendar_id}/feeds/", {
          params: { path },
          body: { label },
        }),
      ),
    onSuccess: async (result) => {
      setLabel("");
      await show(result);
    },
  });
  const rotate = useMutation({
    mutationFn: (id: number) =>
      unwrap(
        api.POST("/api/v1/orgs/{org_slug}/calendars/{calendar_id}/feeds/{id}/rotate/", {
          params: { path: { ...path, id } },
        }),
      ),
    onSuccess: show,
  });
  const revoke = useMutation({
    mutationFn: (id: number) =>
      unwrap(
        api.DELETE("/api/v1/orgs/{org_slug}/calendars/{calendar_id}/feeds/{id}/", {
          params: { path: { ...path, id } },
        }),
      ),
    onSuccess: () => {
      setCreated(null);
      return client.invalidateQueries({ queryKey });
    },
  });

  async function copy(url: string) {
    await navigator.clipboard.writeText(url);
    setCopied(true);
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    create.mutate();
  }

  const list = feeds.data?.results ?? [];

  return (
    <Card title={t("feeds.title")}>
      <p className="mb-4 text-sm text-muted">{t("feeds.intro")}</p>

      {created && (
        <div className="mb-4 rounded-lg border border-accent bg-accent-soft p-3" role="status">
          <p className="mb-2 text-sm font-medium">{t("feeds.copyOnce")}</p>
          <div className="flex flex-wrap gap-2">
            <Input
              readOnly
              dir="ltr"
              aria-label={t("feeds.url")}
              value={created.url}
              onFocus={(e) => e.target.select()}
              className="min-w-0 flex-1 font-mono text-xs"
            />
            <Button variant="ghost" onClick={() => copy(created.url)}>
              {copied ? t("feeds.copied") : t("feeds.copy")}
            </Button>
          </div>
        </div>
      )}

      {list.length === 0 ? (
        <p className="mb-4 text-sm text-muted">{t("feeds.none")}</p>
      ) : (
        <ul className="mb-4 divide-y divide-line">
          {list.map((feed) => (
            <li key={feed.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
              <div className="text-sm">
                <p className="font-medium">{feed.label || t("feeds.unnamed")}</p>
                <p className="text-muted">
                  {t("feeds.created", { date: fmt.shortDate(feed.created_at.slice(0, 10)) })}
                  {" · "}
                  {feed.last_used_at
                    ? t("feeds.lastUsed", { date: fmt.shortDate(feed.last_used_at.slice(0, 10)) })
                    : t("feeds.neverUsed")}
                </p>
              </div>
              {canWrite && (
                <div className="flex gap-2">
                  <Button
                    variant="ghost"
                    disabled={rotate.isPending}
                    onClick={() => rotate.mutate(feed.id)}
                  >
                    {t("feeds.rotate")}
                  </Button>
                  <Button
                    variant="danger"
                    disabled={revoke.isPending}
                    onClick={() => revoke.mutate(feed.id)}
                  >
                    {t("feeds.revoke")}
                  </Button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      {canWrite && (
        <form onSubmit={onSubmit} className="flex flex-wrap items-end gap-2">
          <Field label={t("feeds.label")}>
            <Input
              maxLength={80}
              value={label}
              placeholder={t("feeds.labelPlaceholder")}
              onChange={(e) => setLabel(e.target.value)}
            />
          </Field>
          <Button type="submit" disabled={create.isPending}>
            {t("feeds.create")}
          </Button>
        </form>
      )}
      <ErrorText error={feeds.error ?? create.error ?? rotate.error ?? revoke.error} />
    </Card>
  );
}
