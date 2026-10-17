import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { api, unwrap } from "../api/client";
import { Button } from "./ui";

export function DigestToggle({ org, calendar }: { org: string; calendar: string }) {
  const { t } = useTranslation();
  const client = useQueryClient();
  const queryKey = ["digest", org, calendar];
  const params = { params: { path: { org_slug: org, calendar_id: calendar } } };
  const url = "/api/v1/orgs/{org_slug}/calendars/{calendar_id}/digest/" as const;

  const digest = useQuery({ queryKey, queryFn: () => unwrap(api.GET(url, params)) });
  const toggle = useMutation({
    mutationFn: (on: boolean) => unwrap(on ? api.PUT(url, params) : api.DELETE(url, params)),
    onSuccess: (data) => client.setQueryData(queryKey, data),
  });

  if (!digest.data) return null;
  const on = digest.data.subscribed;
  return (
    <Button
      variant="ghost"
      aria-pressed={on}
      title={t("digest.hint")}
      disabled={toggle.isPending}
      onClick={() => toggle.mutate(!on)}
    >
      {on ? t("digest.on") : t("digest.off")}
    </Button>
  );
}
