import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { currentLanguage } from "../../i18n";
import { useFormat } from "../../lib/format";
import { Mark, Wordmark } from "./Brand";
import { Switches } from "./Switches";

// Same content and look as backend/apps/public/templates/public/_footer.html.
const POPULAR = ["PK", "SA", "AE", "US", "GB", "IN"];
const REPO_URL = "https://github.com/ahmershahdev/holidayops";

export function sitePrefix(): string {
  const language = currentLanguage();
  return language === "en" ? "" : `/${language}`;
}

export function SiteFooter() {
  const { t } = useTranslation();
  const fmt = useFormat();
  const prefix = sitePrefix();
  const year = new Date().getFullYear();
  const link = "text-[#e6edf7] hover:text-[#2dd4c4]";
  const heading = "mb-1 text-xs font-semibold tracking-[0.12em] text-[#8fa3bd] uppercase";

  return (
    <footer className="site-footer relative mt-16 overflow-hidden rounded-t-[2rem] bg-night pt-14 text-[#c7d3e3]">
      <svg
        className="footer-route absolute inset-x-0 top-0 h-14 w-full"
        viewBox="0 0 1200 60"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <path pathLength={1} d="M0 50 C 300 50, 420 10, 640 22 S 1000 40, 1200 8" />
      </svg>
      <div className="mx-auto grid max-w-6xl gap-10 px-4 sm:grid-cols-2 lg:grid-cols-[1.6fr_1fr_1fr_1fr]">
        <div className="sm:col-span-2 lg:col-span-1">
          <a
            href={`${prefix}/holidays/`}
            className="flex items-center gap-2 text-xl text-[#e6edf7]"
          >
            <Mark />
            <Wordmark />
          </a>
          <p className="my-4 max-w-sm">{t("footer.tagline")}</p>
          <Link
            to="/signup"
            className="inline-block rounded-full bg-[#2dd4c4] px-5 py-2.5 font-semibold text-[#06122a] hover:bg-[#5eead4]"
          >
            {t("footer.start")}
          </Link>
        </div>
        <nav className="grid content-start gap-2.5" aria-label={t("footer.product")}>
          <h2 className={heading}>{t("footer.product")}</h2>
          <a className={link} href={`${prefix}/holidays/`}>
            {t("nav.holidays")}
          </a>
          <a className={link} href={`${prefix}/pricing/`}>
            {t("nav.pricing")}
          </a>
          <Link className={link} to="/playground">
            {t("nav.playground")}
          </Link>
          <Link className={link} to="/app">
            {t("footer.calendars")}
          </Link>
        </nav>
        <nav className="grid content-start gap-2.5" aria-label={t("footer.popular")}>
          <h2 className={heading}>{t("footer.popular")}</h2>
          {POPULAR.map((code) => (
            <a
              key={code}
              className={link}
              href={`${prefix}/holidays/${code.toLowerCase()}/${year}/`}
            >
              {fmt.country(code)}
            </a>
          ))}
        </nav>
        <nav className="grid content-start gap-2.5" aria-label={t("footer.developers")}>
          <h2 className={heading}>{t("footer.developers")}</h2>
          <a className={link} href="/api/v1/docs/">
            {t("nav.apiDocs")}
          </a>
          <a className={link} href="/api/v1/schema/">
            {t("footer.schema")}
          </a>
          <a className={link} href={REPO_URL} rel="noopener">
            GitHub
          </a>
          <a className={link} href="/sitemap.xml">
            {t("footer.sitemap")}
          </a>
        </nav>
      </div>
      <div className="mx-auto mt-12 flex max-w-6xl flex-wrap items-center justify-between gap-4 border-t border-[#24375c] px-4 py-6 text-sm">
        <Switches dark />
        <p>
          © {year} HolidayOps · {t("footer.credit")}
        </p>
        <a className={link} href="#top">
          {t("footer.top")} ↑
        </a>
      </div>
      <p className="footer-word" aria-hidden="true" dir="ltr">
        HolidayOps
      </p>
    </footer>
  );
}
