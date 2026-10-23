import { useMutation, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useSearchParams } from "react-router";
import { api, type Schemas, unwrap } from "../api/client";
import { AuthField, AuthLayout, EyeToggle, SubmitButton } from "../components/auth/AuthShell";
import { useBotCheck } from "../components/auth/BotCheck";
import {
  OrDivider,
  SsoButtons,
  TwoFactorForm,
  useSsoProviders,
} from "../components/auth/TwoFactorForm";
import { ErrorText } from "../components/ui";
import { safeNext } from "../lib/navigation";
import { CodeInput } from "./ForgotPasswordPage";

const RESEND_AFTER = 60;

export function AuthPage({ mode }: { mode: "login" | "signup" }) {
  const { t } = useTranslation();
  const [search] = useSearchParams();
  const next = safeNext(search.get("next"));
  const [email, setEmail] = useState(search.get("email") ?? "");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [shown, setShown] = useState(false);
  const client = useQueryClient();
  const navigate = useNavigate();
  const login = mode === "login";
  const [twoFactor, setTwoFactor] = useState(search.get("two_factor") === "1");
  const [verifying, setVerifying] = useState(false);
  const bot = useBotCheck("signup");
  const ssoError = search.get("sso_error");
  const hasSso = (useSsoProviders().data ?? []).length > 0;

  async function finish(user: Schemas["User"]) {
    client.setQueryData(["me"], user);
    // Django rotates the CSRF token on login, so fetch the fresh one.
    await client.invalidateQueries({ queryKey: ["csrf"] });
    navigate(next);
  }

  const submit = useMutation({
    mutationFn: async () =>
      login
        ? unwrap(api.POST("/api/v1/auth/login/", { body: { email, password } }))
        : unwrap(
            api.POST("/api/v1/auth/signup/", {
              body: { email, password, name, ...(await bot.fields()) },
            }),
          ),
    onSuccess: async (result) => {
      if ("two_factor_required" in result) setTwoFactor(true);
      else if ("verification_required" in result) setVerifying(true);
      else await finish(result);
    },
    onError: bot.onError,
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    submit.mutate();
  }

  if (verifying) {
    return (
      <AuthLayout
        title={t("auth.codeTitle")}
        lead={
          <>
            {t("auth.verifyLead")}{" "}
            <strong className="font-semibold text-ink" dir="ltr">
              {email}
            </strong>
          </>
        }
      >
        <VerifyEmailForm
          email={email}
          onDone={(result) =>
            "two_factor_required" in result ? setTwoFactor(true) : void finish(result)
          }
          onBack={() => setVerifying(false)}
        />
      </AuthLayout>
    );
  }

  if (twoFactor) {
    return (
      <AuthLayout title={t("twoFactor.title")} lead={t("twoFactor.lead")}>
        <TwoFactorForm onDone={finish} />
        <p className="text-sm text-muted">
          <button
            type="button"
            onClick={() => setTwoFactor(false)}
            className="font-semibold text-accent underline-offset-4 hover:underline"
          >
            {t("twoFactor.back")}
          </button>
        </p>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title={login ? t("auth.loginTitle") : t("auth.signupTitle")}
      lead={login ? t("auth.loginLead") : t("auth.signupLead")}
    >
      {ssoError && (
        <p role="alert" className="rounded-2xl bg-holiday-soft px-4 py-3 text-sm text-holiday">
          {t(`sso.errors.${ssoError}`, { defaultValue: t("sso.errors.failed") })}
        </p>
      )}
      {hasSso && (
        <>
          <SsoButtons next={next} />
          <OrDivider />
        </>
      )}
      <form onSubmit={onSubmit} className="flex flex-col gap-5">
        {!login && (
          <AuthField
            label={t("auth.name")}
            icon="user"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoComplete="name"
            maxLength={150}
            placeholder={t("auth.namePlaceholder")}
          />
        )}
        <AuthField
          label={t("auth.email")}
          icon="mail"
          type="email"
          required
          dir="ltr"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="email"
          placeholder="you@company.com"
        />
        <AuthField
          label={t("auth.password")}
          icon="lock"
          type={shown ? "text" : "password"}
          required
          dir="ltr"
          minLength={login ? undefined : 10}
          maxLength={128}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete={login ? "current-password" : "new-password"}
          placeholder={login ? t("auth.passwordPlaceholder") : t("auth.passwordHint")}
          hint={login ? undefined : t("auth.passwordHint")}
          trailing={<EyeToggle shown={shown} onToggle={() => setShown(!shown)} />}
          aside={
            login && (
              <Link
                to={`/forgot-password${email ? `?email=${encodeURIComponent(email)}` : ""}`}
                className="text-sm font-medium text-accent underline-offset-4 hover:underline"
              >
                {t("auth.forgot")}
              </Link>
            )
          }
        />
        {!login && bot.widget}
        <ErrorText error={submit.error} />
        <SubmitButton pending={submit.isPending} disabled={!login && bot.waiting}>
          {login ? t("auth.login") : t("auth.signup")}
        </SubmitButton>
      </form>
      <p className="text-sm text-muted">
        {login ? t("auth.newHere") : t("auth.haveAccount")}{" "}
        <Link
          className="font-semibold text-accent underline-offset-4 hover:underline"
          to={`${login ? "/signup" : "/login"}?${search.toString()}`}
        >
          {login ? t("auth.createAccount") : t("auth.login")}
        </Link>
      </p>
    </AuthLayout>
  );
}

function VerifyEmailForm({
  email,
  onDone,
  onBack,
}: {
  email: string;
  onDone: (result: Schemas["User"] | Schemas["TwoFactorRequired"]) => void;
  onBack: () => void;
}) {
  const { t } = useTranslation();
  const [code, setCode] = useState("");
  const [wait, setWait] = useState(RESEND_AFTER);
  const bot = useBotCheck("verify");

  useEffect(() => {
    if (wait <= 0) return;
    const timer = setTimeout(() => setWait(wait - 1), 1000);
    return () => clearTimeout(timer);
  }, [wait]);

  const verify = useMutation({
    mutationFn: () => unwrap(api.POST("/api/v1/auth/verify/", { body: { email, code } })),
    onSuccess: onDone,
  });

  const resend = useMutation({
    mutationFn: async () =>
      unwrap(api.POST("/api/v1/auth/verify/resend/", { body: { email, ...(await bot.fields()) } })),
    onSuccess: () => setWait(RESEND_AFTER),
    onError: bot.onError,
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    verify.mutate();
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-5">
      <CodeInput value={code} onChange={setCode} />
      {bot.widget}
      <ErrorText error={verify.error ?? resend.error} />
      <SubmitButton pending={verify.isPending}>{t("auth.verify")}</SubmitButton>
      <p className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted">
        <span>{t("auth.verifyExpires")}</span>
        <button
          type="button"
          disabled={wait > 0 || resend.isPending || bot.waiting}
          onClick={() => resend.mutate()}
          className="font-semibold text-accent underline-offset-4 enabled:hover:underline disabled:text-muted"
        >
          {wait > 0 ? t("auth.resendIn", { seconds: wait }) : t("auth.resend")}
        </button>
        <button
          type="button"
          onClick={onBack}
          className="font-semibold text-accent underline-offset-4 hover:underline"
        >
          {t("auth.otherEmail")}
        </button>
      </p>
      <p className="text-xs text-muted">{t("auth.spamHint")}</p>
    </form>
  );
}
