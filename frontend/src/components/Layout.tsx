import { useQueryClient } from "@tanstack/react-query";
import { Suspense, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, NavLink, Outlet } from "react-router";
import { api, unwrap } from "../api/client";
import { currentLanguage } from "../i18n";
import { useEnsureCsrf, useLogout, useMe } from "../lib/auth";
import { VerifyBanner } from "./auth/VerifyBanner";
import { AccountMenu } from "./frame/AccountMenu";
import { Mark, Wordmark } from "./frame/Brand";
import { SiteFooter, sitePrefix } from "./frame/SiteFooter";
import { Switches } from "./frame/Switches";

const pill =
  "relative inline-flex min-h-10 items-center rounded-full px-3 py-1.5 text-[0.95rem] font-medium whitespace-nowrap text-muted transition-colors hover:text-ink";
const navLink = ({ isActive }: { isActive: boolean }) =>
  `${pill} nav-underline ${isActive ? "text-ink" : ""}`;

export function Layout() {
  useEnsureCsrf();
  const { t } = useTranslation();
  const { data: me } = useMe();
  const client = useQueryClient();
  const language = currentLanguage();
  const logout = useLogout();
  const [menuOpen, setMenuOpen] = useState(false);
  const prefix = sitePrefix();

  // Emails are written in the account's language, so keep it in step with the UI choice.
  useEffect(() => {
    if (!me || me.language === language) return;
    void unwrap(api.PATCH("/api/v1/auth/me/", { body: { language } })).then((user) =>
      client.setQueryData(["me"], user),
    );
  }, [me, language, client]);

  useEffect(() => {
    document.documentElement.style.overflow = menuOpen ? "hidden" : "";
  }, [menuOpen]);

  const links = (
    <>
      <a className={`${pill} nav-underline`} href={`${prefix}/holidays/`}>
        {t("nav.holidays")}
      </a>
      <a className={`${pill} nav-underline`} href={`${prefix}/pricing/`}>
        {t("nav.pricing")}
      </a>
      <a className={`${pill} nav-underline`} href={`${prefix}/guide/`}>
        {t("nav.guide")}
      </a>
      <a className={`${pill} nav-underline`} href="/api/v1/docs/">
        {t("nav.apiDocs")}
      </a>
      <NavLink to="/playground" className={navLink}>
        {t("nav.playground")}
      </NavLink>
      {me && (
        <NavLink to="/app" className={navLink}>
          {t("nav.calendars")}
        </NavLink>
      )}
    </>
  );

  const signOut = () => logout.mutate(undefined, { onSuccess: () => window.location.assign("/") });
  const auth = me ? (
    <button type="button" className={pill} onClick={signOut}>
      {t("auth.logout")}
    </button>
  ) : (
    <>
      <Link to="/login" className={pill}>
        {t("auth.login")}
      </Link>
      <Link
        to="/signup"
        className="rounded-full bg-accent px-4 py-2 text-sm font-semibold text-on-accent transition-colors hover:bg-accent-strong"
      >
        {t("footer.start")}
      </Link>
    </>
  );

  return (
    <div id="page-top" className="flex min-h-dvh flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:start-4 focus:top-4 focus:z-[60] focus:rounded-lg focus:bg-surface focus:px-4 focus:py-2"
      >
        {t("nav.skip")}
      </a>
      <header
        id="top"
        className={`site-header sticky top-0 z-50 border-b border-transparent ${menuOpen ? "menu-open" : ""}`}
      >
        <div className="mx-auto flex min-h-[4.25rem] max-w-6xl items-center gap-6 px-4">
          <a
            href={`${prefix}/`}
            className="brand flex items-center gap-2 text-xl text-ink"
            aria-label="HolidayOps"
          >
            <Mark />
            <Wordmark />
          </a>
          <nav aria-label={t("nav.main")} className="hidden gap-1 lg:flex">
            {links}
          </nav>
          <div className="ms-auto hidden items-center gap-3 lg:flex">
            <Switches />
            {me ? <AccountMenu email={me.email} onLogout={signOut} /> : auth}
          </div>
          <button
            type="button"
            className="ms-auto grid size-11 place-items-center rounded-full border border-line bg-surface lg:hidden"
            aria-expanded={menuOpen}
            aria-controls="mobile-menu"
            aria-label={t("nav.menu")}
            onClick={() => setMenuOpen(!menuOpen)}
          >
            <span className={`burger ${menuOpen ? "is-open" : ""}`} aria-hidden="true">
              <i />
              <i />
            </span>
          </button>
        </div>
        {menuOpen && (
          <div
            id="mobile-menu"
            onClick={(event) => {
              if (
                (event.target as HTMLElement).closest("a, button[type=button]:not([aria-pressed])")
              )
                setMenuOpen(false);
            }}
            className="mobile-sheet fixed inset-x-0 top-[4.25rem] bottom-0 z-40 flex flex-col gap-6 overflow-y-auto bg-paper px-5 pt-8 pb-[calc(2rem+env(safe-area-inset-bottom))] lg:hidden"
          >
            <nav aria-label={t("nav.main")} className="sheet-links grid">
              {links}
            </nav>
            <div className="flex flex-wrap items-center gap-3">{auth}</div>
            <Switches />
          </div>
        )}
      </header>
      <main id="main" className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 px-4 py-8">
        {me && !me.email_verified && <VerifyBanner me={me} />}
        <Suspense fallback={<div className="min-h-[60vh]" aria-busy="true" />}>
          <Outlet />
        </Suspense>
      </main>
      <SiteFooter />
    </div>
  );
}
