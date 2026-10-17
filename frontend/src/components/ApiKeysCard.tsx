import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, unwrap } from "../api/client";
import { ltr } from "../lib/chart";
import { useFormat } from "../lib/format";
import { Button, Card, ErrorText, Field, Input } from "./ui";

export function ApiKeysCard({ org, canManage }: { org: string; canManage: boolean }) {
  const { t } = useTranslation();
  const fmt = useFormat();
  const client = useQueryClient();
  const [name, setName] = useState("");
  const [created, setCreated] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const queryKey = ["api-keys", org];
  const path = { params: { path: { org_slug: org } } };
  const refresh = () =>
    Promise.all([
      client.invalidateQueries({ queryKey }),
      client.invalidateQueries({ queryKey: ["usage", org] }),
    ]);

  const keys = useQuery({
    queryKey,
    queryFn: () => unwrap(api.GET("/api/v1/orgs/{org_slug}/api-keys/", path)),
  });
  const create = useMutation({
    mutationFn: () =>
      unwrap(api.POST("/api/v1/orgs/{org_slug}/api-keys/", { ...path, body: { name } })),
    onSuccess: (key) => {
      setName("");
      setCreated(key.key);
      setCopied(false);
      return refresh();
    },
  });
  const revoke = useMutation({
    mutationFn: (id: number) =>
      unwrap(
        api.DELETE("/api/v1/orgs/{org_slug}/api-keys/{id}/", {
          params: { path: { org_slug: org, id } },
        }),
      ),
    onSuccess: refresh,
  });

  async function copy(value: string) {
    await navigator.clipboard.writeText(value);
    setCopied(true);
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    create.mutate();
  }

  const list = keys.data ?? [];

  return (
    <Card title={t("apiKeys.title")}>
      <p className="mb-4 text-sm text-muted">
        {t("apiKeys.intro", { header: ltr("Authorization: Bearer <key>") })}
      </p>

      {created && (
        <div className="mb-4 rounded-lg border border-accent bg-accent-soft p-3" role="status">
          <p className="mb-2 text-sm font-medium">{t("apiKeys.copyOnce")}</p>
          <div className="flex flex-wrap gap-2">
            <Input
              readOnly
              dir="ltr"
              aria-label={t("apiKeys.key")}
              value={created}
              onFocus={(e) => e.target.select()}
              className="min-w-0 flex-1 font-mono text-xs"
            />
            <Button variant="ghost" onClick={() => copy(created)}>
              {copied ? t("feeds.copied") : t("feeds.copy")}
            </Button>
          </div>
          <pre className="mt-2 overflow-x-auto text-xs text-muted" dir="ltr">
            {`curl -H "Authorization: Bearer ${created}" \\\n  "${window.location.origin}/api/v1/business-days/check/?country=PK&date=2027-03-23"`}
          </pre>
        </div>
      )}

      {list.length === 0 ? (
        <p className="mb-4 text-sm text-muted">{t("apiKeys.none")}</p>
      ) : (
        <ul className="mb-4 divide-y divide-line">
          {list.map((key) => (
            <li key={key.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
              <div className="text-sm">
                <p className="font-medium">
                  {key.name}{" "}
                  <span className="font-mono text-xs text-muted" dir="ltr">
                    hops_{key.prefix}_…
                  </span>
                </p>
                <p className="text-muted">
                  {t("feeds.created", { date: fmt.shortDate(key.created_at.slice(0, 10)) })}
                  {" · "}
                  {key.last_used_at
                    ? t("feeds.lastUsed", { date: fmt.shortDate(key.last_used_at.slice(0, 10)) })
                    : t("feeds.neverUsed")}
                </p>
              </div>
              {canManage && (
                <Button
                  variant="danger"
                  disabled={revoke.isPending}
                  onClick={() => revoke.mutate(key.id)}
                >
                  {t("feeds.revoke")}
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}

      {canManage ? (
        <form onSubmit={onSubmit} className="flex flex-wrap items-end gap-2">
          <Field label={t("apiKeys.name")}>
            <Input
              required
              maxLength={80}
              value={name}
              placeholder={t("apiKeys.namePlaceholder")}
              onChange={(e) => setName(e.target.value)}
            />
          </Field>
          <Button type="submit" disabled={create.isPending}>
            {t("apiKeys.create")}
          </Button>
        </form>
      ) : (
        <p className="text-sm text-muted">{t("apiKeys.ownersOnly")}</p>
      )}
      <ErrorText error={keys.error ?? create.error ?? revoke.error} />
    </Card>
  );
}
