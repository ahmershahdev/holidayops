import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { sitePrefix } from "../components/frame/SiteFooter";

const ROUTE = "M10 120 C 150 120, 220 40, 330 60";

// Same look as backend/apps/public/templates/public/404.html.
export function NotFoundPage() {
  const { t } = useTranslation();
  return (
    <section className="grid justify-items-start gap-4 py-10 sm:py-16">
      <p
        aria-hidden="true"
        className="font-display text-[clamp(6rem,22vw,14rem)] leading-[0.85] font-extrabold tracking-[-0.06em] text-transparent [-webkit-text-stroke:2px_var(--color-accent)]"
      >
        404
      </p>
      <h1 className="font-display text-3xl font-bold sm:text-4xl">{t("notFound.title")}</h1>
      <p className="max-w-xl text-muted">{t("notFound.body")}</p>
      <svg
        viewBox="0 0 600 140"
        aria-hidden="true"
        className="not-found-flight w-full max-w-xl overflow-visible rtl:-scale-x-100"
      >
        <path
          pathLength={1}
          d={ROUTE}
          className="fill-none stroke-line"
          strokeWidth="2"
          strokeDasharray="0.01 0.02"
        />
        <path
          pathLength={1}
          d={ROUTE}
          className="route fill-none stroke-glow"
          strokeWidth="4"
          strokeLinecap="round"
        />
        <path
          pathLength={1}
          d="M330 60 C 420 76, 470 20, 590 110"
          className="fill-none stroke-holiday"
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray="0.02 0.03"
        />
      </svg>
      <div className="flex flex-wrap items-center gap-3">
        <Link
          to="/"
          className="rounded-full bg-accent px-5 py-2.5 font-semibold text-on-accent hover:bg-accent-strong"
        >
          {t("notFound.home")}
        </Link>
        <a className="text-accent underline" href={`${sitePrefix()}/holidays/`}>
          {t("notFound.holidays")}
        </a>
      </div>
    </section>
  );
}
