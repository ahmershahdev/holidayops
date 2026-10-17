import { useMutation } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router";
import { api, unwrap } from "../api/client";
import { Button, Card, ErrorText, PageHeader } from "../components/ui";

export function UnsubscribePage() {
  const { t } = useTranslation();
  const [search] = useSearchParams();
  const token = search.get("token") ?? "";
  const unsubscribe = useMutation({
    mutationFn: () => unwrap(api.POST("/api/v1/digests/unsubscribe/", { body: { token } })),
  });

  return (
    <>
      <PageHeader title={t("digest.unsubscribeTitle")} />
      <Card>
        {unsubscribe.isSuccess ? (
          <p className="text-sm" role="status">
            {t("digest.unsubscribed")}{" "}
            <Link to="/app" className="text-accent hover:underline">
              {t("nav.calendars")}
            </Link>
          </p>
        ) : (
          <div className="flex flex-col items-start gap-3">
            <p className="text-sm text-muted">{t("digest.unsubscribeIntro")}</p>
            <Button disabled={!token || unsubscribe.isPending} onClick={() => unsubscribe.mutate()}>
              {t("digest.unsubscribe")}
            </Button>
            {unsubscribe.isError && <ErrorText error={t("digest.badLink")} />}
          </div>
        )}
      </Card>
    </>
  );
}
