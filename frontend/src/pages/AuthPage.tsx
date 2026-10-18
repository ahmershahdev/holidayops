import { useMutation, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useSearchParams } from "react-router";
import { api, unwrap } from "../api/client";
import { AuthField, AuthLayout, EyeToggle, SubmitButton } from "../components/auth/AuthShell";
import { ErrorText } from "../components/ui";
import { safeNext } from "../lib/navigation";

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

  const submit = useMutation({
    mutationFn: () =>
      login
        ? unwrap(api.POST("/api/v1/auth/login/", { body: { email, password } }))
        : unwrap(api.POST("/api/v1/auth/signup/", { body: { email, password, name } })),
    onSuccess: async (user) => {
      client.setQueryData(["me"], user);
      // Django rotates the CSRF token on login, so fetch the fresh one.
      await client.invalidateQueries({ queryKey: ["csrf"] });
      navigate(next);
    },
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    submit.mutate();
  }

  return (
    <AuthLayout
      title={login ? t("auth.loginTitle") : t("auth.signupTitle")}
      lead={login ? t("auth.loginLead") : t("auth.signupLead")}
    >
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
        <ErrorText error={submit.error} />
        <SubmitButton pending={submit.isPending}>
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
