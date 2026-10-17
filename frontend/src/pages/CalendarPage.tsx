import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";
import { api, unwrap } from "../api/client";
import { useCountries } from "../api/hooks";
import { CalendarExplorer } from "../components/calendar/CalendarExplorer";
import { DigestToggle } from "../components/DigestToggle";
import { ErrorText, PageHeader } from "../components/ui";
import { weekStartFor } from "../lib/dates";

export function CalendarPage() {
  const { t } = useTranslation();
  const { org = "", id = "" } = useParams();
  const countries = useCountries();
  const orgDetail = useQuery({
    queryKey: ["org", org],
    queryFn: () =>
      unwrap(api.GET("/api/v1/orgs/{org_slug}/", { params: { path: { org_slug: org } } })),
  });
  const calendar = useQuery({
    queryKey: ["calendar", org, id],
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/orgs/{org_slug}/calendars/{id}/", {
          params: { path: { org_slug: org, id } },
        }),
      ),
  });

  if (calendar.error) return <ErrorText error={calendar.error} />;
  if (!calendar.data) return null;

  const sources = calendar.data.sources.map((s) =>
    s.subdiv ? `${s.country}-${s.subdiv}` : s.country,
  );
  const firstCountry = countries.data?.find((c) => c.code === calendar.data.sources[0]?.country);
  const weekend = calendar.data.weekend ?? firstCountry?.weekend ?? [5, 6];
  const role = orgDetail.data?.role;

  return (
    <>
      <PageHeader
        title={calendar.data.name}
        subtitle={sources.join(" + ")}
        actions={
          <>
            <Link
              to={`/app/${org}`}
              className="rounded-lg border border-line bg-surface px-4 py-2 text-sm hover:border-accent"
            >
              {t("common.back")}
            </Link>
            <DigestToggle org={org} calendar={id} />
            {role && role !== "viewer" && (
              <Link
                to={`/app/${org}/calendars/${id}/settings`}
                className="rounded-lg border border-line bg-surface px-4 py-2 text-sm hover:border-accent"
              >
                {t("settings.title")}
              </Link>
            )}
          </>
        }
      />
      <CalendarExplorer
        target={{ calendar: id }}
        weekStart={weekStartFor(weekend)}
        sources={sources}
        editor={{ org, calendar: id, canWrite: Boolean(role && role !== "viewer") }}
      />
    </>
  );
}
