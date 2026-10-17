import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useSearchParams } from "react-router";
import { api, unwrap } from "../api/client";
import { Button, Card, ErrorText, PageHeader } from "../components/ui";
import { useMe } from "../lib/auth";

export function InvitePage() {
  const { t } = useTranslation();
  const [search] = useSearchParams();
  const token = search.get("token") ?? "";
  const me = useMe();
  const client = useQueryClient();
  const navigate = useNavigate();
  const path = { params: { path: { token } } };

  const invite = useQuery({
    queryKey: ["invite", token],
    queryFn: () => unwrap(api.GET("/api/v1/invites/{token}/", path)),
    enabled: Boolean(token),
  });
  const accept = useMutation({
    mutationFn: () => unwrap(api.POST("/api/v1/invites/{token}/accept/", path)),
    onSuccess: async (org) => {
      await client.invalidateQueries({ queryKey: ["orgs"] });
      navigate(`/app/${org.slug}`);
    },
  });

  if (!token || invite.isError) {
    return (
      <>
        <PageHeader title={t("invite.title")} />
        <Card>
          <p className="text-sm">{t("invite.invalid")}</p>
        </Card>
      </>
    );
  }
  if (!invite.data || me.isPending) return null;

  const data = invite.data;
  const back = `/invite?token=${encodeURIComponent(token)}`;
  const auth = (to: string) =>
    `${to}?${new URLSearchParams({ next: back, email: data.email }).toString()}`;
  const wrongAccount = me.data && me.data.email.toLowerCase() !== data.email.toLowerCase();

  return (
    <>
      <PageHeader title={t("invite.title")} />
      <Card>
        <p className="mb-4">
          {t("invite.body", {
            inviter: data.invited_by || "HolidayOps",
            org: data.org_name,
            role: t(`roles.${data.role}`),
          })}
        </p>
        {!me.data ? (
          <div className="flex flex-wrap items-center gap-3">
            <Link
              to={auth("/signup")}
              className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent/90"
            >
              {t("invite.signup")}
            </Link>
            <Link to={auth("/login")} className="text-sm text-accent underline">
              {t("invite.login")}
            </Link>
            <p className="w-full text-sm text-muted">
              {t("invite.useEmail", { email: data.email })}
            </p>
          </div>
        ) : wrongAccount ? (
          <p className="text-sm text-holiday" role="alert">
            {t("invite.wrongAccount", { email: data.email, current: me.data.email })}
          </p>
        ) : (
          <Button disabled={accept.isPending} onClick={() => accept.mutate()}>
            {t("invite.accept")}
          </Button>
        )}
        <ErrorText error={accept.error} />
      </Card>
    </>
  );
}
