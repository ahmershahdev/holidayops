import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { Link, Navigate } from "react-router";
import { api, unwrap } from "../api/client";
import { Badge, Button, Card, ErrorText, Field, Input } from "../components/ui";
import { useMe } from "../lib/auth";

export function OrgsPage() {
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
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold text-slate-900">Your organizations</h1>
      <Card>
        {orgs.data?.length === 0 && (
          <p className="text-slate-600">No organizations yet. Create one below.</p>
        )}
        <ul className="divide-y divide-slate-100">
          {orgs.data?.map((org) => (
            <li key={org.id} className="flex items-center justify-between py-3">
              <Link to={`/app/${org.slug}`} className="font-medium text-teal-800 hover:underline">
                {org.name}
              </Link>
              <Badge tone="slate">{org.role}</Badge>
            </li>
          ))}
        </ul>
      </Card>
      <Card title="New organization">
        <form onSubmit={onSubmit} className="flex items-end gap-3">
          <Field label="Name">
            <Input required value={name} onChange={(e) => setName(e.target.value)} />
          </Field>
          <Button type="submit" disabled={create.isPending}>
            Create
          </Button>
        </form>
        <ErrorText error={create.error} />
      </Card>
    </div>
  );
}
