import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, Navigate } from "react-router";
import { api, unwrap } from "../api/client";
import { Badge, Button, Card, ErrorText, Field, Input, PageHeader } from "../components/ui";
import { useMe } from "../lib/auth";

export function OrgsPage() {
  const { t } = useTranslation();
  const me = useMe();
  const client = useQueryClient();
  const [name, setName] = useState("");
  const orgs = useQuery({
    queryKey: ["orgs"],
    queryFn: () => unwrap(api.GET("/api/v1/orgs/")),
    enabled: Boolean(me.data),
  });
  const create = useMutation({
    mutationFn: () => unwrap(api.POST("/api/v1/orgs/", { body: { name } })),
    onSuccess: () => {
      setName("");
      return client.invalidateQueries({ queryKey: ["orgs"] });
    },
  });

  if (me.isLoading) return null;
  if (!me.data) return <Navigate to="/login" replace />;

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    create.mutate();
  }

  return (
    <>
      <PageHeader title={t("orgs.title")} subtitle={t("orgs.subtitle")} />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card title={t("orgs.yours")}>
          {orgs.data?.length === 0 && <p className="text-muted">{t("orgs.empty")}</p>}
          <ul className="divide-y divide-line">
            {orgs.data?.map((org) => (
              <li key={org.id} className="flex items-center justify-between py-3">
                <Link to={`/app/${org.slug}`} className="font-medium text-accent hover:underline">
                  {org.name}
                </Link>
                {org.role && <Badge tone="neutral">{t(`roles.${org.role}`)}</Badge>}
              </li>
            ))}
          </ul>
        </Card>
        <Card title={t("orgs.new")}>
          <form onSubmit={onSubmit} className="flex flex-wrap items-end gap-3">
            <Field label={t("settings.name")}>
              <Input
                required
                maxLength={120}
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </Field>
            <Button type="submit" disabled={create.isPending}>
              {t("common.create")}
            </Button>
          </form>
          <ErrorText error={create.error} />
        </Card>
      </div>
    </>
  );
}
