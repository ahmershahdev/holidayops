import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { api, unwrap } from "../api/client";
import { Badge, Button, Card, ErrorText } from "./ui";

/** Where this account is signed in, with a way to sign the other devices out. */
export function SessionsCard() {
  const { t, i18n } = useTranslation();
  const client = useQueryClient();
  const sessions = useQuery({
    queryKey: ["sessions"],
    queryFn: () => unwrap(api.GET("/api/v1/auth/sessions/")),
  });
  const refresh = () => client.invalidateQueries({ queryKey: ["sessions"] });
  const endOne = useMutation({
    mutationFn: (id: number) =>
      unwrap(
        api.DELETE("/api/v1/auth/sessions/{session_id}/", { params: { path: { session_id: id } } }),
      ),
    onSuccess: refresh,
  });
  const endOthers = useMutation({
    mutationFn: () => unwrap(api.POST("/api/v1/auth/sessions/others/")),
    onSuccess: refresh,
  });
  const when = new Intl.DateTimeFormat(i18n.language, { dateStyle: "medium", timeStyle: "short" });
  const rows = sessions.data ?? [];
  const others = rows.filter((row) => !row.current).length;

  return (
    <Card title={t("sessions.title")}>
      <p className="mb-4 text-sm text-muted">{t("sessions.lead")}</p>
      <ul className="flex flex-col gap-3">
        {rows.map((row) => (
          <li
            key={row.id}
            className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-line px-4 py-3"
          >
            <div className="flex min-w-0 flex-col gap-0.5">
              <span className="flex flex-wrap items-center gap-2 text-sm font-medium text-ink">
                {row.browser || row.system
                  ? t("sessions.device", {
                      browser: row.browser || t("sessions.unknownBrowser"),
                      system: row.system || t("sessions.unknownSystem"),
                    })
                  : t("sessions.unknownDevice")}
                {row.current && <Badge tone="workday">{t("sessions.thisDevice")}</Badge>}
              </span>
              <span className="text-xs text-muted">
                {t("sessions.lastSeen", { when: when.format(new Date(row.last_seen_at)) })}
                {row.ip && (
                  <>
                    {" · "}
                    <span dir="ltr">{row.ip}</span>
                  </>
                )}
              </span>
            </div>
            {!row.current && (
              <Button
                variant="danger"
                disabled={endOne.isPending}
                onClick={() => endOne.mutate(row.id)}
              >
                {t("sessions.signOut")}
              </Button>
            )}
          </li>
        ))}
      </ul>
      {others > 0 && (
        <div className="mt-4">
          <Button variant="ghost" disabled={endOthers.isPending} onClick={() => endOthers.mutate()}>
            {t("sessions.signOutOthers")}
          </Button>
        </div>
      )}
      <ErrorText error={sessions.error ?? endOne.error ?? endOthers.error} />
    </Card>
  );
}
