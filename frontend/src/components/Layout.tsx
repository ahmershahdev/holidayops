import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Link, NavLink, Outlet, useNavigate } from "react-router";
import { api, unwrap } from "../api/client";
import { changeLanguage, currentLanguage, type Language, LANGUAGES } from "../i18n";
import { useEnsureCsrf, useLogout, useMe } from "../lib/auth";
import { Button, Select } from "./ui";

const navLink = ({ isActive }: { isActive: boolean }) =>
  `rounded-lg px-3 py-2 text-sm font-medium ${isActive ? "bg-accent-soft text-accent" : "text-muted hover:text-ink"}`;

export function Layout() {
  useEnsureCsrf();
  const { t } = useTranslation();
  const { data: me } = useMe();
  const client = useQueryClient();
  const language = currentLanguage();

  // Emails are written in the account's language, so keep it in step with the UI choice.
  useEffect(() => {
    if (!me || me.language === language) return;
    void unwrap(api.PATCH("/api/v1/auth/me/", { body: { language } })).then((user) =>
      client.setQueryData(["me"], user),
    );
  }, [me, language, client]);
  const logout = useLogout();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:start-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-surface focus:px-4 focus:py-2"
      >
        {t("nav.skip")}
      </a>
      <header className="border-b border-line bg-paper/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
          <Link to="/" className="font-display text-xl font-semibold text-ink" dir="ltr">
            Holiday<span className="text-accent">Ops</span>
          </Link>
          <nav
            aria-label={t("nav.main")}
            className="order-3 flex w-full gap-1 sm:order-none sm:w-auto"
          >
            <NavLink to="/" end className={navLink}>
              {t("nav.playground")}
            </NavLink>
            <NavLink to="/app" className={navLink}>
              {t("nav.calendars")}
            </NavLink>
            <a className={navLink({ isActive: false })} href="/api/v1/docs/">
              {t("nav.apiDocs")}
            </a>
          </nav>
          <div className="ms-auto flex items-center gap-2 text-sm">
            <Select
              aria-label={t("nav.language")}
              value={currentLanguage()}
              onChange={(e) => void changeLanguage(e.target.value as Language)}
              className="py-1.5"
            >
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code} lang={l.code}>
                  {l.label}
                </option>
              ))}
            </Select>
            {me ? (
              <>
                <span className="hidden text-muted md:inline">{me.email}</span>
                <Button
                  variant="ghost"
                  onClick={() => logout.mutate(undefined, { onSuccess: () => navigate("/") })}
                >
                  {t("auth.logout")}
                </Button>
              </>
            ) : (
              <>
                <Link to="/login" className="px-2 text-ink hover:underline">
                  {t("auth.login")}
                </Link>
                <Link
                  to="/signup"
                  className="rounded-lg bg-accent px-4 py-2 font-medium text-white hover:bg-accent-strong"
                >
                  {t("auth.signup")}
                </Link>
              </>
            )}
          </div>
        </div>
      </header>
      <main id="main" className="mx-auto flex max-w-6xl flex-col gap-8 px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}
