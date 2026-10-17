import { useMutation, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useSearchParams } from "react-router";
import { api, unwrap } from "../api/client";
import { Button, Card, ErrorText, Field, Input } from "../components/ui";
import { safeNext } from "../lib/navigation";

export function AuthPage({ mode }: { mode: "login" | "signup" }) {
  const { t } = useTranslation();
  const [search] = useSearchParams();
  const next = safeNext(search.get("next"));
  const [email, setEmail] = useState(search.get("email") ?? "");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const client = useQueryClient();
  const navigate = useNavigate();

  const submit = useMutation({
    mutationFn: () =>
      mode === "login"
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
    <div className="mx-auto w-full max-w-md">
      <Card heading="h1" title={mode === "login" ? t("auth.loginTitle") : t("auth.signupTitle")}>
        <form onSubmit={onSubmit} className="flex flex-col gap-4">
          {mode === "signup" && (
            <Field label={t("auth.name")}>
              <Input value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" />
            </Field>
          )}
          <Field label={t("auth.email")}>
            <Input
              type="email"
              required
              dir="ltr"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
            />
          </Field>
          <Field
            label={t("auth.password")}
            hint={mode === "signup" ? t("auth.passwordHint") : undefined}
          >
            <Input
              type="password"
              required
              dir="ltr"
              minLength={mode === "signup" ? 10 : undefined}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
            />
          </Field>
          <ErrorText error={submit.error} />
          <Button type="submit" disabled={submit.isPending}>
            {mode === "login" ? t("auth.login") : t("auth.signup")}
          </Button>
          <p className="text-center text-sm text-muted">
            {mode === "login" ? t("auth.newHere") : t("auth.haveAccount")}{" "}
            <Link
              className="text-accent underline"
              to={`${mode === "login" ? "/signup" : "/login"}?${search.toString()}`}
            >
              {mode === "login" ? t("auth.createAccount") : t("auth.login")}
            </Link>
          </p>
        </form>
      </Card>
    </div>
  );
}
