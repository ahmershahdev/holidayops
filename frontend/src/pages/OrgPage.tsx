import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { Link, useParams } from "react-router";
import { api, type Schemas, unwrap } from "../api/client";
import { CountrySelect } from "../components/CountrySelect";
import { Badge, Button, Card, ErrorText, Field, Input, Select } from "../components/ui";

const ROLES: Schemas["RoleEnum"][] = ["viewer", "member", "admin", "owner"];

function NewCalendarForm({ org }: { org: string }) {
  const client = useQueryClient();
  const [name, setName] = useState("");
  const [countries, setCountries] = useState(["PK"]);
  const create = useMutation({
    mutationFn: () =>
      unwrap(
        api.POST("/api/v1/orgs/{org_slug}/calendars/", {
          params: { path: { org_slug: org } },
          body: { name, sources: countries.map((country) => ({ country })) },
        }),
      ),
    onSuccess: () => {
      setName("");
      setCountries(["PK"]);
      return client.invalidateQueries({ queryKey: ["calendars", org] });
    },
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    create.mutate();
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-3">
      <Field label="Calendar name">
        <Input required value={name} onChange={(e) => setName(e.target.value)} />
      </Field>
      <span className="text-sm font-medium text-slate-700">Countries (holidays are merged)</span>
      {countries.map((code, i) => (
        <div key={i} className="flex gap-2">
          <CountrySelect
            value={code}
            onChange={(c) => setCountries(countries.map((old, j) => (j === i ? c : old)))}
          />
          {countries.length > 1 && (
            <Button
              type="button"
              variant="danger"
              onClick={() => setCountries(countries.filter((_, j) => j !== i))}
            >
              Remove
            </Button>
          )}
        </div>
      ))}
      <div className="flex gap-2">
        <Button type="button" variant="ghost" onClick={() => setCountries([...countries, "SA"])}>
          Add country
        </Button>
        <Button type="submit" disabled={create.isPending}>
          Create calendar
        </Button>
      </div>
      <ErrorText error={create.error} />
    </form>
  );
}

function Members({ org, canManage }: { org: string; canManage: boolean }) {
  const client = useQueryClient();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Schemas["RoleEnum"]>("viewer");
  const path = { params: { path: { org_slug: org } } };
  const members = useQuery({
    queryKey: ["members", org],
    queryFn: () => unwrap(api.GET("/api/v1/orgs/{org_slug}/members/", path)),
  });
  const add = useMutation({
    mutationFn: () =>
      unwrap(api.POST("/api/v1/orgs/{org_slug}/members/", { ...path, body: { email, role } })),
    onSuccess: () => {
      setEmail("");
      return client.invalidateQueries({ queryKey: ["members", org] });
    },
  });

  return (
    <Card title="Members">
      <ul className="divide-y divide-slate-100">
        {members.data?.map((m) => (
          <li key={m.id} className="flex items-center justify-between py-2 text-sm">
            <span>{m.user.name || m.user.email}</span>
            <Badge tone="slate">{m.role}</Badge>
          </li>
        ))}
      </ul>
      {canManage && (
        <form
          className="mt-4 flex flex-wrap items-end gap-2"
          onSubmit={(e) => (e.preventDefault(), add.mutate())}
        >
          <Field label="Add by email (they must have an account)">
            <Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
          <Select value={role} onChange={(e) => setRole(e.target.value as Schemas["RoleEnum"])}>
            {ROLES.map((r) => (
              <option key={r}>{r}</option>
            ))}
          </Select>
          <Button type="submit">Add</Button>
        </form>
      )}
      <ErrorText error={add.error ?? members.error} />
    </Card>
  );
}

export function OrgPage() {
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
  const canWrite = role !== "viewer";
  const canManage = role === "admin" || role === "owner";

  if (detail.error) return <ErrorText error={detail.error} />;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold text-slate-900">{detail.data?.name}</h1>
        <Badge tone="slate">{role}</Badge>
      </div>
      <div className="grid gap-6 md:grid-cols-2">
        <Card title="Calendars">
          {calendars.data?.results.length === 0 && (
            <p className="text-sm text-slate-600">No calendars yet.</p>
          )}
          <ul className="divide-y divide-slate-100">
            {calendars.data?.results.map((c) => (
              <li key={c.id} className="py-2">
                <Link
                  to={`/app/${org}/calendars/${c.id}`}
                  className="font-medium text-teal-800 hover:underline"
                >
                  {c.name}
                </Link>
                <span className="ms-2 text-sm text-slate-500">
                  {c.sources.map((s) => s.country).join(" + ")}
                </span>
              </li>
            ))}
          </ul>
        </Card>
        {canWrite && (
          <Card title="New calendar">
            <NewCalendarForm org={org} />
          </Card>
        )}
      </div>
      <Members org={org} canManage={canManage} />
    </div>
  );
}
