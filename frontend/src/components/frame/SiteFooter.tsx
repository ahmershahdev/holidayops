import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { currentLanguage } from "../../i18n";
import { useMe } from "../../lib/auth";
import { useFormat } from "../../lib/format";
import { Mark, Wordmark } from "./Brand";

// Same markup and classes as backend/apps/public/templates/public/_footer.html; the styles are
// one block shared by both stylesheets.
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
  const { data: me } = useMe();

  return (
    <footer className="site-footer">
      <div className="footer-inner">
        <div className="footer-cta">
          <p className="footer-cta-title">
            <span>{t("footer.ctaLine1")}</span>{" "}
            <span className="footer-accent">{t("footer.ctaLine2")}</span>
          </p>
          <div className="footer-actions">
            {me ? (
              <Link className="footer-button" to="/app">
                {t("footer.openCalendars")}
              </Link>
            ) : (
              <>
                <Link className="footer-button footer-button-ghost" to="/login">
                  {t("auth.login")}
                </Link>
                <Link className="footer-button" to="/signup">
                  {t("footer.start")}
                </Link>
              </>
            )}
          </div>
        </div>
        <svg
          className="footer-route"
          viewBox="0 0 1200 80"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <path pathLength={1} d="M4 70 C 260 70, 420 18, 640 30 S 1000 56, 1192 10" />
          <circle cx="1192" cy="10" r="4" />
        </svg>
        <div className="footer-grid">
          <div className="footer-brand">
            <a href={`${prefix}/`} className="brand">
              <Mark />
              <Wordmark />
            </a>
            <p>{t("footer.tagline")}</p>
          </div>
          <nav className="footer-col" aria-label={t("footer.product")}>
            <h2>{t("footer.product")}</h2>
            <a href={`${prefix}/holidays/`}>{t("nav.holidays")}</a>
            <a href={`${prefix}/pricing/`}>{t("nav.pricing")}</a>
            <Link to="/playground">{t("nav.playground")}</Link>
            <Link to="/app">{t("footer.calendars")}</Link>
          </nav>
          <nav className="footer-col footer-countries" aria-label={t("footer.popular")}>
            <h2>{t("footer.popular")}</h2>
            {POPULAR.map((code) => (
              <a key={code} href={`${prefix}/holidays/${code.toLowerCase()}/${year}/`}>
                {fmt.country(code)}
              </a>
            ))}
          </nav>
          <nav className="footer-col" aria-label={t("footer.developers")}>
            <h2>{t("footer.developers")}</h2>
            <a href="/api/v1/docs/">{t("nav.apiDocs")}</a>
            <a href="/api/v1/schema/">{t("footer.schema")}</a>
            <a href={REPO_URL} rel="noopener">
              GitHub
            </a>
            <a href="/sitemap.xml">{t("footer.sitemap")}</a>
          </nav>
        </div>
        <div className="footer-bottom">
          <p>© {year} HolidayOps</p>
          <p>{t("footer.credit")}</p>
        </div>
      </div>
      <p className="footer-word" aria-hidden="true" dir="ltr">
        HolidayOps
      </p>
      <a className="to-top" href="#page-top" aria-label={t("footer.top")}>
        <svg viewBox="0 0 48 48" aria-hidden="true">
          <circle className="to-top-track" cx="24" cy="24" r="21" />
          <circle className="to-top-ring" cx="24" cy="24" r="21" pathLength={1} />
          <path className="to-top-arrow" d="M24 31V17M17.5 23.5 24 17l6.5 6.5" />
        </svg>
      </a>
    </footer>
  );
}
