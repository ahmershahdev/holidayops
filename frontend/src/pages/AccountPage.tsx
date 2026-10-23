import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router";
import { api, type Schemas, unwrap } from "../api/client";
import { SsoButtons, useSsoProviders } from "../components/auth/TwoFactorForm";
import { SessionsCard } from "../components/SessionsCard";
import { Badge, Button, Card, ErrorText, Field, Input, PageHeader, Select } from "../components/ui";
import { useMe } from "../lib/auth";

const LANGUAGES = [
  ["en", "English"],
  ["ur", "اردو"],
  ["ar", "العربية"],
] as const;

function Profile({ me }: { me: Schemas["User"] }) {
  const { t } = useTranslation();
  const client = useQueryClient();
  const [name, setName] = useState(me.name ?? "");
  const [language, setLanguage] = useState(me.language ?? "en");
  const save = useMutation({
    mutationFn: () =>
      unwrap(
        api.PATCH("/api/v1/auth/me/", {
          body: { name, language: language as Schemas["LanguageEnum"] },
        }),
      ),
    onSuccess: (user) => client.setQueryData(["me"], user),
  });
  return (
    <Card title={t("account.profile")}>
      <form
        className="grid gap-4 sm:grid-cols-[1fr_12rem_auto] sm:items-end"
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          save.mutate();
        }}
      >
        <Field label={t("auth.name")}>
          <Input value={name} maxLength={150} onChange={(e) => setName(e.target.value)} />
        </Field>
        <Field label={t("account.emailLanguage")}>
          <Select
            value={language}
            onChange={(e) => setLanguage(e.target.value as Schemas["LanguageEnum"])}
          >
            {LANGUAGES.map(([code, label]) => (
              <option key={code} value={code}>
                {label}
              </option>
            ))}
          </Select>
        </Field>
        <Button type="submit" disabled={save.isPending}>
          {save.isSuccess ? t("account.saved") : t("account.save")}
        </Button>
      </form>
      <p className="mt-4 text-sm text-muted">
        <span dir="ltr">{me.email}</span> ·{" "}
        <Link
          className="font-medium text-accent hover:underline"
          to={`/forgot-password?email=${encodeURIComponent(me.email)}`}
        >
          {me.has_password ? t("account.changePassword") : t("account.setPassword")}
        </Link>
      </p>
      <ErrorText error={save.error} />
    </Card>
  );
}

function RecoveryList({ codes }: { codes: string[] }) {
  const { t } = useTranslation();
  const download = `data:text/plain;charset=utf-8,${encodeURIComponent(codes.join("\n") + "\n")}`;
  return (
    <div className="mt-4 rounded-2xl border border-line bg-paper p-4">
      <p className="mb-3 text-sm font-medium text-ink">{t("twoFactor.saveCodes")}</p>
      <ul dir="ltr" className="grid grid-cols-2 gap-x-6 gap-y-1 font-mono text-sm text-ink">
        {codes.map((code) => (
          <li key={code}>{code}</li>
        ))}
      </ul>
      <a
        className="mt-3 inline-block text-sm font-medium text-accent hover:underline"
        href={download}
        download="holidayops-recovery-codes.txt"
      >
        {t("twoFactor.downloadCodes")}
      </a>
    </div>
  );
}

