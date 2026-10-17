import { useMutation, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, type InputHTMLAttributes, type ReactNode, useId, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useSearchParams } from "react-router";
import { api, unwrap } from "../api/client";
import { ErrorText } from "../components/ui";
import { safeNext } from "../lib/navigation";

const ICONS = {
  user: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 20a8 8 0 0 1 16 0",
  mail: "M4 6h16v12H4zM4 7l8 6 8-6",
  lock: "M6 11h12v9H6zM8 11V8a4 4 0 0 1 8 0v3",
};

function AuthField({
  label,
  icon,
  hint,
  trailing,
  ...input
}: InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  icon: keyof typeof ICONS;
  hint?: string;
  trailing?: ReactNode;
}) {
  const id = useId();
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium text-ink">
        {label}
      </label>
      <div className="group relative flex items-center">
        <svg
          viewBox="0 0 24 24"
          aria-hidden="true"
          className="pointer-events-none absolute start-3.5 size-5 fill-none stroke-muted stroke-[1.6] transition-colors group-focus-within:stroke-accent"
        >
          <path d={ICONS[icon]} strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <input
          id={id}
          {...input}
          aria-describedby={hint ? `${id}-hint` : undefined}
          className="h-12 w-full rounded-2xl border border-line bg-surface ps-11 pe-12 text-[0.95rem] text-ink transition-[border-color,box-shadow] placeholder:text-muted/70 focus:border-accent focus:ring-4 focus:ring-accent/15 focus:outline-none"
        />
        {trailing}
      </div>
      {hint && (
        <span id={`${id}-hint`} className="text-xs text-muted">
          {hint}
        </span>
      )}
    </div>
  );
}

function EyeToggle({ shown, onToggle }: { shown: boolean; onToggle: () => void }) {
  const { t } = useTranslation();
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-label={shown ? t("auth.hidePassword") : t("auth.showPassword")}
      aria-pressed={shown}
      className="absolute end-2 grid size-9 place-items-center rounded-xl text-muted transition-colors hover:bg-accent-soft hover:text-ink"
    >
      <svg
        viewBox="0 0 24 24"
        aria-hidden="true"
        className="size-5 fill-none stroke-current stroke-[1.6]"
      >
        <path
          d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx="12" cy="12" r="3" />
        {shown && <path d="M4 4l16 16" strokeLinecap="round" />}
      </svg>
    </button>
  );
}

function ArtPanel() {
  const { t } = useTranslation();
  const points = [t("auth.point1"), t("auth.point2"), t("auth.point3")];
  return (
    <aside
      aria-hidden="true"
      className="auth-art relative hidden overflow-hidden rounded-[2rem] bg-night p-10 text-[#e6edf7] lg:flex lg:flex-col lg:justify-between"
    >
      <svg
        className="auth-route absolute inset-0 size-full"
        viewBox="0 0 400 520"
        preserveAspectRatio="none"
      >
        <path pathLength={1} d="M-10 285 C 100 285, 150 215, 230 222 S 345 185, 380 178" />
      </svg>
      <p className="relative font-display text-4xl leading-[1.05] font-bold tracking-tight">
        <span className="block">{t("footer.ctaLine1")}</span>
        <span className="block text-[#2dd4c4]">{t("footer.ctaLine2")}</span>
      </p>
      <ol className="relative grid gap-4">
        {points.map((point, i) => (
          <li key={point} className="flex items-center gap-3 text-[0.95rem] text-[#c7d3e3]">
            <span className="grid size-8 shrink-0 place-items-center rounded-full border border-[#24375c] bg-[#111d36] font-display text-sm font-semibold text-[#2dd4c4]">
              {i + 1}
            </span>
            {point}
          </li>
        ))}
      </ol>
    </aside>
  );
}

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
    <div className="mx-auto grid w-full max-w-5xl items-stretch gap-10 py-4 lg:grid-cols-[1fr_0.9fr] lg:py-8">
      <section className="flex flex-col justify-center gap-8 lg:px-6">
        <header className="flex flex-col gap-3">
          <h1 className="font-display text-4xl font-bold tracking-tight text-ink sm:text-5xl">
            {login ? t("auth.loginTitle") : t("auth.signupTitle")}
          </h1>
          <p className="max-w-sm text-muted">
            {login ? t("auth.loginLead") : t("auth.signupLead")}
          </p>
        </header>
        <form onSubmit={onSubmit} className="flex flex-col gap-5">
          {!login && (
            <AuthField
              label={t("auth.name")}
              icon="user"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoComplete="name"
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
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={login ? "current-password" : "new-password"}
            placeholder={login ? t("auth.passwordPlaceholder") : t("auth.passwordHint")}
            hint={login ? undefined : t("auth.passwordHint")}
            trailing={<EyeToggle shown={shown} onToggle={() => setShown(!shown)} />}
          />
          <ErrorText error={submit.error} />
          <button
            type="submit"
            disabled={submit.isPending}
            className="group mt-1 flex h-12 items-center justify-center gap-2 rounded-full bg-accent font-semibold text-on-accent transition-colors hover:bg-accent-strong disabled:cursor-wait disabled:opacity-70"
          >
            {login ? t("auth.login") : t("auth.signup")}
            <svg
              viewBox="0 0 20 20"
              aria-hidden="true"
              className="size-4 fill-none stroke-current stroke-2 transition-transform group-hover:translate-x-1 rtl:-scale-x-100 rtl:group-hover:-translate-x-1"
            >
              <path d="M4 10h12M11 5l5 5-5 5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
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
      </section>
      <ArtPanel />
    </div>
  );
}
