import { useMutation, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, type Schemas, unwrap } from "../../api/client";
import type { ISODate } from "../../lib/dates";
import { useFormat } from "../../lib/format";
import { Button, ErrorText, Field, Input, Select } from "../ui";
import type { DayResult } from "./dayStatus";
import { StatusLine } from "./StatusLine";

type CustomDay = Schemas["CustomDay"];
type Kind = Schemas["CustomDayKindEnum"];
const KINDS: Kind[] = ["closure", "half_day", "working_day"];

type Editor = { org: string; calendar: string; custom?: CustomDay; canWrite: boolean };

export function DayPanel({
  date,
  day,
  editor,
}: {
  date: ISODate;
  day?: DayResult;
  editor?: Editor;
}) {
  const fmt = useFormat();
  return (
    <div className="flex flex-col gap-4">
      <h2 className="font-display text-xl">{fmt.longDate(date)}</h2>
      {day && <StatusLine day={day} />}
      {editor?.canWrite && (
        <CustomDayEditor key={`${date}-${editor.custom?.id}`} date={date} {...editor} />
      )}
    </div>
  );
}

function CustomDayEditor({ date, org, calendar, custom }: Editor & { date: ISODate }) {
  const { t } = useTranslation();
  const client = useQueryClient();
  const [name, setName] = useState(custom?.name ?? "");
  const [kind, setKind] = useState<Kind>(custom?.kind ?? "closure");
  const base = { org_slug: org, calendar_id: calendar };

  const refresh = () =>
    Promise.all(
      ["custom-days", "range", "holidays"].map((key) =>
        client.invalidateQueries({ queryKey: [key] }),
      ),
    );

  const save = useMutation({
    mutationFn: () =>
      custom
        ? unwrap(
            api.PATCH("/api/v1/orgs/{org_slug}/calendars/{calendar_id}/custom-days/{id}/", {
              params: { path: { ...base, id: custom.id } },
              body: { name, kind },
            }),
          )
        : unwrap(
            api.POST("/api/v1/orgs/{org_slug}/calendars/{calendar_id}/custom-days/", {
              params: { path: base },
              body: { date, name, kind },
            }),
          ),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: (id: number) =>
      unwrap(
        api.DELETE("/api/v1/orgs/{org_slug}/calendars/{calendar_id}/custom-days/{id}/", {
          params: { path: { ...base, id } },
        }),
      ),
    onSuccess: refresh,
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    save.mutate();
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-3 border-t border-line pt-4">
      <h3 className="text-sm font-semibold">{custom ? t("custom.edit") : t("custom.add")}</h3>
      <Field label={t("custom.kind")}>
        <Select value={kind} onChange={(e) => setKind(e.target.value as Kind)}>
          {KINDS.map((k) => (
            <option key={k} value={k}>
              {t(`custom.kinds.${k}`)}
            </option>
          ))}
        </Select>
      </Field>
      <Field label={t("custom.name")}>
        <Input required maxLength={120} value={name} onChange={(e) => setName(e.target.value)} />
      </Field>
      <div className="flex gap-2">
        <Button type="submit" disabled={save.isPending}>
          {custom ? t("common.save") : t("common.add")}
        </Button>
        {custom && (
          <Button type="button" variant="danger" onClick={() => remove.mutate(custom.id)}>
            {t("common.remove")}
          </Button>
        )}
      </div>
      <ErrorText error={save.error ?? remove.error} />
    </form>
  );
}
