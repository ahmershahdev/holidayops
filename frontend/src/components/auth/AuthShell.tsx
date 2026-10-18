import { type InputHTMLAttributes, type ReactNode, lazy, Suspense, useId } from "react";
import { useTranslation } from "react-i18next";

// three.js is ~150 KB gzipped: only the auth pages load it, after their form is on screen.
const GlobeArt = lazy(() => import("./GlobeArt").then((m) => ({ default: m.GlobeArt })));

const ICONS = {
  user: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 20a8 8 0 0 1 16 0",
  mail: "M4 6h16v12H4zM4 7l8 6 8-6",
  lock: "M6 11h12v9H6zM8 11V8a4 4 0 0 1 8 0v3",
  key: "M8 15a4 4 0 1 1 0-8 4 4 0 0 1 0 8zM11 11h9M17 11v3M20 11v2",
};

export function AuthField({
  label,
  icon,
  hint,
  trailing,
  aside,
  ...input
}: InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  icon: keyof typeof ICONS;
  hint?: string;
  trailing?: ReactNode;
  aside?: ReactNode;
}) {
  const id = useId();
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between gap-3">
        <label htmlFor={id} className="text-sm font-medium text-ink">
          {label}
        </label>
        {aside}
      </div>
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

export function EyeToggle({ shown, onToggle }: { shown: boolean; onToggle: () => void }) {
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

export function SubmitButton({ pending, children }: { pending: boolean; children: ReactNode }) {
  return (
    <button
      type="submit"
      disabled={pending}
      className="group mt-1 flex h-12 items-center justify-center gap-2 rounded-full bg-accent font-semibold text-on-accent shadow-[0_12px_30px_-12px] shadow-accent/60 transition-[background-color,transform] hover:bg-accent-strong active:scale-[0.98] disabled:cursor-wait disabled:opacity-70"
    >
      {children}
      <svg
        viewBox="0 0 20 20"
        aria-hidden="true"
        className="size-4 fill-none stroke-current stroke-2 transition-transform group-hover:translate-x-1 rtl:-scale-x-100 rtl:group-hover:-translate-x-1"
      >
        <path d="M4 10h12M11 5l5 5-5 5" strokeLinecap="round" strokeLinejoin="round" />
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
      className="auth-art relative isolate flex min-h-56 flex-col justify-between overflow-hidden rounded-[2rem] bg-night p-7 text-[#e6edf7] lg:min-h-[36rem] lg:p-10"
    >
      <Suspense fallback={null}>
        <GlobeArt className="auth-globe absolute inset-0 -z-10" />
      </Suspense>
      <p className="relative max-w-[16ch] font-display text-3xl leading-[1.05] font-bold tracking-tight lg:text-4xl">
        <span className="block">{t("footer.ctaLine1")}</span>
        <span className="block text-[#2dd4c4]">{t("footer.ctaLine2")}</span>
      </p>
      <ol className="relative hidden gap-3 lg:grid">
        {points.map((point, i) => (
          <li
            key={point}
            className="flex w-fit items-center gap-3 rounded-full border border-[#24375c] bg-[#0b1b3f]/70 py-1.5 ps-1.5 pe-4 text-[0.95rem] text-[#c7d3e3] backdrop-blur"
          >
            <span className="grid size-7 shrink-0 place-items-center rounded-full bg-[#2dd4c4] font-display text-sm font-semibold text-[#06122a]">
              {i + 1}
            </span>
            {point}
          </li>
        ))}
      </ol>
    </aside>
  );
}

/** Form on one side, the globe panel on the other; the panel moves above the form on phones. */
export function AuthLayout({
  title,
  lead,
  children,
}: {
  title: string;
  lead: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="mx-auto grid w-full max-w-5xl items-stretch gap-8 py-4 lg:grid-cols-[1fr_0.95fr] lg:gap-10 lg:py-8">
      <section className="order-2 flex flex-col justify-center gap-8 lg:order-1 lg:px-6">
        <header className="flex flex-col gap-3">
          <h1 className="font-display text-4xl font-bold tracking-tight text-ink sm:text-5xl">
            {title}
          </h1>
          <p className="max-w-sm text-muted">{lead}</p>
        </header>
        {children}
      </section>
      <div className="order-1 lg:order-2">
        <ArtPanel />
      </div>
    </div>
  );
}