function TwoFactorCard({ me }: { me: Schemas["User"] }) {
  const { t } = useTranslation();
  const client = useQueryClient();
  const status = useQuery({
    queryKey: ["2fa"],
    queryFn: () => unwrap(api.GET("/api/v1/auth/2fa/")),
  });
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [codes, setCodes] = useState<string[]>([]);
  const refresh = () =>
    Promise.all([
      client.invalidateQueries({ queryKey: ["2fa"] }),
      client.invalidateQueries({ queryKey: ["me"] }),
    ]);

  const setup = useMutation({ mutationFn: () => unwrap(api.POST("/api/v1/auth/2fa/setup/")) });
  const confirm = useMutation({
    mutationFn: () => unwrap(api.POST("/api/v1/auth/2fa/confirm/", { body: { code } })),
    onSuccess: (data) => {
      setCodes(data.recovery_codes);
      setCode("");
      setup.reset();
      return refresh();
    },
  });
  const regenerate = useMutation({
    mutationFn: () => unwrap(api.POST("/api/v1/auth/2fa/recovery-codes/", { body: { code } })),
    onSuccess: (data) => {
      setCodes(data.recovery_codes);
      setCode("");
      return refresh();
    },
  });
  const disable = useMutation({
    mutationFn: () => unwrap(api.POST("/api/v1/auth/2fa/disable/", { body: { code, password } })),
    onSuccess: () => {
      setCode("");
      setPassword("");
      setCodes([]);
      return refresh();
    },
  });

  const enabled = status.data?.enabled ?? false;
  return (
    <Card
      title={
        <span className="flex items-center gap-3">
          {t("twoFactor.cardTitle")}
          <Badge tone={enabled ? "workday" : "neutral"}>
            {enabled ? t("twoFactor.on") : t("twoFactor.off")}
          </Badge>
        </span>
      }
    >
      <p className="text-sm text-muted">{t("twoFactor.explain")}</p>

      {!enabled && !setup.data && (
        <Button className="mt-4" onClick={() => setup.mutate()} disabled={setup.isPending}>
          {t("twoFactor.turnOn")}
        </Button>
      )}

      {!enabled && setup.data && (
        <div className="mt-4 grid gap-5 sm:grid-cols-[auto_1fr] sm:items-start">
          <img
            src={setup.data.qr}
            alt={t("twoFactor.qrAlt")}
            width={180}
            height={180}
            className="rounded-2xl border border-line bg-white p-2"
          />
          <form
            className="flex flex-col gap-3"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              confirm.mutate();
            }}
          >
            <p className="text-sm text-ink">{t("twoFactor.scan")}</p>
            <p className="text-xs text-muted">
              {t("twoFactor.manual")}{" "}
              <code dir="ltr" className="rounded bg-paper px-1.5 py-0.5 break-all text-ink">
                {setup.data.secret}
              </code>
            </p>
            <Field label={t("twoFactor.codeLabel")}>
              <Input
                dir="ltr"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                required
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
              />
            </Field>
            <ErrorText error={confirm.error} />
            <Button type="submit" disabled={confirm.isPending}>
              {t("twoFactor.confirm")}
            </Button>
          </form>
        </div>
      )}

      {codes.length > 0 && <RecoveryList codes={codes} />}

      {enabled && (
        <div className="mt-4 flex flex-col gap-3">
          <p className="text-sm text-muted">
            {t("twoFactor.codesLeft", { count: status.data?.recovery_codes_left ?? 0 })}
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label={t("twoFactor.codeLabel")}>
              <Input
                dir="ltr"
                autoComplete="one-time-code"
                maxLength={20}
                value={code}
                onChange={(e) => setCode(e.target.value)}
              />
            </Field>
            {me.has_password && (
              <Field label={t("auth.password")}>
                <Input
                  type="password"
                  dir="ltr"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </Field>
            )}
          </div>
          <ErrorText error={regenerate.error ?? disable.error} />
          <div className="flex flex-wrap gap-2">
            <Button
              variant="ghost"
              disabled={!code || regenerate.isPending}
              onClick={() => regenerate.mutate()}
            >
              {t("twoFactor.newCodes")}
            </Button>
            <Button
              variant="danger"
              disabled={!code || disable.isPending}
              onClick={() => disable.mutate()}
            >
              {t("twoFactor.turnOff")}
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
}

function ConnectedCard() {
  const { t } = useTranslation();
  const client = useQueryClient();
  const providers = useSsoProviders().data ?? [];
  const identities = useQuery({
    queryKey: ["identities"],
    queryFn: () => unwrap(api.GET("/api/v1/auth/identities/")),
  });
  const unlink = useMutation({
    mutationFn: (provider: string) =>
      unwrap(api.DELETE("/api/v1/auth/identities/{provider}/", { params: { path: { provider } } })),
    onSuccess: () => client.invalidateQueries({ queryKey: ["identities"] }),
  });
  if (!providers.length && !identities.data?.length) return null;
  const linked = new Set((identities.data ?? []).map((i) => i.provider));
  return (
    <Card title={t("sso.cardTitle")}>
      <ul className="flex flex-col gap-3">
        {(identities.data ?? []).map((identity) => (
          <li
            key={identity.provider}
            className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-line px-4 py-3"
          >
            <span className="text-sm text-ink">
              <strong className="capitalize">{identity.provider}</strong>{" "}
              <span dir="ltr" className="text-muted">
                {identity.email}
              </span>
            </span>
            <Button variant="danger" onClick={() => unlink.mutate(identity.provider)}>
              {t("sso.disconnect")}
            </Button>
          </li>
        ))}
      </ul>
      <ErrorText error={unlink.error} />
      {providers.some((p) => !linked.has(p.id)) && (
        <div className="mt-4 max-w-sm">
          <SsoButtons link />
        </div>
      )}
    </Card>
  );
}

function DataCard({ me }: { me: Schemas["User"] }) {
  const { t } = useTranslation();
  const client = useQueryClient();
  const navigate = useNavigate();
  const [confirm, setConfirm] = useState("");
  const [password, setPassword] = useState("");
  const remove = useMutation({
    mutationFn: () => unwrap(api.POST("/api/v1/auth/me/delete/", { body: { confirm, password } })),
    onSuccess: () => {
      client.clear();
      navigate("/");
    },
  });
  return (
    <Card title={t("account.data")}>
      <p className="text-sm text-muted">{t("account.exportExplain")}</p>
      <a
        href="/api/v1/auth/me/export/"
        download="holidayops-data.json"
        className="mt-3 inline-flex rounded-lg border border-line px-4 py-2 text-sm font-medium text-ink hover:border-accent"
      >
        {t("account.export")}
      </a>
      <form
        className="mt-6 flex flex-col gap-3 rounded-2xl border border-holiday/40 bg-holiday-soft/40 p-4"
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          remove.mutate();
        }}
      >
        <h3 className="font-display text-lg text-holiday">{t("account.delete")}</h3>
        <p className="text-sm text-muted">{t("account.deleteExplain")}</p>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label={t("account.typeEmail", { email: me.email })}>
            <Input
              dir="ltr"
              required
              autoComplete="off"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
            />
          </Field>
          {me.has_password && (
            <Field label={t("auth.password")}>
              <Input
                type="password"
                dir="ltr"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </Field>
          )}
        </div>
        <ErrorText error={remove.error} />
        <Button
          type="submit"
          className="self-start bg-holiday text-white hover:bg-holiday/90"
          disabled={confirm.trim().toLowerCase() !== me.email.toLowerCase() || remove.isPending}
        >
          {t("account.deleteButton")}
        </Button>
      </form>
    </Card>
  );
}

export function AccountPage() {
  const { t } = useTranslation();
  const me = useMe();
  if (me.isLoading) return null;
  if (!me.data) {
    return (
      <p className="text-muted">
        <Link className="text-accent hover:underline" to="/login?next=/app/account">
          {t("auth.login")}
        </Link>
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title={t("account.title")} subtitle={t("account.subtitle")} />
      <Profile me={me.data} />
      <TwoFactorCard me={me.data} />
      <ConnectedCard />
      <SessionsCard />
      <DataCard me={me.data} />
    </div>
  );
}
