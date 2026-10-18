import { useMutation, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useEffect, useId, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useSearchParams } from "react-router";
import { api, unwrap } from "../api/client";
import { AuthField, AuthLayout, EyeToggle, SubmitButton } from "../components/auth/AuthShell";
import { ErrorText } from "../components/ui";

const RESEND_AFTER = 60;

export function CodeInput({
  value,
  onChange,
}: {
  value: string;
  onChange: (code: string) => void;
}) {
  const { t } = useTranslation();
  const id = useId();
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium text-ink">
        {t("auth.code")}
      </label>
      {/* One field, so paste and the phone's one-time-code autofill both work. The six cells
          behind it are drawn with a gradient. */}
      <input
        id={id}
        required
        dir="ltr"
        inputMode="numeric"
        autoComplete="one-time-code"
        pattern="\d{6}"
        maxLength={6}
        value={value}
        onChange={(e) => onChange(e.target.value.replace(/\D/g, "").slice(0, 6))}
        className="code-input h-16 w-full max-w-[22rem] rounded-2xl border border-line bg-surface ps-[1.1rem] font-mono text-3xl font-semibold tracking-[0.92em] text-ink transition-[border-color,box-shadow] focus:border-accent focus:ring-4 focus:ring-accent/15 focus:outline-none"
      />
    </div>
  );
}

export function ForgotPasswordPage() {
  const { t } = useTranslation();
  const [search] = useSearchParams();
  const [email, setEmail] = useState(search.get("email") ?? "");
  const [step, setStep] = useState<"email" | "code">("email");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [shown, setShown] = useState(false);
  const [wait, setWait] = useState(0);
  const client = useQueryClient();
  const navigate = useNavigate();

  useEffect(() => {
    if (wait <= 0) return;
    const timer = setTimeout(() => setWait(wait - 1), 1000);
    return () => clearTimeout(timer);
  }, [wait]);

  const send = useMutation({
    mutationFn: () => unwrap(api.POST("/api/v1/auth/password/forgot/", { body: { email } })),
    onSuccess: () => {
      setStep("code");
      setWait(RESEND_AFTER);
    },
  });

  const reset = useMutation({
    mutationFn: () =>
      unwrap(api.POST("/api/v1/auth/password/reset/", { body: { email, code, password } })),
    onSuccess: async (user) => {
      client.setQueryData(["me"], user);
      await client.invalidateQueries({ queryKey: ["csrf"] });
      navigate("/app");
    },
  });

  function onEmail(event: FormEvent) {
    event.preventDefault();
    send.mutate();
  }

  function onReset(event: FormEvent) {
    event.preventDefault();
    reset.mutate();
  }

  return (
    <AuthLayout
      title={step === "email" ? t("auth.forgotTitle") : t("auth.codeTitle")}
      lead={
        step === "email" ? (
          t("auth.forgotLead")
        ) : (
          <>
            {t("auth.codeLead")}{" "}
            <strong className="font-semibold text-ink" dir="ltr">
              {email}
            </strong>
          </>
        )
      }
    >
      {step === "email" ? (
        <form onSubmit={onEmail} className="flex flex-col gap-5">
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
          <ErrorText error={send.error} />
          <SubmitButton pending={send.isPending}>{t("auth.sendCode")}</SubmitButton>
        </form>
      ) : (
        <form onSubmit={onReset} className="flex flex-col gap-5">
          <CodeInput value={code} onChange={setCode} />
          <AuthField
            label={t("auth.newPassword")}
            icon="lock"
            type={shown ? "text" : "password"}
            required
            dir="ltr"
            minLength={10}
            maxLength={128}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
            placeholder={t("auth.passwordHint")}
            hint={t("auth.passwordHint")}
            trailing={<EyeToggle shown={shown} onToggle={() => setShown(!shown)} />}
          />
          <ErrorText error={reset.error ?? send.error} />
          <SubmitButton pending={reset.isPending}>{t("auth.resetPassword")}</SubmitButton>
          <p className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted">
            <span>{t("auth.codeExpires")}</span>
            <button
              type="button"
              disabled={wait > 0 || send.isPending}
              onClick={() => send.mutate()}
              className="font-semibold text-accent underline-offset-4 enabled:hover:underline disabled:text-muted"
            >
              {wait > 0 ? t("auth.resendIn", { seconds: wait }) : t("auth.resend")}
            </button>
            <button
              type="button"
              onClick={() => setStep("email")}
              className="font-semibold text-accent underline-offset-4 hover:underline"
            >
              {t("auth.otherEmail")}
            </button>
          </p>
        </form>
      )}
      <p className="text-sm text-muted">
        {t("auth.remembered")}{" "}
        <Link className="font-semibold text-accent underline-offset-4 hover:underline" to="/login">
          {t("auth.login")}
        </Link>
      </p>
    </AuthLayout>
  );
}
