import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

export function AccountMenu({ email, onLogout }: { email: string; onLogout: () => void }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointer = (event: MouseEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const item =
    "block w-full rounded-xl px-3 py-2.5 text-start text-sm font-medium text-ink transition-colors hover:bg-accent-soft focus-visible:bg-accent-soft";

  return (
    <div ref={root} className="relative">
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="menu"
        aria-label={t("nav.account")}
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 rounded-full border border-line bg-surface py-1 ps-1 pe-3 transition-colors hover:border-accent"
      >
        <span className="grid size-8 place-items-center rounded-full bg-accent font-display text-sm font-bold text-on-accent">
          {email.charAt(0).toUpperCase()}
        </span>
        <svg
          viewBox="0 0 12 12"
          aria-hidden="true"
          className={`size-3 text-muted transition-transform ${open ? "rotate-180" : ""}`}
        >
          <path
            d="M2.5 4.5 6 8l3.5-3.5"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
          />
        </svg>
      </button>
      {open && (
        <div
          role="menu"
          className="absolute end-0 top-[calc(100%+0.6rem)] z-50 w-64 rounded-2xl border border-line bg-surface p-2 shadow-[0_24px_48px_-24px_rgb(6_18_42/0.45)]"
        >
          <p
            className="truncate border-b border-line px-3 pt-1.5 pb-2.5 text-sm text-muted"
            dir="ltr"
          >
            {email}
          </p>
          <div className="pt-1.5">
            <Link role="menuitem" to="/app" className={item} onClick={() => setOpen(false)}>
              {t("nav.calendars")}
            </Link>
            <button role="menuitem" type="button" className={item} onClick={onLogout}>
              {t("auth.logout")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
