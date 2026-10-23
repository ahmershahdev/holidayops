import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, ApiError, unwrap } from "../../api/client";
import { checkboxSize, loadRecaptcha, pageTheme } from "../../lib/captcha";

export type BotFields = { website: string; captcha_v3?: string; captcha_v2?: string };

function useCaptchaKeys() {
  return useQuery({
    queryKey: ["captcha-keys"],
    queryFn: () => unwrap(api.GET("/api/v1/auth/captcha/")),
    staleTime: Infinity,
  });
}

/** The fields the server's bot check reads (apps/accounts/captcha.py), and the checkbox it asks
 * for when the invisible score is too low. */
export function useBotCheck(action: string) {
  const { i18n } = useTranslation();
  const keys = useCaptchaKeys().data;
  const [honeypot, setHoneypot] = useState("");
  const [challenge, setChallenge] = useState(false);
  const [v2Token, setV2Token] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (keys?.v3) void loadRecaptcha(keys.v3, i18n.language).catch(() => undefined);
  }, [keys?.v3, i18n.language]);

  async function fields(): Promise<BotFields> {
    const out: BotFields = { website: honeypot };
    if (challenge && v2Token) {
      out.captcha_v2 = v2Token;
    } else if (keys?.v3) {
      try {
        const g = await loadRecaptcha(keys.v3, i18n.language);
        out.captcha_v3 = await g.execute(keys.v3, { action });
      } catch {
        // Blocked or offline: the server answers with the checkbox instead.
      }
    }
    return out;
  }

  function onError(error: unknown) {
    const body = error instanceof ApiError ? error.body : null;
    if (body && typeof body === "object" && "captcha" in body && keys?.v2) {
      setChallenge(true);
      setV2Token("");
      // A token works once: a fresh widget for the next try.
      setAttempt((n) => n + 1);
    }
  }

  const widget = (
    <>
      <Honeypot value={honeypot} onChange={setHoneypot} />
      {challenge && keys?.v2 && (
        <Checkbox
          key={attempt}
          siteKey={keys.v2}
          v3Key={keys.v3 ?? null}
          language={i18n.language}
          onToken={setV2Token}
        />
      )}
      {keys?.v3 && <Notice />}
    </>
  );

  return { fields, onError, widget, waiting: challenge && !v2Token };
}

/** People never see or reach this field; a script that fills every input fills it too. */
function Honeypot({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return (
    <div className="honeypot" aria-hidden="true">
      <label>
        Website
        <input
          type="text"
          name="website"
          tabIndex={-1}
          autoComplete="off"
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      </label>
    </div>
  );
}

function Checkbox({
  siteKey,
  v3Key,
  language,
  onToken,
}: {
  siteKey: string;
  v3Key: string | null;
  language: string;
  onToken: (token: string) => void;
}) {
  const { t } = useTranslation();
  const holder = useRef<HTMLDivElement>(null);
  const [theme, setTheme] = useState(pageTheme);
  const [failed, setFailed] = useState(false);

  // The widget can't change theme once drawn, so it is redrawn when the page's theme changes.
  useEffect(() => {
    const observer = new MutationObserver(() => setTheme(pageTheme()));
    observer.observe(document.documentElement, { attributeFilter: ["data-theme"] });
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const element = holder.current;
    if (!element) return;
    let cancelled = false;
    const target = document.createElement("div");
    element.replaceChildren(target);
    loadRecaptcha(v3Key, language)
      .then((g) => {
        if (cancelled) return;
        g.render(target, {
          sitekey: siteKey,
          theme,
          size: checkboxSize(element.clientWidth),
          callback: onToken,
          "expired-callback": () => onToken(""),
          "error-callback": () => onToken(""),
        });
      })
      .catch(() => setFailed(true));
    return () => {
      cancelled = true;
      element.replaceChildren();
    };
  }, [siteKey, v3Key, language, theme, onToken]);

  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm text-muted">{t("auth.captchaPrompt")}</p>
      <div ref={holder} className="captcha-box" />
      {failed && (
        <p role="alert" className="text-sm text-holiday">
          {t("auth.captchaFailed")}
        </p>
      )}
    </div>
  );
}

function Notice() {
  const { t } = useTranslation();
  return (
    <p className="text-xs leading-relaxed text-muted">
      {t("auth.captchaNotice")}{" "}
      <a
        className="underline underline-offset-2 hover:text-ink"
        href="https://policies.google.com/privacy"
        target="_blank"
        rel="noreferrer"
      >
        {t("auth.googlePrivacy")}
      </a>{" "}
      ·{" "}
      <a
        className="underline underline-offset-2 hover:text-ink"
        href="https://policies.google.com/terms"
        target="_blank"
        rel="noreferrer"
      >
        {t("auth.googleTerms")}
      </a>
    </p>
  );
}
