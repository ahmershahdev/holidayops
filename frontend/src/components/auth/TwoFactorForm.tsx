import { useMutation, useQuery } from "@tanstack/react-query";
import { type FormEvent, type ReactNode, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, type Schemas, unwrap } from "../../api/client";
import { ErrorText } from "../ui";
import { AuthField, SubmitButton } from "./AuthShell";

/** The second step of a login: a code from the authenticator app or a recovery code. */
export function TwoFactorForm({ onDone }: { onDone: (user: Schemas["User"]) => void }) {
  const { t } = useTranslation();
  const [code, setCode] = useState("");
  const verify = useMutation({
    mutationFn: () => unwrap(api.POST("/api/v1/auth/2fa/verify/", { body: { code } })),
    onSuccess: onDone,
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    verify.mutate();
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-5">
      <AuthField
        label={t("twoFactor.codeLabel")}
        icon="key"
        required
        dir="ltr"
        autoFocus
        autoComplete="one-time-code"
        maxLength={20}
        value={code}
        onChange={(e) => setCode(e.target.value)}
        placeholder="123456"
        hint={t("twoFactor.codeHint")}
      />
      <ErrorText error={verify.error} />
      <SubmitButton pending={verify.isPending}>{t("twoFactor.verify")}</SubmitButton>
    </form>
  );
}

const LOGOS: Record<string, ReactNode> = {
  google: (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="size-5">
      <path
        fill="#4285F4"
        d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.4h6.5a5.6 5.6 0 0 1-2.4 3.6v3h3.9c2.2-2 3.5-5 3.5-8.7z"
      />
      <path
        fill="#34A853"
        d="M12 24c3.2 0 6-1.1 8-2.9l-3.9-3c-1.1.7-2.5 1.2-4.1 1.2-3.1 0-5.8-2.1-6.7-5H1.3v3.1A12 12 0 0 0 12 24z"
      />
      <path fill="#FBBC05" d="M5.3 14.3a7.2 7.2 0 0 1 0-4.6V6.6h-4a12 12 0 0 0 0 10.8l4-3.1z" />
      <path
        fill="#EA4335"
        d="M12 4.8c1.8 0 3.3.6 4.6 1.8l3.4-3.4A12 12 0 0 0 1.3 6.6l4 3.1c.9-2.9 3.6-4.9 6.7-4.9z"
      />
    </svg>
  ),
  microsoft: (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="size-5">
      <path fill="#F25022" d="M1 1h10.5v10.5H1z" />
      <path fill="#7FBA00" d="M12.5 1H23v10.5H12.5z" />
      <path fill="#00A4EF" d="M1 12.5h10.5V23H1z" />
      <path fill="#FFB900" d="M12.5 12.5H23V23H12.5z" />
    </svg>
  ),
};

export function useSsoProviders() {
  return useQuery({
    queryKey: ["sso"],
    queryFn: () => unwrap(api.GET("/api/v1/auth/sso/")),
    staleTime: Infinity,
  });
}

/** Full-page links, not fetch calls: the provider needs the browser itself. */
export function SsoButtons({ next, link = false }: { next?: string; link?: boolean }) {
  const { t } = useTranslation();
  const providers = useSsoProviders().data ?? [];
  if (!providers.length) return null;
  const query = new URLSearchParams();
  if (next) query.set("next", next);
  if (link) query.set("link", "1");
  return (
    <div className="flex flex-col gap-3">
      {providers.map((provider) => (
        <a
          key={provider.id}
          href={`/sso/${provider.id}/start/?${query.toString()}`}
          className="flex h-12 items-center justify-center gap-3 rounded-full border border-line bg-surface font-semibold text-ink transition-[border-color,transform] hover:border-accent active:scale-[0.98]"
        >
          {LOGOS[provider.id]}
          {link
            ? t("sso.connect", { provider: provider.name })
            : t("sso.continue", { provider: provider.name })}
        </a>
      ))}
    </div>
  );
}

export function OrDivider() {
  const { t } = useTranslation();
  return (
    <div className="flex items-center gap-4 text-xs font-medium tracking-[0.14em] text-muted uppercase">
      <span className="h-px flex-1 bg-line" />
      {t("sso.or")}
      <span className="h-px flex-1 bg-line" />
    </div>
  );
}
