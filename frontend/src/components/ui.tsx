import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from "react";

export function Card({
  title,
  heading: Heading = "h2",
  children,
}: {
  title?: ReactNode;
  heading?: "h1" | "h2";
  children: ReactNode;
}) {
  return (
    <section className="rounded-[var(--radius-card)] border border-line bg-surface p-5">
      {title && <Heading className="mb-4 font-display text-xl text-ink">{title}</Heading>}
      {children}
    </section>
  );
}

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4 border-b border-line pb-5">
      <div>
        <h1 className="font-display text-3xl text-ink sm:text-4xl">{title}</h1>
        {subtitle && <p className="mt-2 max-w-2xl text-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex gap-2">{actions}</div>}
    </header>
  );
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1.5 text-sm">
      <span className="font-medium text-ink">{label}</span>
      {children}
      {hint && <span className="text-xs text-muted">{hint}</span>}
    </label>
  );
}

const control =
  "rounded-lg border border-line bg-surface px-3 py-2 text-ink placeholder:text-muted focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20 disabled:opacity-60";

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`${control} ${props.className ?? ""}`} />;
}

export { Select } from "./Dropdown";

export function Button({
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "danger" }) {
  const styles = {
    primary: "bg-accent text-on-accent hover:bg-accent-strong disabled:bg-muted",
    ghost: "border border-line bg-surface text-ink hover:border-accent",
    danger: "text-holiday hover:bg-holiday-soft",
  }[variant];
  return (
    <button
      type="button"
      {...props}
      className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed ${styles} ${props.className ?? ""}`}
    />
  );
}

export function ErrorText({ error }: { error: unknown }) {
  if (!error) return null;
  const message = error instanceof Error ? error.message : String(error);
  return (
    <p role="alert" className="text-sm text-holiday">
      {message}
    </p>
  );
}

type Tone = "workday" | "holiday" | "closure" | "halfday" | "neutral";

export function Badge({ tone, children }: { tone: Tone; children: ReactNode }) {
  const styles: Record<Tone, string> = {
    workday: "bg-workday-soft text-workday",
    holiday: "bg-holiday-soft text-holiday",
    closure: "bg-closure-soft text-closure",
    halfday: "bg-halfday-soft text-halfday",
    neutral: "bg-paper text-muted border border-line",
  };
  return (
    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[tone]}`}>
      {children}
    </span>
  );
}
