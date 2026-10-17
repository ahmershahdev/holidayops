import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router";
import { api, type Schemas, unwrap } from "../api/client";
import { Badge, Button, Card, ErrorText, Field, Input, PageHeader, Select } from "../components/ui";
import { WebhooksCard } from "../components/WebhooksCard";
import { useMe } from "../lib/auth";
import { useFormat } from "../lib/format";

type Role = Schemas["RoleEnum"];
const ROLES: Role[] = ["viewer", "member", "admin", "owner"];

export function OrgSettingsPage() {
  const { t } = useTranslation();
  const { org = "" } = useParams();
  const client = useQueryClient();
  const navigate = useNavigate();
  const me = useMe().data;
  const fmt = useFormat();
  const path = { params: { path: { org_slug: org } } };
  const detail = useQuery({
    queryKey: ["org", org],
    queryFn: () => unwrap(api.GET("/api/v1/orgs/{org_slug}/", path)),
  });
  const members = useQuery({
    queryKey: ["members", org],
    queryFn: () => unwrap(api.GET("/api/v1/orgs/{org_slug}/members/", path)),
  });
  const [name, setName] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [newRole, setNewRole] = useState<Role>("viewer");
  const [confirmDelete, setConfirmDelete] = useState("");

  const myRole = detail.data?.role as Role | undefined;
  const isAdmin = myRole === "admin" || myRole === "owner";
  const isOwner = myRole === "owner";
  const refreshMembers = () => client.invalidateQueries({ queryKey: ["members", org] });

  const rename = useMutation({
    mutationFn: () =>
      unwrap(api.PATCH("/api/v1/orgs/{org_slug}/", { ...path, body: { name: name ?? "" } })),
    onSuccess: () => client.invalidateQueries({ queryKey: ["org", org] }),
  });
  const invites = useQuery({
    queryKey: ["invites", org],
    queryFn: () => unwrap(api.GET("/api/v1/orgs/{org_slug}/invites/", path)),
    enabled: isAdmin,
  });
  const refreshInvites = () => client.invalidateQueries({ queryKey: ["invites", org] });
  const add = useMutation({
    mutationFn: () =>
      unwrap(
        api.POST("/api/v1/orgs/{org_slug}/invites/", { ...path, body: { email, role: newRole } }),
      ),
    onSuccess: () => {
      setEmail("");
      return refreshInvites();
    },
  });
  const resend = useMutation({
    mutationFn: (id: number) =>
      unwrap(
        api.POST("/api/v1/orgs/{org_slug}/invites/{id}/resend/", {
          params: { path: { org_slug: org, id } },
        }),
      ),
    onSettled: refreshInvites,
  });
  const revoke = useMutation({
    mutationFn: (id: number) =>
      unwrap(
        api.DELETE("/api/v1/orgs/{org_slug}/invites/{id}/", {
          params: { path: { org_slug: org, id } },
        }),
      ),
    onSettled: refreshInvites,
  });
  const changeRole = useMutation({
    mutationFn: ({ id, role }: { id: number; role: Role }) =>
      unwrap(
        api.PATCH("/api/v1/orgs/{org_slug}/members/{id}/", {
          params: { path: { org_slug: org, id } },
          body: { role },
        }),
      ),
    onSettled: refreshMembers,
  });
  const removeMember = useMutation({
    mutationFn: (id: number) =>
      unwrap(
        api.DELETE("/api/v1/orgs/{org_slug}/members/{id}/", {
          params: { path: { org_slug: org, id } },
        }),
      ),
    onSettled: refreshMembers,
  });
  const deleteOrg = useMutation({
    mutationFn: () => unwrap(api.DELETE("/api/v1/orgs/{org_slug}/", path)),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: ["orgs"] });
      navigate("/app");
    },
  });

  if (detail.error) return <ErrorText error={detail.error} />;
  const assignable = ROLES.filter((r) => isOwner || r !== "owner");

  return (
    <>
      <PageHeader
        title={t("org.settingsTitle", { name: detail.data?.name ?? "" })}
        actions={
          <Link
            to={`/app/${org}`}
            className="rounded-lg border border-line bg-surface px-4 py-2 text-sm hover:border-accent"
          >
            {t("common.back")}
          </Link>
        }
      />

      {isAdmin && (
        <Card title={t("org.rename")}>
          <form
            className="flex flex-wrap items-end gap-2"
            onSubmit={(e: FormEvent) => (e.preventDefault(), rename.mutate())}
          >
            <Field label={t("settings.name")}>
              <Input
                required
                maxLength={120}
                value={name ?? detail.data?.name ?? ""}
                onChange={(e) => setName(e.target.value)}
              />
            </Field>
            <Button type="submit">{t("common.save")}</Button>
          </form>
          <ErrorText error={rename.error} />
        </Card>
      )}

      <Card title={t("org.members")}>
        <ul className="divide-y divide-line">
          {members.data?.map((m) => {
            const editable = isAdmin && m.user.id !== me?.id && (isOwner || m.role !== "owner");
            return (
              <li key={m.id} className="flex flex-wrap items-center gap-3 py-3">
                <span className="min-w-0 flex-1">
                  <span className="block font-medium">{m.user.name || m.user.email}</span>
                  {m.user.name && <span className="text-sm text-muted">{m.user.email}</span>}
                </span>
                {editable ? (
                  <>
                    <Select
                      aria-label={t("org.roleFor", { name: m.user.email })}
                      value={m.role}
                      onChange={(e) =>
                        changeRole.mutate({ id: m.id, role: e.target.value as Role })
                      }
                    >
                      {assignable.map((r) => (
                        <option key={r} value={r}>
                          {t(`roles.${r}`)}
                        </option>
                      ))}
                    </Select>
                    <Button variant="danger" onClick={() => removeMember.mutate(m.id)}>
                      {t("common.remove")}
                    </Button>
                  </>
                ) : (
                  <Badge tone="neutral">{t(`roles.${m.role}`)}</Badge>
                )}
              </li>
            );
          })}
        </ul>
        <ErrorText error={changeRole.error ?? removeMember.error ?? members.error} />
        {isAdmin && (
          <form
            className="mt-4 flex flex-wrap items-end gap-2 border-t border-line pt-4"
            onSubmit={(e: FormEvent) => (e.preventDefault(), add.mutate())}
          >
            <Field label={t("org.addByEmail")}>
              <Input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </Field>
            <Select
              aria-label={t("org.role")}
              value={newRole}
              onChange={(e) => setNewRole(e.target.value as Role)}
            >
              {assignable.map((r) => (
                <option key={r} value={r}>
                  {t(`roles.${r}`)}
                </option>
              ))}
            </Select>
            <Button type="submit" disabled={add.isPending}>
              {t("invites.send")}
            </Button>
            <p className="w-full text-xs text-muted">{t("org.addHint")}</p>
          </form>
        )}
        <ErrorText error={add.error} />
        {isAdmin && (invites.data?.length ?? 0) > 0 && (
          <div className="mt-4 border-t border-line pt-4">
            <h3 className="mb-2 text-sm font-medium">{t("invites.pending")}</h3>
            <ul className="divide-y divide-line">
              {invites.data?.map((i) => (
                <li key={i.id} className="flex flex-wrap items-center gap-3 py-2 text-sm">
                  <span className="min-w-0 flex-1" dir="ltr">
                    {i.email}
                  </span>
                  <Badge tone="neutral">{t(`roles.${i.role}`)}</Badge>
                  <span className="text-muted">
                    {t("invites.expires", { date: fmt.shortDate(i.expires_at.slice(0, 10)) })}
                  </span>
                  <Button variant="ghost" onClick={() => resend.mutate(i.id)}>
                    {t("invites.resend")}
                  </Button>
                  <Button variant="danger" onClick={() => revoke.mutate(i.id)}>
                    {t("invites.revoke")}
                  </Button>
                </li>
              ))}
            </ul>
            <ErrorText error={resend.error ?? revoke.error} />
          </div>
        )}
      </Card>

      {isAdmin && <WebhooksCard org={org} />}

      {isOwner && detail.data && (
        <Card title={t("settings.dangerZone")}>
          <p className="mb-3 text-sm text-muted">
            {t("org.deleteHint", { name: detail.data.name })}
          </p>
          <div className="flex flex-wrap gap-2">
            <Input
              aria-label={t("settings.confirmName")}
              value={confirmDelete}
              onChange={(e) => setConfirmDelete(e.target.value)}
              placeholder={detail.data.name}
            />
            <Button
              variant="danger"
              disabled={confirmDelete !== detail.data.name}
              onClick={() => deleteOrg.mutate()}
            >
              {t("org.delete")}
            </Button>
          </div>
          <ErrorText error={deleteOrg.error} />
        </Card>
      )}
    </>
  );
}
